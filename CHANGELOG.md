# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Dependencies
- Bump `bcrypt` from 3.1.4 to 3.1.7
- Bump `cffi` from 1.14.3 to 1.14.6
- Bump `coverage` from 4.5.2 to 4.5.4
- Bump `dictdiffer` from 0.8.0 to 0.8.1
- Bump `google-auth` from 1.6.1 to 1.6.3
- Bump `Jinja2` from 2.10.1 to 2.10.3
- Bump `py` from 1.8.0 to 1.8.2
- Bump `pyasn1` from 0.4.4 to 0.4.8
- Bump `pyasn1-modules` from 0.2.2 to 0.2.8
- Bump `rsa` from 4.7 to 4.7.2
- Bump `urllib3` from 1.25.9 to 1.25.11

## [1.18.2] - 7/20/2023
### Dependencies
- Bump `cryptography` from 3.2 to 41.0.2 to fix [Improper Certificate Validation CVE](https://security.snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-5777683)
- Bump `kubernetes` from 9.0.0 to 9.0.1
- Bump `paramiko` from 2.7.1 to 2.7.2

## [1.18.1] - 7/18/2023
### Changed
- In [`src/cray/cfs/teardown/__main__.py`](src/cray/cfs/teardown/__main__.py), use `yaml.safe_load()`
  instead of `yaml.load()`, both for security reasons and because the current function call breaks
  when moving to `PyYAML` >= 6

### Dependencies
- Bump `PyYAML` from 5.4.1 to 6.0.1 to avoid build issue caused by https://github.com/yaml/pyyaml/issues/601

## [1.18.0] - 6/27/2023
### Removed
- Removed defunct files leftover from previous versioning system

### Added
- Added support for a new configuration parameter for enabling DKMS in IMS

## [1.17.1] - 1/25/2023
### Fixed
- Increased container memory limits
- Excluded missing sessions from retries during setup

## [1.17.0] - 1/12/2023
### Added
- Add Artifactory authentication to Jenkinsfile
- Added a new parameter for naming image customization results
- Added a pointer to IMS logs when image inventory creation fails
- Added cfs_image host group to image customization inventory
- Added Ansible configuration values to enable ARA log collection

### Changed
- Updated dynamic inventory to log and drop invalid HSM group names
- Image teardown now marks failed images correctly
- Log levels are now controlled by a CFS option
- Ansible container limits/requests are now configurable
- Changed session job structure so that only one git-clone and ansible container are created

### Fixed
- Spelling corrections.
- Fixed the exit code when git checkout fails

## [1.16.3] - 2022-12-20
### Added
- Add Artifactory authentication to Jenkinsfile
- Authenticate to CSM's artifactory

## [1.16.2] - 10/28//22
### Changed
- Remove high priority from cfs session pods

## [1.16.1] - 8/4/22
### Fixed
- Escalated pod priority so that configuration has a better chance of running when a node is cordoned

## [1.16.0] - 8/4/22
### Fixed
- Fixed container users to avoid permissions issues when using additional inventory

### Changed
- Changed image customization to allow additional inventory, while adding an automatic limit to Ansible

## [1.15.0] - 7/19/22
### Changed
- Updated build references to AEE 1.3.0 (gitversion/giflow conversion).
- Migrated over to arti internal build references.
- Convert to gitflow/gitversion.
- Fixed Kafka retries

