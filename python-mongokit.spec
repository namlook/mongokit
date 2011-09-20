# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%define srcname mongokit

Name:           python-%{srcname}
Version:        0.7.2
Release:        1%{?dist}
Summary:        Python mongodb kit

Group:          Development/Libraries
License:        Apache License 2
URL:            https://github.com/namlook/mongokit
Source0:        %{srcname}-%{version}.tar.bz2

BuildRequires:  python-devel
BuildRequires:  python-setuptools

Requires:       mongodb, python-anyjson

%description
MongoKit is a python module that brings structured schema and validation layer
on top of the great pymongo driver. It has be written to be as simple and light
as possible with the KISS and DRY principles in mind.

%prep
%setup -q -n %{srcname}-%{version}


%build
# Remove CFLAGS=... for noarch packages (unneeded)
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc AUTHORS CHANGELOG LICENSE README.rst
# For noarch packages: sitelib
 %{python_sitelib}/*
# For arch-specific packages: sitearch
# %{python_sitearch}/*

%changelog
* Sat Sep 17 2011 Pau Aliagas <linuxnow@gmail.com> 0.7.2-1
- Initial version
