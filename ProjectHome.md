Cpuset is a Python application to make using the cpusets facilities in the Linux kernel easier.  The actual included command is called cset and it allows manipulation of cpusets on the system and provides higher level functions such as implementation and control of a basic CPU shielding setup.

The latest version is: **1.5.6**  And the associated [NEWS file is here.](http://code.google.com/p/cpuset/source/browse/NEWS?r=rel_1.5.6)

Cpuset comes with man pages and a tutorial.  You can also read  [the tutorial on the RT Linux Wiki here.](https://rt.wiki.kernel.org/index.php/Cpuset_management_utility/tutorial)

Binary packages for the latest release are available on my [cpuset project at the openSUSE Build Service.](http://download.opensuse.org/repositories/home:/tsariounov:/cpuset/)  This site hosts packages that can be used in many distributions including: openSUSE, Fedora, SLES, RHEL, CentOS, Mandriva.

Also, [this Gentoo ebuild script for 1.5.5](http://cpuset.googlecode.com/files/cpuset-1.5.5.ebuild) has been contributed by Joerg Neikes.

If building from source, cset uses the python distutils to manage installation. It is recommended to create an rpm rather than using the install command since it is far easier to remove and upgrade with rpm. To create an rpm, use the following command:
```
$ python setup.py bdist_rpm
```

To build a source distribution tarball from the source, use this command:
```
$ python setup.py sdist
```