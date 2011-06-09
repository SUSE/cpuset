"""Process manipulation command
"""

__copyright__ = """
Copyright (C) 2007-2010 Novell Inc.
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

from cpuset import config
from cpuset import cset
from cpuset.util import *
from cpuset.commands.common import *
try: from cpuset.commands import set 
except SyntaxError:
    raise
except: 
    pass

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
    # cset proc --list --set myset
        This command will list all the tasks running in the
        cpuset called "myset".

Processes are created by specifying the path to the executable
and specifying the cpuset that the process is to be created in.

For example:
    # cset proc --set=blazing_cpuset --exec /usr/bin/fast_code 
        This command will execute the /usr/bin/fast_code program
        on the "blazing_cpuset" cpuset.

Note that if your command takes options, then use the traditional
"--" marker to separate cset's options from your command's
options.

For example:
    # cset proc --set myset --exec -- ls -l
        This command will execute "ls -l" on the cpuset called
        "myset".

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

Specifying the --fromset is not necessary since the tasks will be
moved to the destination cpuset no matter which cpuset they are
currently running on.

Note however that if you do specify a cpuset with the --fromset
option, then only those tasks that are both in the PIDSPEC *and*
are running in the cpuset specified by --fromset will be moved.
I.e., if there is a task running on the system but not in
--fromset that is in PIDSPEC, it will not be moved.

If the --threads switch is used, then the proc command will
gather any threads of belonging to any processes or threads that
are specified in the PIDSPEC and move them.  This provides an easy
way to move all related threads: just pick one TID from the set
and use the --threads option.

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
--force switch, then all tasks, kernel or not, bound or not,
will be moved.  

CAUTION: Please be cautious with the --force switch, since moving
a kernel thread that is bound to a specific CPU to a cpuset that
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
                       help = 'execute arguments in the specified cpuset; '
                              'use the "--" option separator to separate '
                              'cset options from your exec\'ed command options',
                       dest = 'exc',
                       action = 'store_true'),
           make_option('-u', '--user',
                       help = 'use this USER to --exec (id or name)'),
           make_option('-g', '--group',
                       help = 'use this GROUP to --exec (id or name)'),
           make_option('-m', '--move',
                       help = 'move specified tasks to specified cpuset; '
                              'to move a PIDSPEC to a cpuset, use -m PIDSPEC cpuset; '
                              'to move all tasks only specify --fromset and --toset',
                       action = 'store_true'),
           make_option('-p', '--pid',
                       metavar = 'PIDSPEC',
                       help = 'specify pid or tid specification for move'),
           make_option("--threads",
                       help = 'if specified, any processes found in the PIDSPEC to have '
                              'multiple threads will automatically have all their threads '
                              'added to the PIDSPEC; use to move all related threads to a '
                              'cpuset',
                       action = 'store_true'),
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
           make_option('--force',
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
            if options.exc: 
                tset = cset.unique_set(args[0])
                del args[0]
            else:
                tset = args
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
        fset = None
        tset = None
        # first, we need to know the destination
        if options.toset:
            tset = cset.unique_set(options.toset)
        elif options.set and options.pid:
            tset = cset.unique_set(options.set)
        elif options.set and options.fromset:
            tset = cset.unique_set(options.set)
        elif len(args) > 0:
            if len(args) > 1 and options.pid == None:
                options.pid = args[0]
                if len(args) < 3:
                    tset = cset.unique_set(args[1])
                else:
                    # "-m 123 set1 set2" shortcut
                    fset = cset.unique_set(args[1])
                    tset = cset.unique_set(args[2])
                # take care of set1->set2 shortcut
                pids = pidspec_to_list(options.pid, threads=options.threads)
                if len(pids) == 1:
                    try:
                        fset = cset.unique_set(pids[0])
                        options.pid = None
                    except:
                        pass  # must be real pidspec
            else:
                if len(args) < 2:
                    tset = cset.unique_set(args[0])
                else:
                    fset = cset.unique_set(args[0])
                    tset = cset.unique_set(args[1])
        else:
            raise CpusetException("destination cpuset not specified")
        set.active(tset)
        # next, if there is a pidspec, move just that
        if options.pid:
            if options.fromset and not options.force: 
                fset = cset.unique_set(options.fromset)
            elif options.toset and options.set:
                fset = cset.unique_set(options.set)
            pids = pidspec_to_list(options.pid, fset, options.threads)
            if len(pids):
                log.info('moving following pidspec: %s' % ','.join(pids))
                selective_move(None, tset, pids, options.kthread, options.force)
            else:
                log.info('**> no tasks moved')
            log.info('done')
        else:
            fset = None
            # here we assume move everything from fromset to toset
            if options.fromset:
                fset = cset.unique_set(options.fromset)
            elif options.set:
                fset = cset.unique_set(options.set)
            elif len(args) > 0:
                # this must be the fromset, then...
                fset = cset.unique_set(args[0])
            if fset == None:
                raise CpusetException("origination cpuset not specified")
            nt = len(fset.tasks)
            if nt == 0:
                raise CpusetException('no tasks to move from cpuset "%s"' 
                                      % fset.path)
            if options.move:
                log.info('moving all tasks from %s to %s', 
                         fset.name, tset.path)
                selective_move(fset, tset, None, options.kthread, options.force,
                               options.threads)
            else:
                log.info('moving all kernel threads from %s to %s', 
                         fset.path, tset.path)
                # this is a -k "move", so only move kernel threads
                pids = []
                for task in fset.tasks:
                    try: os.readlink('/proc/'+task+'/exe')
                    except: pids.append(task)
                selective_move(fset, tset, pids, options.kthread, options.force)
            log.info('done')
        return

    # default no options is list
    list_sets(args)

def list_sets(args):
    log.debug("entering list_sets, args=%s", args)
    l = []
    if isinstance(args, list):
        for s in args: 
            if isinstance(s, str):
                l.extend(cset.find_sets(s))
            elif not isinstance(s, cset.CpuSet):
                raise CpusetException(
                        'list_sets() args=%s, of which "%s" not a string or CpuSet' 
                        % (args, s))
            else:
                l.append(s)
    else:
        if isinstance(args, str):
            l.extend(cset.find_sets(args))
        elif not isinstance(args, cset.CpuSet):
            raise CpusetException(
                    "list_sets() passed args=%s, which is not a string or CpuSet" % args)
        else:
            l.append(args)
    if len(l) == 0:
        raise CpusetException("cpuset(s) to list not specified");
    for s in l:
        if len(s.tasks) > 0:
            if verbose:
                log_detailed_task_table(s, ' ')
            else:
                log_detailed_task_table(s, ' ', 78)
        else:
            log.info(cset.summary(s))

def move(fromset, toset, plist=None, verb=None, force=None):
    log.debug('entering move, fromset=%s toset=%s list=%s force=%s verb=%s', 
              fromset, toset, plist, force, verb)
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
        if tset != fset and not force: 
            plist = fset.tasks
        else:
            raise CpusetException(
                    "cannot move tasks into their origination cpuset")
    output = 0
    if verb: 
        output = verb
    elif verbose: 
        output = verbose
    if output:
        l = []
        if config.mread:
            l.append('move_tasks_start')
            l.extend(task_detail_table(plist))
            l.append('move_tasks_stop')
        else:
            l.append(' ')
            l.extend(task_detail_header(' '))
            if output > 1:
                l.extend(task_detail_table(plist, ' '))
            else:
                l.extend(task_detail_table(plist, ' ', 76))
        log.info("\n".join(l))
    # do the move...
    tset.tasks = plist

def selective_move(fset, tset, plist=None, kthread=None, force=None, threads=None):
    log.debug('entering selective_move, fset=%s tset=%s plist=%s kthread=%s force=%s',
              fset, tset, plist, kthread, force)
    task_check = []
    tasks = []
    task_heap = []
    utsk = 0
    ktsk = 0
    autsk = 0
    aktsk = 0
    utsknr = 0
    ktsknr = 0
    ktskb = 0
    sstsk = 0
    target = cset.unique_set(tset)
    if fset: 
        fset = cset.unique_set(fset)
        if fset == target and not force:
            raise CpusetException(
                    "error, same source/destination cpuset, use --force if ok")
        task_check = fset.tasks
    if plist:
        task_heap = plist
    else:
        task_heap = cset.unique_set(fset).tasks
    log.debug('processing task heap')
    for task in task_heap:
        try:
            # kernel threads do not have an excutable image
            os.readlink('/proc/'+task+'/exe')
            autsk += 1
            if fset and not force: 
                try:
                    task_check.index(task)
                    tasks.append(task)
                    log.debug(' added task %s', task)
                    utsk += 1
                    if threads:
                        log.debug(' thread matching, looking for threads for task %s', task)
                        dirs = os.listdir('/proc/'+task+'/task')
                        if len(dirs) > 1:
                            for thread in dirs:
                                if thread != task:
                                    log.debug('  adding thread %s', thread)
                                    tasks.append(thread)
                                    utsk += 1 
                except ValueError:
                    log.debug(' task %s not running in %s, skipped', 
                              task, fset.name)
                    utsknr += 1
            else:
                if not force and cset.lookup_task_from_cpusets(task) == target.path:
                    log.debug(' task %s moving to orgination set %s, skipped',
                              task, target.path)
                    sstsk += 1
                else:
                    tasks.append(task)
                    utsk += 1
        except OSError:
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
                        elif cset.lookup_task_from_cpusets(task) == target.path:
                            log.debug(' task %s moving to orgination set %s, skipped',
                                      task, target.path)
                            sstsk += 1
                        else:
                            log.debug(' kernel thread %s is bound, not adding',
                                      task)
                            ktskb += 1
            except:
                log.debug(' kernel thread %s not found , perhaps it went away',
                          task)
                ktsknr += 1
    # ok, move 'em
    log.debug('moving %d tasks to %s ...', len(tasks), tset.name)
    if len(tasks) == 0: 
        log.info('**> no task matched move criteria')
        if sstsk > 0:
            raise CpusetException('same source/destination cpuset, use --force if ok')
        elif len(task_heap) > 0 and not kthread:
            raise CpusetException('if you want to move kernel threads, use -k')
        elif ktskb > 0:
            raise CpusetException('kernel tasks are bound, use --force if ok')
        return
    if utsk > 0:
        l = []
        l.append('moving')
        l.append(str(utsk))
        l.append('userspace tasks to')
        l.append(tset.path)
        log.info(' '.join(l))
    if utsknr > 0:
        l = []
        l.append('--> not moving')
        l.append(str(utsknr))
        l.append('tasks (not in fromset, use --force)')
        log.info(' '.join(l))
    if ktsk > 0 or kthread:
        l = []
        l.append('moving')
        l.append(str(ktsk))
        l.append('kernel threads to:')
        l.append(tset.path)
        log.info(' '.join(l))
    if ktskb > 0:
        l = []
        l.append('--> not moving')
        l.append(str(ktskb))
        l.append('threads (not unbound, use --force)')
        log.info(' '.join(l))
    if aktsk > 0 and force and not kthread and autsk == 0:
        log.info('*** not moving kernel threads, need both --force and --kthread')
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
    if usr_par: 
        os.setuid(user)
        os.environ["LOGNAME"] = usr_par
        os.environ["USERNAME"] = usr_par
        os.environ["USER"] = usr_par
    os.execvp(args[0], args)

def is_unbound(proc):
    # FIXME: popen is slow... 
    # --> use /proc/<pid>/status -> Cpus_allowed
    #     int(line.replace(',',''), 16)
    #     note: delete leading zeros to compare to allcpumask
    line = os.popen('/usr/bin/taskset -p ' + str(proc) +' 2>/dev/null', 'r').readline()
    aff = line.split()[-1]
    log.debug('is_unbound, proc=%s aff=%s allcpumask=%s', 
              proc, aff, cset.allcpumask)
    if aff == cset.allcpumask: return True
    return False

def pidspec_to_list(pidspec, fset=None, threads=False):
    """create a list of process ids out of a pidspec"""
    log.debug('entering pidspecToList, pidspec=%s fset=%s threads=%s', 
              pidspec, fset, threads)
    if fset: 
        if isinstance(fset, str): fset = cset.unique_set(fset)
        elif not isinstance(fset, cset.CpuSet):
            raise CpusetException("passed fset=%s, which is not a string or CpuSet" % fset)
        log.debug('from-set specified as: %s', fset.path)
    if not isinstance(pidspec, str):
        raise CpusetException('pidspec=%s is not a string' % pidspec)
    groups = pidspec.split(',')
    plist = []
    nifs = 0
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
                    nifs += 1
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
                        nifs += 1
            else:
                plist.extend(rng)
                log.debug(' added range of pids from %s-%s: %s', items[0], items[1], rng)
        else:
            raise CpusetException('pidspec=%s has bad group=%s' % (pidspec, items))
    log.debug('raw parsed pid list of %s tasks: %s', len(plist), plist)
    if nifs > 0:
        if nifs > 1: nmsg = "tasks"
        else: nmsg = "task"
        log.info('**> skipped %s %s, not in origination set "%s"', nifs, nmsg, fset.name)
    log.debug('checking for duplicates...')
    pdict = {}
    dups = 0
    for task in plist:
        if task in pdict:
            dups += 1
            continue
        pdict[task] = True
    log.debug('found %s duplicates', dups)
    if threads:
        log.debug('thread matching activated, looking for threads...')
        dups = 0
        hits = 0
        for task in pdict.keys():
            dirs = os.listdir('/proc/'+str(task)+'/task')
            if len(dirs) > 1:
                hits += 1
                for thread in dirs:
                    if thread in pdict:
                        dups += 1
                        continue
                    pdict[thread] = True
        log.debug('found %s multithreaded containers and %s duplicates', hits, dups)
    plist = pdict.keys()
    log.debug('returning parsed pid list of %s tasks: %s', len(plist), plist)
    return plist

def move_pidspec(pidspec, toset, fset=None, threads=False):
    log.debug('entering move_pidspec, pidspec=%s toset=%s threads=%s', pidspec, toset,
              threads)
    if not fset:
        pids = pidspec_to_list(pidspec, None, threads)
    else:
        # if fromset is specified, only move tasks that are in pidspec
        # and are running in fromset
        log.debug('specified fset=%s', fset)
        pids = pidspec_to_list(pidspec, fset, threads)
        if len(pids) == 0:
            raise CpusetException('tasks do not match all criteria, none moved')
    move(None, toset, pids)

def task_detail(pid, width=70):
    # scheduler policy definitions
    policy = ['o', 'f', 'r', 'b']
    # stat location definitions
    statdef = {
        'pid': 0,
        'name': 1,
        'state': 2,
        'ppid': 3,
        'pgid': 4,
        'sid': 5,
        'priority': 17,
        'nice': 18,
        'numthreads': 19,
        'rtpriority': 39,
        'rtpolicy': 40,
    }
    # get task details from /proc, stat has rtprio/policy but not uid...
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
    stat = file('/proc/'+pid+'/stat', 'r').readline()
    stat = stat.split()
    cmdline = file('/proc/'+pid+'/cmdline').readline()
    # assume that a zero delimits the cmdline (it does now...)
    cmdline = cmdline.replace('\0', ' ')

    out = []
    try:
        uid=pwd.getpwuid(int(stdict['Uid'].split()[0]))[0][:8].ljust(8)
    except:
        uid=stdict['Uid'].split()[0][:8].ljust(8)
    out.append(uid)
    out.append(stdict['Pid'].rjust(5))
    out.append(stdict['PPid'].rjust(5))

    out2 = []
    out2.append(stdict['State'].split()[0])
    out2.append(policy[int(stat[statdef['rtpolicy']])])
    if stat[statdef['rtpolicy']] == '0':
        out2.append('th')
    elif stat[statdef['rtpolicy']] == '3':
        out2.append('at')
    else:
        if int(stat[statdef['rtpriority']]) < 10:
            out2.append('_')
            out2.append(stat[statdef['rtpriority']])
        else:
            out2.append(stat[statdef['rtpriority']].rjust(2))
    out.append(''.join(out2))

    try:
        os.readlink('/proc/'+pid+'/exe')
        #prog = stdict['Name'] + ' '.join(cmdline.split()[1:])
        prog = cmdline
    except:
        prog = '['+stdict['Name']+']'
    out.append(prog)

    if config.mread:
        l2 = []
        for line in out:
            l2.append(line.strip())
        return ';'.join(l2)

    out = ' '.join(out)
    if width != 0 and len(out) >= width:
        out = out[:width-3] + "..."

    return out

def task_detail_header(indent=None):
    if indent == None: istr = ""
    else: istr = indent
    l = []
    l.append(istr + 'USER       PID  PPID SPPr TASK NAME')
    l.append(istr + '-------- ----- ----- ---- ---------')
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
    if not config.mread:
        l.append(cset.summary(set))
        l.extend(task_detail_header(indent))
        l.extend(task_detail_table(set.tasks, indent, width))
    else:
        l.append('proc_list_start-' + set.name)
        l.extend(task_detail_table(set.tasks))
        l.append('proc_list_stop-' + set.name)
    log.info("\n".join(l))

