"""Utility functions
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

import sys, time
from cpuset import config

class CpusetException(Exception):
    pass

class CpusetAbort(CpusetException):
    pass

class CpusetNotFound(CpusetException):
    pass

class CpusetNotUnique(CpusetException):
    pass

class CpusetExists(CpusetException):
    pass

# a twirling bar progress indicator
class TwirlyBar:
    def __init__(self):
        import sys
        self.__dict__['__call__'] = self.tick
        self.__state = 0
        self.__bar = ('|', '/', '-', '\\')

    def tick(self):
        if not config.mread:
            print '\b' + self.__bar[self.__state] + '\b',
        self.__state = self.__state + 1
        if self.__state > 3: self.__state = 0

    def fastick(self):
        for x in range(10):
            self.tick()
            time.sleep(0.04)

# a progress bar indicator
class ProgressBar:
    def __init__(self, finalcount, progresschar=None):
        self.__dict__['__call__'] = self.progress
        self.finalcount=finalcount
        self.blockcount=0
        # Use ascii block char for progress if none passed
        if not progresschar: 
            self.block=chr(178)
        else: 
            self.block=progresschar
        if config.mread: 
            return
        self.f=sys.stdout
        if not self.finalcount: return
        self.f.write('[')
        for i in range(50): self.f.write(' ')
        self.f.write(']%')
        for i in range(52): self.f.write('\b')

    def progress(self, count):
        count=min(count, self.finalcount)

        if self.finalcount:
            percentcomplete=int(round(100*count/self.finalcount))
            if percentcomplete < 1: percentcomplete=1
        else:
            percentcomplete=100

        blockcount=int(percentcomplete/2)
        if not config.mread:
            if blockcount > self.blockcount:
                for i in range(self.blockcount,blockcount):
                    self.f.write(self.block)
                    self.f.flush()

            if percentcomplete == 100: self.f.write("]\n")
        self.blockcount=blockcount

