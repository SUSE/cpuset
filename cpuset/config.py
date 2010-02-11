""" Cpuset Configuration Module

The config module maintains global (class) variables of the various
configuration parameters for the cpuset application.  These are filled in from
applicable configuration file passed as a path to the ReadConfigFile() method,
if desired.  The class variables are given default values in the module source.
Anything found in the configuration files in the list of paths will override
these defaults.
"""

__copyright__ = """
Copyright (C) 2009-2010 Novell Inc.
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

import sys
import types
import ConfigParser

############################################################################
# Default configuration variable values
############################################################################
defloc = '/etc/cset.conf'           # default config file location
mread = False                       # machine readable output, usually set
                                    # via option -m/--machine 
mountpoint = '/cpusets'             # cpuset filessytem mount point
############################################################################

def ReadConfigFiles(path=None):
    if path == None: path = defloc
    cf = ConfigParser.ConfigParser()
    try:
        fr = cf.read(path)
        if len(fr) == 0: return
        # can't use logging, too early...
        if len(cf.sections()) != 1:
            print "cset: warning, more than one section found in config file:", cf.sections()
        if 'default' not in cf.sections():
            print 'cset: [default] section not found in config file "%s"' % path
            sys.exit(3)

    except ConfigParser.MissingSectionHeaderError:
        f = open(path)
        cstr = f.read()
        f.close()
        import StringIO
        cf.readfp(StringIO.StringIO('[default]\n' + cstr))

    # override our globals...
    for opt in cf.options('default'):
        typ = type(globals()[opt])
        if typ == types.BooleanType:
            globals()[opt] = cf.getboolean('default', opt)
        elif typ == types.IntType:
            globals()[opt] = cf.getint('default', opt)
        else:
            globals()[opt] = cf.get('default', opt)

# Importing module autoinitializes it
def __init():
    ReadConfigFiles()

__init()
