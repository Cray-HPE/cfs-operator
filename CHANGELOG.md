# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.16.7] - 7/20/23
### Dependencies
- Bump `cryptography` from 3.2 to 41.0.2 to fix [Improper Certificate Validation CVE](https://security.snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-5777683)
- Bump `kubernetes` from 9.0.0 to 9.0.1
- Bump `paramiko` from 2.7.1 to 2.7.2

## [1.16.6] - 7/18/23
### Changed
- In [`src/cray/cfs/teardown/__main__.py`](src/cray/cfs/teardown/__main__.py), use `yaml.safe_load()`
  instead of `yaml.load()`, both for security reasons and because the current function call breaks
  when moving to `PyYAML` >= 6

### Dependencies
- Bump `PyYAML` from 5.4.1 to 6.0.1 to avoid build issue caused by https://github.com/yaml/pyyaml/issues/601

## [1.16.5] - 1/12/23
### Fixed
- Fixed configurable session requests/limits

## [1.16.4] - 1/6/23
### Added
- Add Artifactory authentication to Jenkinsfile

## [1.16.3] - 12/2/22
### Added
- Authenticate to CSM's artifactory
- Changed session job structure so that only one git-clone and ansible container are created

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

