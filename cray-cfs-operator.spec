# Copyright 2019,2021 Hewlett Packard Enterprise Development LP
Name: cray-cfs-operator-crayctldeploy
License: MIT
Summary: Cray Configuration Framework Operator
Group: System/Management
Version: %(cat .rpm_version)
Release: %(echo ${BUILD_METADATA})
Source: %{name}-%{version}.tar.bz2
Vendor: Cray Inc.
Requires: cray-crayctl
Requires: kubernetes-crayctldeploy

# Project level defines TODO: These should be defined in a central location; DST-892
%define afd /opt/cray/crayctl/ansible_framework
%define roles %{afd}/roles
%define playbooks %{afd}/main
%define modules %{afd}/library

%description
This package provides a Kubernetes Operator for managing the environments via a
Kubernetes Custom Resource Definition (CRD).

%prep
%setup -q

%build

%install
install -m 755 -d %{buildroot}%{roles}/

# All roles and modules from this project
cp -r ansible/roles/* %{buildroot}%{roles}/

%clean
rm -rf %{buildroot}%{roles}/*

%files
%defattr(755, root, root)

%dir %{roles}
%{roles}/cray-cfs-operator-init
