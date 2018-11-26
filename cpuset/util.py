"""Utility functions
"""
from __future__ import unicode_literals
from __future__ import print_function
from future.utils import lrange

from builtins import chr
from builtins import object
__copyright__ = """
Copyright (C) 2007-2010 Novell Inc.
Copyright (C) 2013-2018 SUSE
Author: Alex Tsariounov <tsariounov@gmail.com>

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

# a progress bar indicator
class ProgressBar(object):
    def __init__(self, finalcount, progresschar=None):
        self.finalcount=finalcount
        self.blockcount=0
        self.finished=False
        # Use dark shade (U+2593) char for progress if none passed
        if not progresschar: 
            self.block='\u2593'
        else: 
            self.block=progresschar
        if config.mread: 
            return
        self.f=sys.stdout
        if not self.finalcount: return
        self.f.write('[')
        for i in lrange(50): self.f.write(' ')
        self.f.write(']%')
        for i in lrange(52): self.f.write('\b')

    def __call__(self, count):
        self.progress(count)

    def progress(self, count):
        if self.finished:
            return

        count=min(count, self.finalcount)

        if self.finalcount:
            percentcomplete=int(round(100*count/self.finalcount))
            if percentcomplete < 1: percentcomplete=1
        else:
            percentcomplete=100
            self.finished=True
            return

        blockcount=percentcomplete//2
        if not config.mread:
            if blockcount > self.blockcount:
                for i in lrange(self.blockcount,blockcount):
                    self.f.write(self.block)
                    self.f.flush()

            if percentcomplete == 100:
                self.f.write("]\n")
                self.finished=True
        self.blockcount=blockcount
