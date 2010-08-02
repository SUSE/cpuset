"""Cpuset manipulation command
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

import sys, os, logging, time
from optparse import OptionParser, make_option

from cpuset import config
from cpuset import cset
from cpuset.util import *
from cpuset.commands.common import *
try: from cpuset.commands import proc
except SyntaxError:
    raise
except: 
    pass

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
machines, the memory node can be set to a similar specification
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
        also names the new cpuset implicitly (i.e. no --set
        option, although you can use that if you want to).  If
        the "set_one" name is unique, you can subsequently refer
        to is just by that.  Memory node 3 is assigned to this
        cpuset as well as CPU 3.

The above commands will create the new cpusets, or if they
already exist, they will modify them to the new specifications."""

verbose = 0
options = [make_option('-l', '--list',
                       help = 'list the named cpuset(s); recursive list if also -r',
                       action = 'store_true'),
           make_option('-c', '--cpu',
                       help = 'create or modify cpuset in the specified '
                              'cpuset with CPUSPEC specification',
                       metavar = 'CPUSPEC'),
           make_option('-m', '--mem',
                       help = 'specify which memory nodes to assign '
                              'to the created or modified cpuset (optional)',
                       metavar = 'MEMSPEC'),
           make_option('-n', '--newname',
                       help = 'rename cpuset specified with --set to NEWNAME'),
           make_option('-d', '--destroy',
                       help = 'destroy specified cpuset',
                       action = 'store_true'),
           make_option('-s', '--set',
                       metavar = 'CPUSET',
                       help = 'specify cpuset'),
           make_option('-r', '--recurse',
                       help = 'do things recursively, use with --list and --destroy',
                       action = 'store_true'),
           make_option('--force',
                       help = 'force recursive deletion even if processes are running ' 
                              'in those cpusets (they will be moved to parent cpusets)',
                       action = 'store_true'),
           make_option('-x', '--usehex',
                       help = 'use hexadecimal value for CPUSPEC and MEMSPEC when '
                              'listing cpusets',
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
            list_sets(options.set, options.recurse, options.usehex)
            return
        if len(args): list_sets(args, options.recurse, options.usehex)
        else: list_sets('root', options.recurse, options.usehex)
        return

    if options.cpu or options.mem:
        # create or modify cpuset
        create_from_options(options, args)
        return

    if options.newname:
        rename_set(options, args)
        return

    if options.destroy:
        if options.set: destroy_sets(options.set, options.recurse, options.force)
        else: destroy_sets(args, options.recurse, options.force)
        return

    if options.cpu_exclusive or options.mem_exclusive:
        # FIXME: modification of existing cpusets for exclusivity
        log.info("Modification of cpu_exclusive and mem_exclusive not implemented.")
        return

    # default behavior if no options specified is list
    log.debug('no options set, default is listing cpusets')
    if options.set: list_sets(options.set, options.recurse, options.usehex)
    elif len(args): list_sets(args, options.recurse, options.usehex)
    else: list_sets('root', options.recurse, options.usehex)

def list_sets(tset, recurse=None, usehex=False):
    """list cpusets specified in tset as cpuset or list of cpusets, recurse if true"""
    log.debug('entering list_sets, tset=%s recurse=%s', tset, recurse)
    sl = []
    if isinstance(tset, list):
        for s in tset: sl.extend(cset.find_sets(s))
    else:
        sl.extend(cset.find_sets(tset))
    log.debug('total unique sets in passed tset: %d', len(sl))
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
    if config.mread:
        pl = ['cpuset_list_start']
    else:
        pl = ['']
        pl.extend(set_header(' '))

    for s in sl:
        if verbose:
            pl.append(set_details(s,' ', None, usehex))
        else:
            pl.append(set_details(s,' ', 78, usehex))

    if config.mread:
        pl.append('cpuset_list_end')
    log.info("\n".join(pl))

def destroy_sets(sets, recurse=False, force=False):
    """destroy cpusets in list of sets, recurse if true, if force destroy if tasks running"""
    log.debug('enter destroy_sets, sets=%s, force=%s', sets, force)
    nl = []
    if isinstance(sets, list):
        nl.extend(sets)
    else:
        nl.append(sets)
    # check that sets passed are ok, will raise if one is bad
    sl2 = []
    for s in nl: 
        st = cset.unique_set(s)
        sl2.append(st)
        if len(st.subsets) > 0:
            if not recurse:
                raise CpusetException(
                        'cpuset "%s" has subsets, delete them first, or use --recurse'
                        % st.path)
            elif not force:
                raise CpusetException(
                        'cpuset "%s" has subsets, use --force to destroy'
                        % st.path)
            sl2.extend(st.subsets)
            for node in st.subsets:
                for nd in cset.walk_set(node):
                    sl2.append(nd)

    # ok, good to go
    if recurse: sl2.reverse()
    for s in sl2:
        s = cset.unique_set(s)
        # skip the root set!!! or you'll have problems...
        if s.path == '/': continue
        log.info('--> processing cpuset "%s", moving %s tasks to parent "%s"...',
                 s.name, len(s.tasks), s.parent.path)
        proc.move(s, s.parent)
        log.info('--> deleting cpuset "%s"', s.path)
        destroy(s)
    log.info('done')

def destroy(name):
    """destroy one cpuset by name as cset or string"""
    log.debug('entering destroy, name=%s', name)
    if isinstance(name, str):
        set = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException(
                "passed name=%s, which is not a string or CpuSet" % name) 
    else:
        set = name
    tsks = set.tasks
    if len(tsks) > 0:
        # wait for tasks, sometimes it takes a little while to
        # have them leave the set
        ii = 0
        while len(tsks)>0:
            log.debug('%i tasks still running in set %s, waiting interval %s...',
                      len(tsks), set.name, ii+1)
            time.sleep(0.5)
            tsks = set.tasks
            ii += 1
            if (ii) > 6:
                # try it for 3 seconds, bail if tasks still there
                raise CpusetException(
                    "trying to destroy cpuset %s with tasks running: %s" %
                    (set.path, set.tasks))
    log.debug("tasks expired, deleting set %s" % set.path)
    os.rmdir(cset.CpuSet.basepath+set.path)
    # fixme: perhaps reparsing the all the sets is not so efficient...
    cset.rescan()

def rename_set(options, args):
    """rename cpuset as specified in options and args lists"""
    log.debug('entering rename_set, options=%s args=%s', options, args)
    # figure out target cpuset name, if --set not used, use first arg
    name = options.newname
    if options.set:
        tset = cset.unique_set(options.set)
    elif len(args) > 0:
        tset = cset.unique_set(args[0])
    else:
        raise CpusetException('desired cpuset not specified')
    path = tset.path[0:tset.path.rfind('/')+1]
    log.debug('target set="%s", path="%s", name="%s"', tset.path, path, name)
    try:
        if name.find('/') == -1:
            chk = cset.unique_set(path+name)
        else:
            if name[0:name.rfind('/')+1] != path:
                raise CpusetException('desired name cannot have different path')
            chk = cset.unique_set(name)
        raise CpusetException('cpuset "'+chk.path+'" already exists')
    except CpusetNotFound:
        pass
    except:
        raise

    if name.rfind('/') != -1:
        name = name[name.rfind('/')+1:]
    log.info('--> renaming "%s" to "%s"', cset.CpuSet.basepath+tset.path, name)
    os.rename(cset.CpuSet.basepath+tset.path, cset.CpuSet.basepath+path+name)
    cset.rescan()

def create_from_options(options, args):
    """create cpuset as specified by options and args lists"""
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
    """create one cpuset by name, cpuspec, memspec, cpu and mem exclusive flags"""
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
    """modify one cpuset by name, cpuspec, memspec, cpu and mem exclusive flags"""
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
    """check that cpuset by name or cset is ready to be used"""
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
    """return list of cpuset output header"""
    if indent: istr = indent
    else: istr = ''
    l = []
    #               '123456789-123456789-123456789-123456789-123456789-123456789-'
    l.append(istr + '        Name       CPUs-X    MEMs-X Tasks Subs Path')
    l.append(istr + '------------ ---------- - ------- - ----- ---- ----------')
    return l

def set_details(name, indent=None, width=None, usehex=False):
    """return string of cpuset details"""
    if width == None: width = 0
    if isinstance(name, str):
        set = cset.unique_set(name)
    elif not isinstance(name, cset.CpuSet):
        raise CpusetException("passing bogus set=%s" % name)
    else:
        set = name

    l = []
    l.append(set.name.rjust(12))
    cs = set.cpus
    if cs == '': cs = '*****'
    elif usehex: cs = cset.cpuspec_to_hex(cs)
    l.append(cs.rjust(10))
    if set.cpu_exclusive:
        l.append('y')
    else:
        l.append('n')
    cs = set.mems
    if cs == '': cs = '*****'
    elif usehex: cs = cset.cpuspec_to_hex(cs)
    l.append(cs.rjust(7))
    if set.mem_exclusive:
        l.append('y')
    else:
        l.append('n')
    l.append(str(len(set.tasks)).rjust(5))
    l.append(str(len(set.subsets)).rjust(4))

    if config.mread:
        l.append(set.path)
        l2 = []
        for line in l: 
            l2.append(line.strip())
        return ';'.join(l2)

    out = ' '.join(l) + ' '
    tst = out + set.path

    if width != 0 and len(tst) > width:
        target = width - len(out)
        patha = set.path[:len(set.path)/2-3]
        pathb = set.path[len(set.path)/2:]
        patha = patha[:target/2-3]
        pathb = pathb[-target/2:]
        out += patha + '...' + pathb
    else:
        out = tst

    if indent: istr = indent
    else: istr = ''
    return istr + out
