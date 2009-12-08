"""Process manipulation command
"""

__copyright__ = """
Copyright (C) 2008 Novell Inc.
Author: Alex Tsariounov <alext@novell.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import sys, os, re, logging, pwd, grp
from optparse import OptionParser, make_option

from cpuset import cset
from cpuset.util import *
from cpuset.commands.common import *
try: from cpuset.commands import set 
except: pass

global log
log = logging.getLogger('proc')

help = 'create and manage processes within cpusets'
usage = """%prog [options] [path/program [args]]

This command is used to run and manage arbitrary processes on
specified cpusets. It is also used to move pre-existing processes
and threads to specified cpusets.  You may note there is no
"kill" or "destroy" option -- use the standard OS ^C or kill
commands for that.

To list which tasks are running in a particular cpuset, use the
--list command.

For example:
    # cset proc --list --set priset
        This command will list all the tasks running in the
        cpuset called "priset".

Processes are created by specifying the path to the executable
and specifying the cpuset that the process is to be created in.

For example:
    # cset proc --set=blazing_cpuset --exec /usr/bin/fast_code 
        This command will execute the /usr/bin/fast_code program
        on the "blazing_cpuset" cpuset.

The PIDSPEC argument taken for the move command is a comma
separated list of PIDs or TIDs.  The list can also include
brackets of PIDs or TIDs (i.e. tasks) that are inclusive of the
endpoints.

For example:
    1,2,5               Means processes 1, 2 and 5
    1,2,600-700         Means processes 1, 2 and from 600 to 700

Note that the range of PIDs or TIDs does not need to have every
position populated.  In other words, for the example above, if
there is only one process, say PID 57, in the range of 50-65,
then only that process will be moved.

To move a PIDSPEC to a specific cpuset, you can either specify
the PIDSPEC with --pid and the destination cpuset with --toset,
or use the short hand and list the cpuset name after the PIDSPEC
for the --move arguments.

The move command accepts multiple common calling methods.
For example, the following commands are equivalent:
   # cset proc --move 2442,3000-3200 reserved_set
   # cset proc --move --pid=2442,3000-3200 --toset=reserved_set
       These commands move the tasks defined as 2442 and any
       running task between 3000 and 3200 inclusive of the ends
       to the cpuset called "reserved_set".

Specifying the --fromset is not necesary since the tasks will be
moved to the destination cpuset no matter which cpuset they are
currently running on.

Note however that if you do specify a cpuset with the --fromset
option, then only those tasks that are both in the PIDSPEC *and*
are running in the cpuset specified by --fromset will be moved.
I.e., if there is a task running on the system but not in
--fromset that is in PIDSPEC, it will not be moved.

To move all userspace tasks from one cpuset to another, you need
to specify the source and destination cpuset by name.

For example:
    # cset proc --move --fromset=comp1 --toset=comp42
        This command specifies that all processes and threads
        running on cpuset "comp1" be moved to cpuset "comp42".

Note that the move command will not move kernel threads unless
the -k/--kthread switch is specified.  If it is, then all unbound
kernel threads will be added to the move.  Unbound kernel threads
are those that can run on any CPU.  If you also specify the
-a/--all switch, then all tasks, kernel or not, bound or not,
will be moved.  

CAUTION: Please be cautious with the --all switch, since moving a
kernel thread that is bound to a specific CPU to a cpuset that
does not include that CPU can cause a system hang.

You must specify unique cpuset names for the both exec and move
commands.  If a simple name passed to the --fromset, --toset and
--set parameters is unique on the system then that command
executes.  However, if there are multiple cpusets by that name,
then you will need to specify which one you mean with a full path
rooted at the base cpuset tree.

For example, suppose you have the following cpuset tree:
    /group1
        /myset
        /yourset
    /group2
        /myset
        /yourset

Then, to move a process from myset in group1 to yourset in
group2, you would have to issue the following command:
    # cset proc --move --pid=50 --fromset=/group1/myset \\
            --toset=/group2/yourset
