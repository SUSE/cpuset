"""Memory node manipulation command
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

import sys, os, logging
from optparse import OptionParser, make_option

from cpuset.commands.common import *
from cpuset import cset
from cpuset.util import *

global log
log = logging.getLogger('mem')

help = 'create and destroy memory nodes within cpusets'
usage = """%prog [options] [cpuset name]

Create and manage memory node assignments to cpusets.  Note that for
non-NUMA machines, the memory node assignment will always be 0 (zero)
and is so set by default.  Thus this command only needs to be used
for NUMA machines.
"""

options = [make_option('-l', '--list',
                       help = 'list memory nodes in specified cpuset',
                       action = 'store_true'),
           make_option('-c', '--create',
                       metavar = 'NODESPEC',
                       help = 'create a memory node in specified cpuset'),
           make_option('-d', '--destroy',
                       help = 'destroy specified memory node in specified cpuset',
                       action = 'store_true'),
           make_option('-m', '--move',
                       help = 'move specified memory node to specified cpuset',
                       action = 'store_true'),
           make_option('-s', '--set',
                       metavar = 'CPUSET',
                       help = 'specify immediate cpuset'),
           make_option('-t', '--toset',
                       help = 'specify destination cpuset'),
           make_option('-f', '--fromset',
                       help = 'specify origination cpuset')
          ]

def func(parser, options, args):
    log.debug("entering mem, options=%s, args=%s", options, args)
