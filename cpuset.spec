#
# spec file for package cpuset
#
# Copyright (c) 2018 SUSE LINUX GmbH, Nuernberg, Germany.
# Copyright (c) 2008-2011 Novell, Inc. Waltham, MA, USA
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


%if 0%{?suse_version} < 1315
%define pyver python
%else
%define pyver python3
%endif
%if 0%{?suse_version} && 0%{?suse_version} <= 1110
%{!?python_sitelib: %global python_sitelib %(python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%else
BuildArch:      noarch
%endif
Name:           cpuset
Version:        1.6
Release:        0
Summary:        Allows manipulation of cpusets on system and provides higher level functions
License:        GPL-2.0-only
Group:          System/Management
URL:            https://github.com/lpechacek/cpuset
Source:         https://github.com/lpechacek/cpuset/archive/v%{version}.tar.gz
BuildRequires:  %{pyver}-setuptools
Requires:       %{pyver}-future

%description
Cpuset is a Python application to make using the cpusets facilities in
the Linux kernel easier.  The actual included command is called cset
and it allows manipulation of cpusets on the system and provides higher
level functions such as implementation and control of a basic CPU
shielding setup.

%prep
%setup -q -n %{name}-%{version}

%build
%{pyver} setup.py build
#make doc  ->not yet, asciidoc is missing...

%install
# Install binaries, but do not install docs via setup.py
%{pyver} setup.py install --root=%{buildroot} --prefix=%{_prefix} --install-data=/eraseme
rm -rf %{buildroot}/eraseme

# Install documentation
mkdir -p %{buildroot}/%{_mandir}/man1
mkdir -p %{buildroot}/%{_defaultdocdir}/%{name}/html

install -m 0444 doc/*.1 %{buildroot}/%{_mandir}/man1

install -m 0444 NEWS README AUTHORS COPYING cset.init.d doc/*.txt %{buildroot}/%{_defaultdocdir}/%{name}
install -m 0444 doc/*.html %{buildroot}/%{_defaultdocdir}/%{name}/html/

%files
%doc %{_docdir}/%{name}
%{_bindir}/cset
%if 0%{?suse_version} < 1315
%{python_sitelib}/*
%else
%{python3_sitelib}/*
%endif
%{_mandir}/man1/*

%changelog