"""

verbose = 0
options = [make_option('-l', '--list',
                       help = 'list processes in the specified cpuset',
                       action = 'store_true'),
           make_option('-e', '--exec',
                       help = 'execute arguments in the specified cpuset',
                       dest = 'exc',
                       action = 'store_true'),
           make_option('-u', '--user',
                       help = 'use this USER to --exec (id or name)'),
           make_option('-g', '--group',
                       help = 'use this GROUP to --exec (id or name)'),
           make_option('-m', '--move',
                       help = 'move specified tasks to specified cpuset; '
                              'to move a PIDSPEC to a cpuset, use -m PIDSPEC cpuset; '
                              'to move all tasks specify --fromset and --toset',
                       action = 'store_true'),
           make_option('-p', '--pid',
                       metavar = 'PIDSPEC',
                       help = 'specify pid or tid specification'),
           make_option('-s', '--set',
                       metavar = 'CPUSET',
                       help = 'specify name of immediate cpuset'),
           make_option('-t', '--toset',
                       help = 'specify name of destination cpuset'),
           make_option('-f', '--fromset',
                       help = 'specify name of origination cpuset'),
           make_option('-k', '--kthread',
                       help = 'move, or include moving, unbound kernel threads',
                       action = 'store_true'),
           make_option('-a', '--all',
                       help = 'force all processes and threads to be moved',
                       action = 'store_true'),
           make_option('-v', '--verbose',
                       help = 'prints more detailed output, additive',
                       action = 'count')
          ]

def func(parser, options, args):
    log.debug("entering func, options=%s, args=%s", options, args)

    global verbose
    if options.verbose: verbose = options.verbose

    cset.rescan()

    tset = None 
    if options.list or options.exc:
        if options.set:
            tset = cset.unique_set(options.set)
        elif options.toset:
            tset = cset.unique_set(options.toset)
        elif len(args) > 0:
            tset = cset.unique_set(args[0])
            if options.exc: del args[0]
            else: tset = args
        else:
            raise CpusetException("cpuset not specified")
        try:
            log.debug("operating on set %s", tset.path)
        except:
            log.debug("operating on sets %s", tset)

    if options.exc: run(tset, args, options.user, options.group)

    if options.list:
        list_sets(tset)
        return

    if options.move or options.kthread:
        # first, we need to know the destination
        tset = None
        if options.toset:
            tset = cset.unique_set(options.toset)
        elif options.set:
            tset = cset.unique_set(options.set)
        elif len(args) > 0:
            if len(args) > 1 and options.pid == None:
                options.pid = args[0]
                tset = cset.unique_set(args[1])
            else:
                tset = cset.unique_set(args[0])
        else:
            raise CpusetException("destination cpuset not specified")
        set.active(tset)
        # next, if there is a pidspec, move just that
        if options.pid:
            fset = None
            if options.fromset and not options.all: 
                fset = cset.unique_set(options.fromset)
            pids = pidspec_to_list(options.pid, fset)
            if len(pids):
                l = []
                l.append('--> moving following pidspec: %s' % options.pid)
                l.extend(task_detail_header('   '))
                l.extend(task_detail_table(pids, '   ', 76))
                log.info("\n".join(l))
                selective_move(None, tset, pids, options.kthread, options.all)
            log.info('done')
        else:
            # here we assume move everything from fromset to toset
            if options.fromset == None:
                raise CpusetException("origination cpuset not specified")
            fset = cset.unique_set(options.fromset)
            nt = len(fset.tasks)
            if nt == 0:
                raise CpusetException('no tasks to move from cpuset "%s"' 
                                      % fset.path)
            if options.move:
                log.info('--> moving all tasks from "%s" to "%s"...', 
                         fset.path, tset.path)
                selective_move(fset, tset, None, options.kthread, options.all)
            else:
                log.info('--> moving all kernel threads from "%s" to "%s"...', 
                         fset.path, tset.path)
                # this is a -k "move", so only move kernel threads
                pids = []
                for task in fset.tasks:
                    try: os.readlink('/proc/'+task+'/exe')
                    except: pids.append(task)
                selective_move(fset, tset, pids, options.kthread, options.all)
            log.info('done')
        return

    # default no options is list
    list_sets(args)

def list_sets(args):
    l = []
    if isinstance(args, list):
        for s in args: l.extend(cset.find_sets(s))
    else:
        l.extend(cset.find_sets(args))
    for s in l:
        if len(s.tasks) > 0:
            if verbose:
                log_detailed_task_table(s, '   ')
            else:
                log_detailed_task_table(s, '   ', 76)
        else:
            log.info(cset.summary(s))

def move(fromset, toset, plist=None):
    log.debug('entering move, fromset=%s toset=%s list=%s', fromset, toset, plist)
    if isinstance(fromset, str):
        fset = cset.unique_set(fromset)
    elif not isinstance(fromset, cset.CpuSet) and plist == None:
        raise CpusetException(
                "passed fromset=%s, which is not a string or CpuSet" % fromset)
    else:
        fset = fromset
    if isinstance(toset, str):
        tset = cset.unique_set(toset)
    elif not isinstance(toset, cset.CpuSet):
        raise CpusetException(
                "passed toset=%s, which is not a string or CpuSet" % toset)
    else:
        tset = toset
    if plist == None:
        log.debug('moving default of all processes')
        tset.tasks = fset.tasks
    else:
        tset.tasks = plist

def selective_move(fset, tset, plist=None, kthread=None, force=None):
    log.debug('entering selective_move, fset=%s tset=%s plist=%s kthread=%s force=%s',
              fset, tset, plist, kthread, force)
    target = cset.unique_set(tset)
    tasks = []
    task_heap = []
    task_check = []
    utsk = 0
    ktsk = 0
    autsk = 0
    aktsk = 0
    utsknr = 0
    ktsknr = 0
    ktskb = 0
    if fset: 
        task_check = cset.unique_set(fset).tasks
    if plist:
        task_heap = plist
    else:
        task_heap = cset.unique_set(fset).tasks
    for task in task_heap:
        try:
            # kernel threads do not have an excutable image
            os.readlink('/proc/'+task+'/exe')
            autsk += 1
            if fset and not force: 
                try:
                    task_check.index(task)
                    tasks.append(task)
                    utsk += 1
                except:
                    log.debug(' task %s not running in %s, skipped', 
                              task, fset.name)
                    utsknr += 1
            else:
                tasks.append(task)
                utsk += 1
        except:
            aktsk += 1
            try:
                # this is in try because the task may not exist by the
                # time we do this, in that case, just ignore it
                if kthread:
                    if force: 
                        tasks.append(task)
                        ktsk += 1
                    else:
                        if is_unbound(task): 
                            tasks.append(task)
                            ktsk += 1
                        else:
                            log.debug(' kernel thread %s is bound, not adding',
                                      task)
                            ktskb += 1
            except:
                log.debug(' kernel thread %s not found , perhaps it went away',
                          task)
                ktsknr += 1
    # ok, move 'em
    log.debug('moving %d tasks to "%s"...', len(tasks), tset.name)
    if len(tasks) == 0: 
        log.info('** no task matched move criteria')
    if autsk > 0:
        l = []
        l.append('moving')
        l.append(str(utsk))
        l.append('userspace tasks')
        if utsknr > 0:
            l.append('- not moving')
            l.append(str(utsknr))
            l.append('tasks (not in fromset)')
        log.info(' '.join(l))
    if ktsk > 0 or kthread:
        l = []
        l.append('moving')
        l.append(str(ktsk))
        l.append('kernel threads')
        if ktskb > 0:
            l.append('- not moving')
            l.append(str(ktskb))
            l.append('threads (not unbound)')
        log.info(' '.join(l))
    if aktsk > 0 and force and not kthread and autsk == 0:
        log.info('** not moving kernel threads since both --all and --kthread needed')
    if ktsknr > 0:
        l = []
        l.append('--> not moving')
        l.append(str(ktsknr))
        l.append('tasks because they are missing (race)')
    move(None, target, tasks)

def run(tset, args, usr_par=None, grp_par=None):
    if isinstance(tset, str):
        s = cset.unique_set(tset)
    elif not isinstance(tset, cset.CpuSet):
        raise CpusetException(
                "passed set=%s, which is not a string or CpuSet" % tset)
    else:
        s = tset
    log.debug('entering run, set=%s args=%s ', s.path, args)
    set.active(s)
    # check user
    if usr_par:
        try:
            user = pwd.getpwnam(usr_par)[2]
        except KeyError:
            try:
                user = pwd.getpwuid(int(usr_par))[2]
            except:
                raise CpusetException('unknown user: "%s"' % usr_par)
    if grp_par:
        try:
            group = grp.getgrnam(grp_par)[2]
        except KeyError:
            try:
                group = grp.getgrgid(int(grp_par))[2]
            except:
                raise CpusetException('unknown group: "%s"' % grp_par)
    elif usr_par:
        # if user is specified but group is not, and user is not root,
        # then use the users group
        if user != 0:
            try:
                group = grp.getgrnam('users')[2]
                grp_par = True
            except:
                pass # just forget it
    # move myself into target cpuset and exec child
    move_pidspec(str(os.getpid()), s)
    log.info('--> last message, executed args into cpuset "%s", new pid is: %s', 
             s.path, os.getpid()) 
    # change user and group before exec
    if grp_par: os.setgid(group)
    if usr_par: os.setuid(user)
    os.execvp(args[0], args)

def is_unbound(proc):
    # FIXME: popen is slow... need to use sched_getaffinity() directly,
    # but python doesn't have it... maybe use pyrex to wrap....
    line = os.popen('/usr/bin/taskset -p ' + str(proc), 'r').readline()
    aff = line.split()[-1]
    log.debug('is_unbound, proc=%s aff=%s allcpumask=%s', 
              proc, aff, cset.allcpumask)
    if aff == cset.allcpumask: return True
    return False

def pidspec_to_list(pidspec, fset=None):
    log.debug('entering pidspecToList, pidspec=%s', pidspec)
    if fset: 
        if isinstance(fset, str): fset = cset.unique_set(fset)
        elif not isinstance(fset, cset.CpuSet):
            raise CpusetException("passed fset=%s, which is not a string or CpuSet" % fset)
        log.debug('from-set specified as: %s', fset.path)
    if not isinstance(pidspec, str):
        raise CpusetException('pidspec=%s is not a string' % pidspec)
    groups = pidspec.split(',')
    plist = []
    if fset: chktsk = fset.tasks
    log.debug('parsing groups: %s', groups)
    for sub in groups:
        items = sub.split('-')
        if len(items) == 1:
            if not len(items[0]):
                # two consecutive commas in pidspec, just continue processing
                continue
            # one pid in this group
            if fset:
                try:
                    chktsk.index(items[0])
                    plist.append(items[0])
                    log.debug(' added single pid: %s', items[0])
                except:
                    log.debug(' task %s not running in %s, skipped', items[0], fset.name)
            else:
                plist.append(items[0])
                log.debug(' added single pid: %s', items[0])
        elif len(items) == 2:
            # a range of pids, only include those that exist
            rng = [str(x) for x in range(int(items[0]), int(items[1])+1) 
                           if os.access('/proc/'+str(x), os.F_OK)]
            if fset:
                for tsk in rng:
                    try:
                        chktsk.index(tsk)
                        plist.append(tsk)
                        log.debug(' added task from range: %s', tsk)
                    except:
                        log.debug(' task %s not running in %s, skipped', tsk, fset.name)
            else:
                plist.extend(rng)
                log.debug(' added range of pids from %s-%s: %s', items[0], items[1], rng)
        else:
            raise CpusetException('pidspec=%s has bad group=%s' % (pidspec, items))
    log.debug('returning parsed pid list: %s', plist)
    log.info('%s tasks match criteria', len(plist))
    return plist

def move_pidspec(pidspec, toset, fset=None):
    log.debug('entering move_pidspec, pidspec=%s toset=%s', pidspec, toset)
    if not fset:
        pids = pidspec_to_list(pidspec)
    else:
        # if fromset is specified, only move tasks that are in pidspec
        # and are running in fromset
        log.debug('specified fset=%s', fset)
        pids = pidspec_to_list(pidspec, fset)
        if len(pids) == 0:
            raise CpusetException('tasks do not match all criteria, none moved')
    move(None, toset, pids)

def task_detail(pid, width=65):
    # get task details from /proc
    pid = str(pid)
    if not os.access('/proc/'+pid, os.F_OK):
        raise CpusetException('task "%s" does not exist' % pid)
    status = file('/proc/'+pid+'/status', 'r').readlines()
    stdict = {}
    for line in status:
        try:
            stdict[line.split()[0][:-1]] = line.split(':')[1].strip()
        except:
            pass  # sometimes, we get an extra \n out of this file...
    cmdline = file('/proc/'+pid+'/cmdline').readline()
    # assume that a zero delimits the cmdline (it does now...)
    cmdline = cmdline.replace('\0', ' ')
    used = 0
    out = pwd.getpwuid(int(stdict['Uid'].split()[0]))[0][:8].ljust(8)
    used += 8 
    out += stdict['Pid'].rjust(6)
    used += 6
    out += stdict['PPid'].rjust(6)
    used += 6
    out += stdict['State'].split()[0].center(3)
    used += 3
    try:
        os.readlink('/proc/'+pid+'/exe')
        #prog = stdict['Name'] + ' '.join(cmdline.split()[1:])
        prog = cmdline
    except:
        prog = '['+stdict['Name']+']'
    if width == 0:
        out += prog
    else:
        out += prog[:(width-used)]

    return out

def task_detail_header(indent=None):
    if indent == None: istr = ""
    else: istr = indent
    l = []
    l.append(istr + 'USER       PID  PPID S TASK NAME')
    l.append(istr + '-------- ----- ----- - ---------')
    return l

def task_detail_table(pids, indent=None, width=None):
    l = []
    if indent == None: istr = ""
    else: istr = indent
    for task in pids:
        if width: l.append(istr + task_detail(task, width))
        else: l.append(istr + task_detail(task, 0))
    return l

def log_detailed_task_table(set, indent=None, width=None):
    log.debug("entering print_detailed_task_table, set=%s indent=%s width=%s",
              set.path, indent, width)
    l = []
    l.append(cset.summary(set))
    l.extend(task_detail_header(indent))
    l.extend(task_detail_table(set.tasks, indent, width))
    log.info("\n".join(l))

