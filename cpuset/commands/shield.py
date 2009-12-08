"""Shield supercommand
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

import sys, os, logging
from optparse import OptionParser, make_option

from cpuset.commands.common import *
from cpuset.commands import proc
from cpuset.commands import set
from cpuset import cset
from cpuset.util import *

global log 
log = logging.getLogger('shield')

help = 'supercommand to set up and manage basic shielding'
usage = """%prog [options] [path/program]

This is a supercommand that creates basic cpu shielding.  The
normal cset commands can of course be used to create this basic
shield, but the shield command combines many such commands to
create and manage a common type of cpu shielding setup.

The concept of shielding implies at minimum three cpusets, for
example: root, user and system.  The root cpuset always exists in
all implementations of cpusets and contains all available CPUs on
the machine.  The system cpuset is so named because normal system
tasks are made to run on it.  The user cpuset is so named because
that is the "shielded" cpuset on which you would run your tasks
of interest.

Usually, CPU zero would be in the system set and the rest of the
CPUs would be in the user set.  After creation of the cpusets,
all processes running in the root cpuset are moved to the system
cpuset.  Thus any new processes or threads spawned from these
processes will also run the system cpuset.

If the optional --kthread=on option is given to the shield
command, then all kernel threads (with exception of the per-CPU
bound interrupt kernel threads) are also moved to the system set.

One executes processes on the shielded user cpuset with the
--exec subcommand or moves processes or threads to the shielded
cpuset with the --shield subcommand.  Note that you do not need to
specify which cpuset a process or thread is running in initially
when using the --shield subcommand.

To create a shield, you would execute the shield command with the
--cpu option that specifies CPUSPEC argument that assigns CPUs to
be under the shield (this means assigned to the user cpuset, all
other cpus will be assigned to the system set).

For example:
    # cset shield --cpu=3
        On a 4-way machine, this command will dedicate the first
        3 processors, CPU0-CPU2, for the system set (unshielded)
        and only the last processor, CPU3, for the user set
        (shielded).

The CPUSPEC will accept a comma separated list of CPUs and
inclusive range specifications.   For example, --cpu=1,3,5-7 will
assign CPU1, CPU3, CPU5, CPU6, and CPU7 to the user (or shielded)
cpuset.

If you do not like the names "system" and "user" for the
unshielded and shielded sets respectively, or if those names are
used already, then use the --sysset and --userset options.

For example:

 # cset shield --sysset=free --userset=cage --cpu=2,3 --kthread=on

The above command will use the name "free" for the unshielded
system cpuset, the name "cage" for the shielded user cpuset,
initialize these cpusets and dedicate CPU0 and CPU1 to the "free"
set and (on a 4-way machine) dedicate CPU2 and CPU3 to the "cage"
set.  Further, the command moves all processes and threads,
including kernel threads from the root cpuset to the "free"
cpuset.  Note however that if you do use the --syset/--userset
options, then you must continue to use those for every invocation
of the shield supercommand.

After initialization, you can run the process of interest on the
shielded cpuset with the --exec subcommand, or move processes or
threads already running to the shielded cpuset with the --shield
subcommand.

The PIDSPEC argument taken for the --shield (or -s) subcommand is
a comma separated list of PIDs or TIDs.  The list can also
include brackets of PIDs or TIDs that are inclusive of the
endpoints.

For example:
    1,2,5               Means processes 1, 2 and 5
    1,2,600-700         Means processes 1, 2 and from 600 to 700

    # cset shield --shield=50-65
        This command moves all processes and threads with PID or
        TID in the range 50-65 inclusive, from any cpuset they may
        be running in into the shielded user cpuset.

Note that the range of PIDs or TIDs does not need to have every
position populated.  In other words, for the example above, if
there is only one process, say PID 57, in the range of 50-65,
then only that process will be moved.

DANGER: Please note that there is no checking of processes you
request to move into the shield with the --shield command.  This
means that the tool will happily move, for example, kernel
threads that are bound to specific CPUs with this command. You
can hang your system by indiscriminately specifying arbitrary
PIDs to the --shield command so please be careful.

