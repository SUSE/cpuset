"""Cpuset manipulation command
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

from cpuset import cset
from cpuset.util import *
from cpuset.commands.common import *
try: from cpuset.commands import proc
except: pass

global log
log = logging.getLogger('set')

help = 'create, modify and destroy cpusets'
usage = """%prog [options] [cpuset name]

This command is used to create, modify, and destroy cpusets.
Cpusets form a tree-like structure rooted at the root cpuset
which always includes all system CPUs and all system memory
nodes.

A cpuset is an organizational unit that defines a group of CPUs
and a group of memory nodes where a process or thread (i.e. task)
is allowed to run on.  For non-NUMA machines, the memory node is
always 0 (zero) and cannot be set to anything else.  For NUMA
machines, the memory node can be set to a similar specifcation
as the CPU definition and will tie those memory nodes to that
cpuset.  You will usually want the memory nodes that belong to
the CPUs defined to be in the same cpuset.

A cpuset can have exclusive right to the CPUs defined in it.
This means that only this cpuset can own these CPUs.  Similarly,
a cpuset can have exclusive right to the memory nodes defined in
it.  This means that only this cpuset can own these memory
nodes.

Cpusets can be specified by name or by path; however, care
should be taken when specifying by name if the name is not
unique.  This tool will generally not let you do destructive
things to non-unique cpuset names.

Cpusets are uniquely specified by path.  The path starts at where
the cpusets filesystem is mounted so you generally do not have to
know where that is.  For example, so specify a cpuset that is
called "two" which is a subset of "one" which in turn is a subset
of the root cpuset, use the path "/one/two" regardless of where
the cpusets filesystem is mounted.

When specifying CPUs, a so-called CPUSPEC is used.  The CPUSPEC
will accept a comma-separated list of CPUs and inclusive range
specifications.   For example, --cpu=1,3,5-7 will assign CPU1,
CPU3, CPU5, CPU6, and CPU7 to the specified cpuset.

Note that cpusets follow certain rules.  For example, children
can only include CPUs that the parents already have.  If you do
not follow those rules, the kernel cpuset subsystem will not let
you create that cpuset.  For example, if you create a cpuset that
contains CPU3, and then attempt to create a child of that cpuset
with a CPU other than 3, you will get an error, and the cpuset
will not be active.  The error is somewhat cryptic in that it is
usually a "Permission denied" error.

Memory nodes are specified with a MEMSPEC in a similar way to
the CPUSPEC.  For example, --mem=1,3-6 will assign MEM1, MEM3,
MEM4, MEM5, and MEM6  to the specified cpuset.

Note that if you attempt to create or modify a cpuset with a
memory node specification that is not valid, you may get a
cryptic error message, "No space left on device", and the
modification will not be allowed.

When you destroy a cpuset, then the tasks running in that set are
moved to the parent of that cpuset.  If this is not what you
want, then manually move those tasks to the cpuset of your choice
with the 'cset proc' command (see 'cset proc --help' for more
information).

EXAMPLES

Create a cpuset with the default memory specification:

    # cset set --cpu=2,4,6-8 --set=new_set

        This command creates a cpuset called "new_set" located
        off the root cpuset which holds CPUS 2,4,6,7,8 and node 0
        (interleaved) memory.  Note that --set is optional, and
        you can just specify the name for the new cpuset after
        all arguments.

Create a cpuset that specifies both CPUs and memory nodes:

    # cset set --cpu=3 --mem=3 /rad/set_one

        Note that this command uses the full path method to
        specify the name of the new cpuset "/rad/set_one". It
        also names the new cpuset implicitily (i.e. no --set
        option, although you can use that if you want to).  If
        the "set_one" name is unique, you can subsequently refer
        to is just by that.  Memory node 3 is assigned to this
        cpuset as well as CPU 3.

