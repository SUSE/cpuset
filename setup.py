#!/usr/bin/env python

import glob
from distutils.core import setup

from cpuset.version import version

setup(name = 'cpuset',
    version = version,
    license = 'GPLv2',
    author = 'Alex Tsariounov',
    author_email = 'tsariounov@gmail.com',
    maintainer = 'Michal Koutny',
    maintainer_email = 'mkoutny@suse.com',
    url = 'https://github.com/SUSE/cpuset',
    description = 'Allows manipulation of cpusets and provides higher level functions.',
    long_description = \
        'Cpuset is a Python application to make using the cpusets facilities in the Linux\n'
        'kernel easier. The actual included command is called cset and it allows\n'
        'manipulation of cpusets on the system and provides higher level functions such as\n'
        'implementation and control of a basic cpu shielding setup.',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Systems Administration',
    ],
    scripts = ['cset'],
    packages = ['cpuset', 'cpuset.commands'],
    data_files = [
		  ('share/doc/packages/cpuset', ['README', 'COPYING', 'AUTHORS', 'NEWS', 'INSTALL']),
		  ('share/doc/packages/cpuset', glob.glob('doc/*.html')),
		  ('share/doc/packages/cpuset', glob.glob('doc/*.txt')),
	         ]
    )