The --unshield (or -u) subcommand will remove the specified
processes or threads from the shielded cpuset and move them into
the unshielded (or system) cpuset.  This option also takes a
PIDSPEC argument, the same as for the --shield subcommand.

Both the --shield and the --unshield commands will also finally
output the number of tasks running in the shield and out of the
shield.  If you do not specify a PIDSPEC to these commands, then
just that status is output.  By specifying also a --verbose in
addition, then you will get a listing of every task that is
running in either the shield or out of the shield.

Using no subcommand, ie. only "cset shield", will output the
status of both shield and non-shield.  Tasks will be listed if
--verbose is used.

You can adjust which CPUs are in the shielded cpuset by issuing
the --cpu subcommand again anytime after the shield has been
initialized.  

For example if the original shield contained CPU0 and CPU1 in the
system set and CPU2 and CPU3 in the user set, if you then issue
the following command:
    
    # cset shield --cpu=1,2,3
    
then that command will move CPU1 into the shielded "user" cpuset.
Any processes or threads that were running on CPU1 that belonged
to the unshielded "system" cpuset are migrated to CPU0 by the
system.

The --reset subcommand will in essence destroy the shield.  For
example, if there was a shield on a 4-way machine with CPU0 in
system and CPUs 1-3 in user with processes running on the user
cpuset (i.e. in the shield), and a --reset subcommand was issued,
then all processes running in both system and user cpusets would
be migrated to the root cpuset (which has access to all CPUs and
never goes away), after which both system and user cpusets would
be destroyed.