The above commands will create the new cpusets, or if they
already exist, they will modify them to the new specifications."""

verbose = 0
options = [make_option('-l', '--list',
                       help = 'list the named cpuset(s); recursive list if also -r; '
                              'members if also -a',
                       action = 'store_true'),
           make_option('-c', '--cpu',
                       help = 'create or modify cpuset in the specified '
                              'cpuset with CPUSPEC specification',
                       metavar = 'CPUSPEC'),
           make_option('-m', '--mem',
                       help = 'specify which memory nodes to assign '
                              'to the created or modified cpuset',
                       metavar = 'MEMSPEC'),
           make_option('-d', '--destroy',
                       help = 'destroy specified cpuset',
                       action = 'store_true'),
           make_option('-s', '--set',
                       metavar = 'CPUSET',
                       help = 'specify cpuset'),
           make_option('-a', '--all',
                       help = 'also do listing of member cpusets',
                       action = 'store_true'),
           make_option('-r', '--recurse',
                       help = 'do recursive listing, for use with --list',
                       action = 'store_true'),
           make_option('-v', '--verbose',
                       help = 'prints more detailed output, additive',
                       action = 'count'),
           make_option('--cpu_exclusive',
                       help = 'mark this cpuset as owning its CPUs exclusively',
                       action = 'store_true'),
           make_option('--mem_exclusive',
                       help = 'mark this cpuset as owning its MEMs exclusively',
                       action = 'store_true'),
          ]

def func(parser, options, args):
    log.debug("entering func, options=%s, args=%s", options, args)
    global verbose
    if options.verbose: verbose = options.verbose

    cset.rescan()

    if options.list:
        if options.set:
            list_sets(options.set, options.recurse, options.all)
            return
        if len(args): list_sets(args, options.recurse, options.all)
        else: list_sets('root', options.recurse, options.all)
        return

    if options.cpu or options.mem:
        # create or modify cpuset
        create_from_options(options, args)
        return

    if options.destroy:
        if options.set: destroy_sets(options.set)
        else: destroy_sets(args)
        return

    if options.cpu_exclusive or options.mem_exclusive:
        # modification of existing cpusets for exclusivity
        return

    # default behavior if no options specified is list
    log.debug('no options set, default is listing cpusets')
    if len(args): list_sets(args, options.recurse, options.all)
    else: list_sets('root', options.recurse, options.all)

def list_sets(tset, recurse=None, members=None):
    log.debug('entering list_sets, tset=%s recurse=%s', tset, recurse)
    sl = []
    if isinstance(tset, list):
        for s in tset: sl.extend(cset.find_sets(s))
    else:
        sl.extend(cset.find_sets(tset))
    log.debug('total unique sets in passed tset: %d', len(sl))
    if recurse: members = True
    if members:
        sl2 = []
        for s in sl:
            sl2.append(s)
            if len(s.subsets) > 0:
                sl2.extend(s.subsets)
            if recurse:
                for node in s.subsets:
                    for nd in cset.walk_set(node):
                        sl2.append(nd)
        sl = sl2
    pl = ['']
    pl.extend(set_header('   '))
    for s in sl:
        if verbose:
            pl.append(set_details(s,'   ', 0))
        else:
            pl.append(set_details(s,'   '))
    log.info("\n".join(pl))

def destroy_sets(sets):
    log.debug('enter destroy_sets, sets=%s', sets)
    nl = []
    try:
        nl.extend(sets)
    except:
        nl.append(sets)
    # check that sets passed are ok, will raise if one is bad
    for s in nl: 
        st = cset.unique_set(s)
        if len(st.subsets) > 0:
            raise CpusetException('cpuset "%s" has subsets, delete them first'
                                  % st.path)
    # ok, good to go
    for s in nl:
        s = cset.unique_set(s)
        log.info('--> processing cpuset "%s", moving %s tasks to parent "%s"...',
                 s.name, len(s.tasks), s.parent.path)
        proc.move(s, s.parent)
        log.info('deleting cpuset "%s"', s.path)
        destroy(s)
    log.info('done')

def destroy(name):
    log.debug('entering destroy, name=%s', name)
    if isinstance(name, str):
        set = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException(
                "passed name=%s, which is not a string or CpuSet" % name) 
    else:
        set = name
    if len(set.tasks) > 0:
        log.debug('%i tasks still running in set %s', len(set.tasks), name)
        raise CpusetException(
                "trying to destroy cpuset %s with tasks running" % name)
    os.rmdir(cset.CpuSet.basepath+set.path)
    # fixme: perhaps reparsing the all the sets is not so efficient...
    cset.rescan()

def create_from_options(options, args):
    log.debug('entering create_from_options, options=%s args=%s', options, args)
    # figure out target cpuset name, if --set not used, use first arg
    if options.set:
        tset = options.set
    elif len(args) > 0:
        tset = args[0]
    else:
        raise CpusetException('cpuset not specified')
    cspec = None
    mspec = None
    cx = None
    mx = None
    if options.cpu: 
        cset.cpuspec_check(options.cpu)
        cspec = options.cpu
    if options.mem:
        cset.memspec_check(options.mem)
        mspec = options.mem
    if options.cpu_exclusive: cx = options.cpu_exclusive
    if options.mem_exclusive: mx = options.mem_exclusive
    try:
        create(tset, cspec, mspec, cx, mx)
        if not mspec: modify(tset, memspec='0') # always need at least this
        log.info('--> created cpuset "%s"', tset)
    except CpusetExists:
        modify(tset, cspec, mspec, cx, mx)
        log.info('--> modified cpuset "%s"', tset)
    active(tset)

def create(name, cpuspec, memspec, cx, mx):
    log.debug('entering create, name=%s cpuspec=%s memspec=%s cx=%s mx=%s',
              name, cpuspec, memspec, cx, mx)
    try:
        cset.unique_set(name)
    except CpusetNotFound:
       pass 
    except:
        raise CpusetException('cpuset "%s" not unique, please specify by path' % name)
    else:
        raise CpusetExists('attempt to create already existing set: "%s"' % name) 
    # FIXME: check if name is a path here
    os.mkdir(cset.CpuSet.basepath+'/'+name)
    # fixme: perhaps reparsing the all the sets is not so efficient...
    cset.rescan()
    log.debug('created new cpuset "%s"', name)
    modify(name, cpuspec, memspec, cx, mx)

def modify(name, cpuspec=None, memspec=None, cx=None, mx=None):
    log.debug('entering modify, name=%s cpuspec=%s memspec=%s cx=%s mx=%s',
              name, cpuspec, memspec, cx, mx)
    if isinstance(name, str):
        nset = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException(
                "passed name=%s, which is not a string or CpuSet" % name) 
    else:
        nset = name
    log.debug('modifying cpuset "%s"', nset.name)
    if cpuspec: nset.cpus = cpuspec
    if memspec: nset.mems = memspec
    if cx: nset.cpu_exclusive = cx
    if mx: nset.mem_exclusive = mx

def active(name):
    log.debug("entering active, name=%s", name)
    if isinstance(name, str):
        set = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException("passing bogus name=%s" % name)
    else:
        set = name
    if set.cpus == '':
        raise CpusetException('"%s" cpuset not active, no cpus defined' % set.path)
    if set.mems == '':
        raise CpusetException('"%s" cpuset not active, no mems defined' % set.path)

def set_header(indent=None):
    if indent: istr = indent
    else: istr = ''
    l = []
    #               '1234567890-1234567890-1234567890-1234567890-1234567890'
    l.append(istr + '        Name       CPUs-X    MEMs-X Tasks Subs Path')
    l.append(istr + '------------ ---------- - ------- - ----- ---- ----------')
    return l

def set_details(name, indent=None, width=75):
    if isinstance(name, str):
        set = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException("passing bogus set=%s" % name)
    else:
        set = name
    if indent: istr = indent
    else: istr = ''
    l = []
    used = 0
    l.append(istr)
    used += len(istr)
    l.append(set.name.rjust(12))
    used += 12
    cs = set.cpus
    if cs == '': cs = '*****'
    l.append(cs.rjust(11))
    used += 11 
    if set.cpu_exclusive:
        l.append(' y')
    else:
        l.append(' n')
    used += 2
    cs = set.mems
    if cs == '': cs = '*****'
    l.append(cs.rjust(8))
    used += 8
    if set.mem_exclusive:
        l.append(' y')
    else:
        l.append(' n')
    used += 2
    l.append(str(len(set.tasks)).rjust(6))
    used += 6
    l.append(str(len(set.subsets)).rjust(5))
    used += 5
    l.append(' ')
    used += 1
    if width == 0:
        l.append(set.path)
    else:
        l.append(set.path[:(width-used)])
    return ''.join(l)
