"""Front end command line tool for Linux cpusets
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

import sys, os
from optparse import OptionParser
from cpuset import config
import cpuset.commands
from cpuset.commands.common import CmdException
from cpuset.util import CpusetException

#
# The commands map
#
class Commands(dict):
    """Commands class. It performs on-demand module loading
    """
    def canonical_cmd(self, key):
        """Return the canonical name for a possibly-shortenned
        command name.
        """
        candidates = [cmd for cmd in self.keys() if cmd.startswith(key)]

        if not candidates:
            log.error('Unknown command: %s', key)
            log.error('Try "%s help" for a list of supported commands', prog)
            sys.exit(1)
        elif len(candidates) > 1:
            log.error('Ambiguous command: %s', key)
            log.error('Candidates are: %s', ', '.join(candidates))
            sys.exit(1)

        return candidates[0]
        
    def __getitem__(self, key):
        """Return the command python module name based.
        """
        global prog

        cmd_mod = self.get(key) or self.get(self.canonical_cmd(key))
            
        __import__('cpuset.commands.' + cmd_mod)
        return getattr(cpuset.commands, cmd_mod)

commands = Commands({
    'shield':       'shield',
    'set':          'set',
#    'mem':          'mem',
    'proc':         'proc',
    })

supercommands = (
    'shield',
    )

def _print_helpstring(cmd):
    print '  ' + cmd + ' ' * (12 - len(cmd)) + commands[cmd].help
    
def print_help():
    print 'Usage: %s [global options] <command> [command options]' % os.path.basename(sys.argv[0])
    print
    print 'Global options:'
    print '  -l/--log <fname>       output debugging log in fname'
    print '  -m/--machine           print machine readable output'
    print '  -x/--tohex <CPUSPEC>   convert a CPUSPEC to hex'
    print
    print 'Generic commands:'
    print '  help        print the detailed command usage'
    print '  version     display version information'
    print '  copyright   display copyright information'

    cmds = commands.keys()
    cmds.sort()
    print 
    print 'Super commands (high-level and multi-function):'
    for cmd in supercommands:
        _print_helpstring(cmd)
    print
    print 'Regular commands:'
    for cmd in cmds:
        if not cmd in supercommands:
            _print_helpstring(cmd)

def main():

    # handle pipes better
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    global prog
    prog = os.path.basename(sys.argv[0])

    global logfile
    logfile = None

    if len(sys.argv) < 2:
        print >> sys.stderr, 'usage: %s <command>' % prog
        print >> sys.stderr, \
              '  Try "%s --help" for a list of supported commands' % prog
        sys.exit(1)
    
    # configure logging
    import logging
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(prog + ': %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    global log
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)

    try:
        debug_level = int(os.environ['CSET_DEBUG_LEVEL'])
    except KeyError:
        debug_level = 0
    except ValueError:
        log.error('Invalid CSET_DEBUG_LEVEL environment variable')
        sys.exit(1)

    while True:
        if len(sys.argv) == 1:
            log.error('no arguments, nothing to do!')
            sys.exit(2)
        cmd = sys.argv[1]
        if cmd in ['-l', '--log']:
            if len(sys.argv) < 3:
                log.critical('not enough arguments')
                sys.exit(1)
            # FIXME: very fragile
            logfile = sys.argv[2]
            #trace = logging.FileHandler('/var/log/cset.log', 'w')
            trace = logging.FileHandler(logfile, 'a')
            trace.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s %(name)-6s %(levelname)-8s %(message)s',
                                          '%y%m%d-%H:%M:%S')
            trace.setFormatter(formatter)
            logging.getLogger('').addHandler(trace)
            log.debug("---------- STARTING ----------")
            from cpuset.version import version
            log.debug('Cpuset (cset) %s' % version)
            del(sys.argv[2])
            del(sys.argv[1])
            continue
        if cmd in ['-h', '--help']:
           if len(sys.argv) >= 3:
               cmd = commands.canonical_cmd(sys.argv[2])
               sys.argv[2] = '--help'
           else:
               print_help()
               sys.exit(0)
        if cmd == 'help':
            if len(sys.argv) == 3 and not sys.argv[2] in ['-h', '--help']:
                cmd = commands.canonical_cmd(sys.argv[2])
                if not cmd in commands:
                    log.error('help: "%s" command unknown' % cmd)
                    sys.exit(1)

                sys.argv[0] += ' %s' % cmd
                command = commands[cmd]
                parser = OptionParser(usage = command.usage,
                                      option_list = command.options)
                from pydoc import pager
                pager(parser.format_help())
            else:
                print_help()
            sys.exit(0)
        if cmd in ['-v', '--version', 'version']:
            from cpuset.version import version
            log.info('Cpuset (cset) %s' % version)
            sys.exit(0)
        if cmd in ['-c', 'copyright', 'copying']:
            log.info(__copyright__)
            sys.exit(0)
        if cmd in ['-m', '--machine']:
            config.mread = True
            del(sys.argv[1])
            continue
        if cmd in ['-x', '--tohex']:
            if len(sys.argv) < 3:
                log.critical('not enough arguments')
                sys.exit(1)
            cpuspec = sys.argv[2]
            import cset
            try:
                print cset.cpuspec_to_hex(cpuspec)
            except (ValueError, OSError, IOError, CpusetException, CmdException), err:
                log.critical('**> ' + str(err))
                if debug_level:
                    raise
                else:
                    sys.exit(2)
            sys.exit(0)

        break

    # re-build the command line arguments
    cmd = commands.canonical_cmd(cmd)
    sys.argv[0] += ' %s' % cmd
    del(sys.argv[1])
    log.debug('cmdline: ' + ' '.join(sys.argv))

    try:
        # importing the cset class creates the model
        log.debug("creating cpuset model")
        import cpuset.cset
        command = commands[cmd]
        usage = command.usage.split('\n')[0].strip()
        parser = OptionParser(usage = usage, option_list = command.options)
        options, args = parser.parse_args()
        command.func(parser, options, args)
    except (ValueError, OSError, IOError, CpusetException, CmdException), err:
        log.critical('**> ' + str(err))
        if str(err).find('Permission denied') != -1:
            log.critical('insufficient permissions, you probably need to be root')
        if str(err).find('invalid literal') != -1:
            log.critical('option not understood')
        if debug_level:
            raise
        else:
            sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(1)

    sys.exit(0)
