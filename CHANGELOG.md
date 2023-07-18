# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

