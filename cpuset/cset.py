"""Cpuset class and cpuset graph, importing module will create model
"""

__copyright__ = """
Copyright (C) 2007-2010 Novell Inc.
Author: Alex Tsariounov <alext@novell.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import os, re, sys, logging

if __name__ == '__main__': 
    sys.path.insert(0, "..")
    logging.basicConfig()

from cpuset.util import *
log = logging.getLogger('cset')
RootSet = None

class CpuSet(object):
    # sets is a class variable dict that keeps track of all 
    # cpusets discovered such that we can link them in properly.
    # The basepath is it's base path, the sets are indexed via
    # a relative path from this basepath.
    sets = {}
    basepath = ''

    def __init__(self, path=None):
        log.debug("initializing CpuSet")
        if (path == None):
            # recursively find all cpusets and link together
            # note: a breadth-first search could do this in one
            #       pass, but there are never many cpusets, so
            #       that optimization is left for the future
            log.debug("finding all cpusets")
            path = self.locate_cpusets()
            CpuSet.basepath = path
            log.debug("creating root node at %s", path)
            self.__root = True
            self.name = 'root'
            self.path = '/'
            self.parent = self
            if (CpuSet.sets): 
                del CpuSet.sets
                CpuSet.sets = {}
            CpuSet.sets[self.path] = self
            # bottom-up search otherwise links will not exist
            log.debug("starting bottom-up discovery walk...")
            for dir, dirs, files in os.walk(path, topdown=False):
                log.debug("*** walking %s", dir)
                if dir != CpuSet.basepath:
                    node = CpuSet(dir)
                else:
                    node = self
                node.subsets = []
                for sub in dirs:
                    if len(sub) > 0:
                        relpath = os.path.join(dir,sub).replace(CpuSet.basepath, '')
                    else:
                        relpath = '/'
                    node.subsets.append(CpuSet.sets[relpath])
                log.debug("%s has %i subsets: [%s]", dir, 
                          len(node.subsets), '|'.join(dirs))

            log.debug("staring top-down parenting walk...")
            for dir, dirs, files in os.walk(path):
                dir = dir.replace(CpuSet.basepath, '')
                if len(dir) == 0: dir = '/'
                node = CpuSet.sets[dir]
                log.debug("~~~ walking %s", node.path)
                if dir == '/':
                    log.debug("parent is self (root cpuset), skipping")
                else:
                    parpath = dir[0:dir.rfind('/')]
                    log.debug('parpath decodes to: %s from dir of: %s', parpath, dir)
                    if CpuSet.sets.has_key(parpath):
                        log.debug("parent is %s", parpath)
                        node.parent = CpuSet.sets[parpath]
                    else:
                        log.debug("parent is root cpuset")
                        node.parent = CpuSet.sets['/']
            log.debug("found %i cpusets", len(CpuSet.sets))
        else:
            # one new cpuset node
            log.debug("new cpuset node absolute: %s", path)
            if len(path) > len(CpuSet.basepath):
                path = path.replace(CpuSet.basepath, '')
            else:
                path = '/'
            log.debug(" relative: %s", path)
            if CpuSet.sets.has_key(path):
                log.debug("the cpuset %s already exists, skipping", path)
                self = CpuSet.sets[path]  # questionable....
                return
            cpus = CpuSet.basepath + path + "/cpus"
            if not os.access(cpus, os.F_OK):
                # not a cpuset directory
                str = '%s is not a cpuset directory' % (CpuSet.basepath + path)
                log.error(str)
                raise CpusetException(str)
            self.__root = False
            self.read_cpuset(path)
            CpuSet.sets[path] = self

    def locate_cpusets(self):
        log.debug("locating cpuset filesystem...")
        cpuset = re.compile(r"none (/.+) cpuset .+")
        cgroup = re.compile(r"none (/.+) cgroup .+")
        path = None
        f = file("/proc/mounts")
        for line in f:
            res = cpuset.search(line)
            if res:
                path = res.group(1)
                break
            else:
                if cgroup.search(line):
                    groups = line.split()
                    if re.search("cpuset", groups[3]):
                        path = groups[1]
                        break
        f.close()

        if not path:
            # mounted cpusets not found, so mount them

            if not os.access(config.mountpoint, os.F_OK):
                os.mkdir(config.mountpoint)
            ret = os.system("mount -t cpuset none " + config.mountpoint)
            if ret:
               raise CpusetException(
                     'mount of cpuset filesystem failed, do you have permission?')
            path = config.mountpoint
        log.debug("cpusets mounted at: " + path)
        return path

    def read_cpuset(self, path):
        log.debug("reading cpuset passed relpath: %s", path)
        self.path = path
        log.debug("...path=%s", path)
        self.name = path[path.rfind('/')+1:]
        log.debug("...name=%s", self.name)

    # Properties of cpuset node
    def delprop(self):
        raise AttributeError, "deletion of properties not allowed"

    def getcpus(self): 
        f = file(CpuSet.basepath+self.path+"/cpus")
        return f.readline()[:-1]
    def setcpus(self, newval):
        cpuspec_check(newval)
        f = file(CpuSet.basepath+self.path+"/cpus",'w')
        f.write(str(newval))
        f.close()
        log.debug("-> prop_set %s.cpus = %s", self.path, newval) 
    cpus = property(fget=getcpus, fset=setcpus, fdel=delprop, doc="CPU specifier")

    def getmems(self): 
        f = file(CpuSet.basepath+self.path+"/mems")
        return f.readline()[:-1]
    def setmems(self, newval): 
        # FIXME: check format for correctness
        f = file(CpuSet.basepath+self.path+"/mems",'w')
        f.write(str(newval))
        f.close()
        log.debug("-> prop_set %s.mems = %s", self.path, newval) 
    mems = property(getmems, setmems, delprop, "Mem node specifier")
    
    def getcpuxlsv(self): 
        f = file(CpuSet.basepath+self.path+"/cpu_exclusive")
        if f.readline()[:-1] == '1':
            return True
        else:
            return False
    def setcpuxlsv(self, newval):
        log.debug("-> prop_set %s.cpu_exclusive = %s", self.path, newval) 
        f = file(CpuSet.basepath+self.path+"/cpu_exclusive",'w')
        if newval:
            f.write('1')
        else:
            f.write('0')
        f.close()
    cpu_exclusive = property(getcpuxlsv, setcpuxlsv, delprop, 
                             "CPU exclusive flag")

    def getmemxlsv(self): 
        f = file(CpuSet.basepath+self.path+"/mem_exclusive")
        if f.readline()[:-1] == '1':
            return True
        else:
            return False
    def setmemxlsv(self, newval):
        log.debug("-> prop_set %s.mem_exclusive = %s", self.path, newval) 
        f = file(CpuSet.basepath+self.path+"/mem_exclusive",'w')
        if newval:
            f.write('1')
        else:
            f.write('0')
        f.close()
    mem_exclusive = property(getmemxlsv, setmemxlsv, delprop, 
                             "Memory exclusive flag")

    def gettasks(self):
        f = file(CpuSet.basepath+self.path+"/tasks")
        lst = []
        for task in f: lst.append(task[:-1])
        return lst
    def settasks(self, tasklist):
        notfound = []
        unmovable = []
        if len(tasklist) > 3:
            pb = ProgressBar(len(tasklist), '=')
            tick = 0
            prog = True
        else:
            prog = False
        for task in tasklist:
            try:
                f = file(CpuSet.basepath+self.path+"/tasks",'w')
                f.write(task)
                f.close()
            except Exception, err:
                if str(err).find('No such process') != -1:
                    notfound.append(task)
                elif str(err).find('Invalid argument'):
                    unmovable.append(task)
                else: 
                    raise
            if prog:
                tick += 1
                pb(tick)
        if len(notfound) > 0:
            log.info('**> %s tasks were not found, so were not moved', len(notfound))
            log.debug(' not found: %s', notfound)
        if len(unmovable) > 0:
            log.info('**> %s tasks are not movable, impossible to move', len(unmovable))
            log.debug(' not movable: %s', unmovable)
        log.debug("-> prop_set %s.tasks set with %s tasks", self.path, 
                  len(tasklist)) 
    tasks = property(gettasks, settasks, delprop, "Task list")

#
# Helper functions
#

def lookup_task_from_proc(pid):
    """lookup the cpuset of the specified pid from proc filesystem"""
    log.debug("entering lookup_task_from_proc, pid = %s", str(pid))
    path = "/proc/"+str(pid)+"/cpuset"
    if os.access(path, os.F_OK):
        set = file(path).readline()[:-1]
        log.debug('lookup_task_from_proc: found task %s cpuset: %s', str(pid), set)
        return set
    # FIXME: add search for threads here...
    raise CpusetException("task ID %s not found, i.e. not running" % str(pid))

def lookup_task_from_cpusets(pid):
    """lookup the cpuset of the specified pid from cpuset filesystem"""
    log.debug("entering lookup_task_from_cpusets, pid = %s", str(pid))
    global RootSet
    if RootSet == None: rescan()
    gotit = None
    if pid in RootSet.tasks:
        gotit = RootSet
    else:
        for node in walk_set(RootSet):
            if pid in node.tasks:
                gotit = node
                break
    if gotit:
        log.debug('lookup_task_from_cpusets: found task %s cpuset: %s', str(pid),
                  gotit.path)
        return gotit.path
    raise CpusetException("task ID %s not found, i.e. not running" % str(pid))

def unique_set(name):
    """find a unique cpuset by name or path, raise if multiple sets found"""
    log.debug("entering unique_set, name=%s", name)
    if name == None:
        raise CpusetException('unique_set() passed None as arg')
    if isinstance(name, CpuSet): return name
    nl = find_sets(name)
    if len(nl) > 1: 
        raise CpusetNotUnique('cpuset name "%s" not unique: %s' % (name,
                              [x.path for x in nl]) )
    return nl[0]

def find_sets(name):
    """find cpusets by name or path, raise CpusetNotFound if not found"""
    log = logging.getLogger("cset.find_sets")
    log.debug('finding "%s" in cpusets', name)
    nodelist = []
    if name.find('/') == -1:
        log.debug("find by name")
        if name == 'root':
            log.debug("returning root set")
            nodelist.append(RootSet)
        else:
            log.debug("walking from: %s", RootSet.path)
            for node in walk_set(RootSet):
                if node.name == name:
                    log.debug('... found node "%s"', name)
                    nodelist.append(node)
    else:
        log.debug("find by path")
        # make sure that leading slash is used if searching by path
        if name[0] != '/': name = '/' + name
        if name in CpuSet.sets:
            log.debug('... found node "%s"', CpuSet.sets[name].name)
            nodelist.append(CpuSet.sets[name])
    if len(nodelist) == 0:
        raise CpusetNotFound('cpuset "%s" not found in cpusets' % name)
    return nodelist

def walk_set(set):
    """ generator for walking cpuset graph, breadth-first, more or less... """
    log = logging.getLogger("cset.walk_set")
    for node in set.subsets:
        log.debug("+++ yield %s", node.name)
        yield node

    for node in set.subsets:
        for result in walk_set(node): 
            log.debug("++++++ yield %s", node.name) 
            yield result 

def rescan():
    """re-read the cpuset directory to sync system with data structs"""
    log.debug("entering rescan")
    global RootSet, maxcpu, allcpumask
    RootSet = CpuSet()
    # figure out system properties
    log.debug("rescan: all cpus = %s", RootSet.cpus)
    maxcpu = int(RootSet.cpus.split('-')[-1].split(',')[-1])
    log.debug("        max cpu = %s", maxcpu)
    allcpumask = calc_cpumask(maxcpu)
    log.debug("        allcpumask = %s", allcpumask)

def cpuspec_check(cpuspec, usemax=True):
    """check format of cpuspec for validity"""
    log.debug("cpuspec_check(%s)", cpuspec)
    mo = re.search("[^0-9,\-]", cpuspec)
    if mo:
        str = 'CPUSPEC "%s" contains invalid charaters: %s' % (cpuspec, mo.group())
        log.debug(str)
        raise CpusetException(str)
    groups = cpuspec.split(',')
    if usemax and int(groups[-1].split('-')[-1]) > int(maxcpu):
        str = 'CPUSPEC "%s" specifies higher max(%s) than available(%s)' % \
              (cpuspec, groups[-1].split('-')[-1], maxcpu)
        log.debug(str)
        raise CpusetException(str)
    for sub in groups:
        it = sub.split('-')
        if len(it) == 2:
            if len(it[0]) == 0 or len(it[1]) == 0:
                # catches negative numbers
                raise CpusetException('CPUSPEC "%s" has bad group "%s"' % (cpuspec, sub))
        if len(it) > 2:
            raise CpusetException('CPUSPEC "%s" has bad group "%s"' % (cpuspec, sub))

def cpuspec_to_hex(cpuspec):
    """convert a cpuspec to the hexadecimal string representation"""
    log.debug('cpuspec_to_string(%s)', cpuspec)
    cpuspec_check(cpuspec, usemax=False)
    groups = cpuspec.split(',')
    number = 0
    for sub in groups:
        items = sub.split('-')
        if len(items) == 1:
            if not len(items[0]):
                # two consecutive commas in cpuspec
                continue
            # one cpu in this group
            log.debug(" adding cpu %s to result", items[0])
            number |= 1 << int(items[0])
        elif len(items) == 2: 
            il = [int(ii) for ii in items]
            if il[1] >= il[0]: rng = range(il[0], il[1]+1)
            else: rng = range(il[1], il[0]+1)
            log.debug(' group=%s has cpu range of %s', sub, rng)
            for num in rng: number |= 1 << num
        else:
            raise CpusetException('CPUSPEC "%s" has bad group "%s"' % (cpuspec, sub))
    log.debug(' final int number=%s in hex=%x', number, number)
    return '%x' % number

def memspec_check(memspec):
    """check format of memspec for validity"""
    # FIXME: look under /sys/devices/system/node for numa memory node
    # information and check the memspec that way, currently we only do
    # a basic check
    log.debug("memspec_check(%s)", memspec)
    mo = re.search("[^0-9,\-]", memspec)
    if mo:
        str = 'MEMSPEC "%s" contains invalid charaters: %s' % (memspec, mo.group())
        log.debug(str)
        raise CpusetException(str)

def cpuspec_inverse(cpuspec):
    """calculate inverse of cpu specification"""
    cpus = [0 for x in range(maxcpu+1)]
    groups = cpuspec.split(',')
    log.debug("cpuspec_inverse(%s) maxcpu=%d groups=%d", 
              cpuspec, maxcpu, len(groups))
    for set in groups:
        items = set.split('-')
        if len(items) == 1:
            if not len(items[0]):
                # common error of two consecutive commas in cpuspec,
                # just ignore it and keep going
                continue
            cpus[int(items[0])] = 1
        elif len(items) == 2:
            for x in range(int(items[0]), int(items[1])+1):
                cpus[x] = 1
        else:
            raise CpusetException("cpuspec(%s) has bad group %s" % (cpuspec, set))
    log.debug("cpuspec array: %s", cpus)
    # calculate inverse of array
    for x in range(0, len(cpus)):
        if cpus[x] == 0:
            cpus[x] = 1
        else:
            cpus[x] = 0
    log.debug("      inverse: %s", cpus)
    # build cpuspec expression
    nspec = ""
    ingrp = False
    for x in range(0, len(cpus)):
        if cpus[x] == 0 and ingrp:
            nspec += str(begin)
            if x > begin+1: 
                if cpus[x] == 1:
                    nspec += '-' + str(x)
                else:
                    nspec += '-' + str(x-1)
            ingrp = False
        if cpus[x] == 1:
            if not ingrp: 
                if len(nspec): nspec += ','
                begin = x
            ingrp = True
            if x == len(cpus)-1:
                nspec += str(begin)
                if x > begin:
                    nspec += '-' + str(x)
    log.debug("inverse cpuspec: %s", nspec)
    return nspec

def summary(set):
    """return summary of cpuset with number of tasks running"""
    log.debug("entering summary, set=%s", set.path)
    if len(set.tasks) == 1: msg = 'task'
    else: msg = 'tasks'
    return ('"%s" cpuset of CPUSPEC(%s) with %s %s running' %
            (set.name, set.cpus, len(set.tasks), msg) )
            
def calc_cpumask(max):
    all = 1
    ii = 1
    while ii < max+1:
        all |= 1 << ii
        ii += 1
    return "%x" % all


# Test if stand-alone execution
if __name__ == '__main__':
    rescan()

    # first create them, then find them
    try:
        os.makedirs(CpuSet.basepath+'/csettest/one/x')
        os.mkdir(CpuSet.basepath+'/csettest/one/y')
        os.makedirs(CpuSet.basepath+'/csettest/two/x')
        os.mkdir(CpuSet.basepath+'/csettest/two/y')
    except:
        pass

    print 'Max cpu on system:', maxcpu
    print 'All cpu mask: 0x%s' % allcpumask

    print '------- find_sets tests --------'
    print 'Find by root of "root" -> ', find_sets("root")
    print 'Find by path of "/" -> ', find_sets("/")

    print 'Find by path of "/csettest/one" -> ', find_sets("/csettest/one")
    print 'Find by name of "one" -> ', find_sets("one")
    print 'Find by path of "/csettest/two" -> ', find_sets("/csettest/two")
    print 'Find by name of "two" -> ', find_sets("two")

    print 'Find by path of "/csettest/one/x" -> ', find_sets("/csettest/one/x")
    print 'Find by name of "x" -> ', find_sets("x")
    print 'Find by path of "/csettest/two/y" -> ', find_sets("/csettest/two/y")
    print 'Find by name of "y" -> ', find_sets("y")

    try:
        node = find_sets("cantfindmenoway")
        print 'Found "cantfindmenoway??!? -> ', node
    except CpusetException, err:
        print 'Caught exeption for non-existant set (correctly)-> ', err

