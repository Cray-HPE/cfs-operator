# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
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

