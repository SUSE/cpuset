#  
# spec file for package cpuset (Version 1.5.2)  
#  
# Copyright (c) 2008-2010 Novell, Inc. Waltham, MA, USA
# This file and all modifications and additions to the pristine  
# package are under the same license as the package itself.  
#  
# Please submit bugfixes or comments via 
#        http://code.google.com/p/cpuset/issues/list
#    Or 
#        http://bugs.opensuse.org/
# 
# For supported products, via http://bugzilla.novell.com
#  

# norootforbuild  

Name:           cpuset
Version:        1.5.2
Release:        1
License:        GPL v2 only
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
Url:            http://code.google.com/p/cpuset
Group:          System/Management
Summary:        Allows manipulation of cpusets on system and provides higher level functions
Source:         %{name}-%{version}.tar.gz
BuildRequires:  python-devel

%if 0%{?suse_version} > 0
%py_requires
%endif

%{!?python_sitelib: %define python_sitelib %(python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%description

Cpuset is a Python application to make using the cpusets facilities in
the Linux kernel easier.  The actual included command is called cset
and it allows manipulation of cpusets on the system and provides higher
level functions such as implementation and control of a basic CPU
shielding setup.


Authors:
--------
    Alex Tsariounov <alext@novell.com>

%prep
%setup


%build
CFLAGS="%{optflags}" \
%{__python} setup.py build
#make doc  ->not yet, asciidoc is missing...


%install
# Install binaries, but do not install docs via setup.py
%{__python} setup.py install --root=%{buildroot} --prefix=%{_prefix} --install-data=/eraseme
%{__rm} -rf %{buildroot}/eraseme

# Install documentation
%{__mkdir_p} %{buildroot}/%{_defaultdocdir}/cpuset
%{__cp} NEWS README INSTALL AUTHORS COPYING cset.init.d %{buildroot}/%{_defaultdocdir}/cpuset/
%{__mkdir_p} %{buildroot}/%{_mandir}/man1
cd doc
%{__gzip} *.1
%{__cp} *.1.gz %{buildroot}/%{_mandir}/man1
%{__cp} *.txt %{buildroot}/%{_defaultdocdir}/cpuset/
%{__mkdir} %{buildroot}/%{_defaultdocdir}/cpuset/html
%{__cp} *.html %{buildroot}/%{_defaultdocdir}/cpuset/html/


%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root)
%{_bindir}/cset
%{python_sitelib}/*
%{_mandir}/man1/*
%{_defaultdocdir}/*


%changelog