Note that even though you can mix general usage of cpusets with
the shielding concepts described here, you generally will not
want to.  For more complex shielding or usage scenarios, one
would generally use the normal cpuset commands (i.e. cset set
and proc) directly."""

USR_SET = '/user'
SYS_SET = '/system'
verbose = 0

# callback for --shield/--unshield, allows optional argument
# if no arg, then status of either shield or unshield is displayed
def shield_cb(option, opt_str, value, parser):
    if value == None:
        try:
            arg = parser.rargs[0]
            if arg[0] != '-':
                # assign and consume argument
                value = arg
                del parser.rargs[0]
            else:
                value = True
        except IndexError, err:
            # no further arguments
            value = True
        except:
            raise
    setattr(parser.values, option.dest, value)

options = [make_option('-c', '--cpu',
                       metavar = 'CPUSPEC',
                       help = 'modifies or initializes the shield cpusets'),
           make_option('-r', '--reset',
                       help = 'destroys the shield',
                       action = 'store_true'),
           make_option('-e', '--exec',
                       help = 'executes args in the shield',
                       dest = 'exc',
                       action = 'store_true'),
            make_option('--user',
                       help = 'use this USER for --exec (id or name)'),
            make_option('--group',
                       help = 'use this GROUP for --exec (id or name)'),
           make_option('-s', '--shield',
                       action = 'callback',
                       callback=shield_cb,
                       dest = 'shield',
                       metavar = 'PIDSPEC',
                       help = 'shield specified PIDSPEC of processes or threads'),
           make_option('-u', '--unshield',
                       action = 'callback',
                       callback=shield_cb,
                       dest = 'unshield',
                       metavar = 'PIDSPEC',
                       help = 'remove specified PIDSPEC of processes or threads from shield'),
           make_option('-k', '--kthread',
                       metavar = 'on|off',
                       choices = ['on', 'off'],
                       help = 'shield from unbound interrupt threads as well'),
           make_option('-f', '--force',
                       help = 'force operation, use with care',
                       action = 'store_true'),
           make_option('-v', '--verbose',
                       help = 'prints more detailed output, additive',
                       action = 'count'),
           make_option('--sysset',
                       help = 'optionally specify system cpuset name'),
           make_option('--userset',
                       help = 'optionally specify user cpuset name')
          ]

def func(parser, options, args):
    log.debug("entering shield, options=%s, args=%s", options, args)
    global verbose
    if options.verbose: verbose = options.verbose
    cset.rescan()

    if options.sysset: 
        global SYS_SET
        SYS_SET = options.sysset
    if options.userset: 
        global USR_SET
        USR_SET = options.userset

    if (not options.cpu and not options.reset and not options.exc and
        not options.shield and not options.unshield and not options.kthread):
        shield_exists()
        if len(args) == 0:
            log.info("--> shielding system active with")
            print_all_stats()
        else:
            exec_args(args, options.user, options.group)
        return
        
    if options.reset: 
        reset_shield()
        return

    # note that the following options fall through to others
    # to allow for multiple options/commands on one cmdline
    if options.cpu: make_shield(options.cpu, options.kthread)

    elif options.kthread: make_kthread(options.kthread)

    if options.exc: exec_args(args, options.user, options.group)

    if options.shield: 
        shield_exists()
        try:
            log.info('--> shielding following pidspec: %s', options.shield)
            if options.force:
                proc.move_pidspec(options.shield, USR_SET)
            else:
                proc.move_pidspec(options.shield, USR_SET, SYS_SET)
            log.info('done')
        except Exception, err:
            if str(err).find('Permission denied') != -1:
                raise
            if options.shield != True:
                log.info(err)
                log.info('--> bad pidspec: %s, shield state is:', options.shield)
            else:
                log.info('--> shielded state is:')
            print_usr_stats()

    if options.unshield: 
        shield_exists()
        try:
            log.info('--> unshielding following pidspec: %s', options.unshield)
            if options.force:
                proc.move_pidspec(options.unshield, SYS_SET)
            else:
                proc.move_pidspec(options.unshield, SYS_SET, USR_SET)
            log.info('done')
        except Exception, err:
            if str(err).find('Permission denied') != -1:
                raise
            if options.unshield != True:
                log.info('--> bad pidspec: %s, unshielded state is:', options.unshield)
            else:
                log.info('--> not shielded state is:')
            print_sys_stats()

def print_all_stats():
    print_sys_stats()
    print_usr_stats()

def print_sys_stats():
    if verbose and len(cset.unique_set(SYS_SET).tasks) > 0:
        if verbose == 1:
            proc.log_detailed_task_table(cset.unique_set(SYS_SET), '   ', 76)
        else:
            proc.log_detailed_task_table(cset.unique_set(SYS_SET), '   ')
    else:
        log.info(cset.summary(cset.unique_set(SYS_SET)))

def print_usr_stats():
    if verbose and len(cset.unique_set(USR_SET).tasks) > 0:
        if verbose == 1:
            proc.log_detailed_task_table(cset.unique_set(USR_SET), '   ', 76)
        else:
            proc.log_detailed_task_table(cset.unique_set(USR_SET), '   ')
    else:
        log.info(cset.summary(cset.unique_set(USR_SET)))

def shield_exists():
    try:
        cset.unique_set(USR_SET)
        cset.unique_set(SYS_SET)
        return True
    except CpusetNotFound:
        log.info('can\'t find "%s" and "%s" cpusets on system...', SYS_SET, USR_SET)
        raise CpusetException('--> shielding not active on system')

def reset_shield():
    log.info("--> deactivating/reseting shielding")
    shield_exists()
    tasks = cset.unique_set(USR_SET).tasks
    log.info('moving %s tasks from "%s" user set to root set...', 
             len(tasks), USR_SET)
    proc.move(USR_SET, 'root')
    tasks = cset.unique_set(SYS_SET).tasks
    log.info('moving %s tasks from "%s" system set to root set...', 
             len(tasks), SYS_SET)
    proc.move(SYS_SET, 'root')
    log.info('deleting "%s" and "%s" sets', USR_SET, SYS_SET)
    set.destroy(USR_SET)
    set.destroy(SYS_SET)
    log.info('done')

def make_shield(cpuspec, kthread):
    memspec = '0' # FIXME: for numa, we probably want a more intelligent scheme
    log.debug("entering make_shield, cpuspec=%s kthread=%s", cpuspec, kthread)
    # create base cpusets for shield
    cset.cpuspec_check(cpuspec)
    cpuspec_inv = cset.cpuspec_inverse(cpuspec)
    try:
        shield_exists()
    except:
        log.debug("shielding does not exist, creating")
        try:
            set.create(USR_SET, cpuspec, memspec, True, False)
            set.create(SYS_SET, cpuspec_inv, memspec, True, False)
        except Exception, instance:
            # unroll
            try: set.destroy(USR_SET)
            except: pass
            try: set.destroy(SYS_SET)
            except: pass
            log.critical('--> failed to create shield, hint: do other cpusets exist?')
            raise instance
        log.info('--> activating shielding:')
    else:
        log.debug("shielding exists, modifying cpuspec")
        # note, since we're going to modify the cpu assigments to these sets,
        # they cannot be exclusive, the following modify() calls will make
        # them exclusive again
        cset.unique_set(USR_SET).cpu_exclusive = False
        cset.unique_set(SYS_SET).cpu_exclusive = False
        set.modify(USR_SET, cpuspec, memspec, False, False)
        set.modify(SYS_SET, cpuspec_inv, memspec, False, False)
        # reset cpu exlusivity
        cset.unique_set(USR_SET).cpu_exclusive = True
        cset.unique_set(SYS_SET).cpu_exclusive = True
        log.info('--> shielding modified with:')
    # move root tasks into system set
    root_tasks = cset.unique_set('/').tasks
    log.debug("number of root tasks are: %s", len(root_tasks))
    # figure out what in root set is not a kernel thread
    tasks = []
    for task in root_tasks:
        try:
            os.readlink('/proc/'+task+'/exe')
            tasks.append(task)
        except:
            pass
    if len(tasks) != 0:
        log.info("moving %s tasks from root into system cpuset...", len(tasks))
    proc.move('root', SYS_SET, tasks)
    # move kernel theads into system set if asked for
    if kthread == 'on':
        root_tasks = cset.unique_set('/').tasks
        tasks = []
        for task in root_tasks:
            try:
                if proc.is_unbound(task): tasks.append(task)
            except:
                pass
        if len(tasks) != 0:
            log.info("kthread shield activated, moving %s tasks into system cpuset...",
                     len(tasks))
        proc.move('root', SYS_SET, tasks)
    # print out stats
    print_all_stats()

def make_kthread(state):
    log.debug("entering make_kthread, state=%s", state)
    shield_exists()
    if state == 'on':
        log.info('--> activating kthread shielding')
        root_tasks = cset.unique_set('/').tasks
        log.debug('root set has %d tasks, checking for unbound', 
                  len(root_tasks))
        tasks = []
        for task in root_tasks:
            try:
                if proc.is_unbound(task): tasks.append(task)
            except:
                pass
        if len(tasks) != 0:
            log.debug("total root tasks %s", len(root_tasks))
            log.info("kthread shield activated, moving %s tasks into system cpuset...",
                     len(tasks))
            proc.move('root', SYS_SET, tasks)
            if verbose == 1:
                proc.log_detailed_task_table(tasks, '   ', 76)
            elif verbose > 1:
                proc.log_detailed_task_table(tasks, '   ')
    else:
        log.info('--> deactivating kthread shielding')
        usr_tasks = cset.unique_set(SYS_SET).tasks
        tasks = []
        for task in usr_tasks:
            try:
                os.readlink('/proc/'+task+'/exe')
            except:
                tasks.append(task)
        if len(tasks) != 0:
            log.info("moving %s tasks into root cpuset...", len(tasks))
        proc.move(SYS_SET, '/', tasks)
        if verbose == 1:
            proc.log_detailed_task_table(tasks, '   ', 76)
        elif verbose > 1:
            proc.log_detailed_task_table(tasks, '   ')
    log.info('done')

def exec_args(args, upar, gpar):
    log.debug("entering exec_args, args=%s", args)
    shield_exists()
    proc.run(USR_SET, args, upar, gpar)

