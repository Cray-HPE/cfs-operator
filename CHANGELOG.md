# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- CASMCMS-9335: cfs session patch fails to update Job ID causing session to remain in pending state.

## [1.29.0] - 02/13/2025
### Changed
- Updated cfs-api clusterrole definition to allow it to introspect into tenant namespaces for access to secrets

### Added
- Allow session_events to perform VAULT_TOKEN lookups when associated with a configset owned by a tenant

### Dependencies
- CASMCMS-9282
  - Bump Alpine version from 3.15 to 3.21, because 3.15 no longer receives security patches
  - Use Python venv inside Docker image.
  - Update Python dependencies for move to Python 3.12
  - Update to `cray-aee` 1.18 for CSM 1.7

## [1.28.0] - 01/22/2025
### Changed
- Removed openssh and added openssh-client package.

## [1.27.1] - 09/06/2024
### Dependencies
- Bump `cryptography` to 43.0.1 to resolve CVE

## [1.27.0] - 09/03/2024
### Dependencies
- CSM 1.6 moved to Kubernetes 1.24, so use client v24.x to ensure compatibility
- CASMPET-7064 - update to cray-services:11.0.0 base chart

## [1.26.3] - 08/23/2024
### Dependencies
- CASMCMS-9115: Move to `ansible-execution-environment` 1.17

## [1.26.2] - 08/16/2024
### Changed
- Print list of installed Python modules after pip installs in Dockerfile, for logging purposes.

### Dependencies
- Instead of using `update_external_versions` to find the latest patch version of
  liveness, instead just pin the major/minor number directly in constraints.txt.
- Use `requests_retry_session` module instead of duplicating code.
- Add missing required modules to requirements.txt

## [1.26.1] - 07/24/2024
### Dependencies
- Bumped dependency versions to resolve CVEs:
| Package                  | From       | To        |
|--------------------------|------------|-----------|
| `certifi`                | 2018.11.29 | 2023.7.22 |
| `cryptography`           | 41.0.2     | 42.0.8    |

## [1.26.0] - 07/24/2024
### Changed
- When creating Kubernetes jobs for CFS sessions, if the CFS session TTL option is set,
  use it to set the `ttl_seconds_after_finished` option for the Kubernetes job.

## [1.25.0] - 06/04/2024
### Changed
- When building unstable charts, have them point to the corresponding unstable cfs-operator images

### Dependencies
- CASMCMS-9018/CAST-35618: Bump `paramiko` from 2.7.2 to 2.11.1 to prevent Blowfish deprecation warnings.

## [1.24.0] - 03/01/2024
### Changed
- CASMCMS-8896 - enhance the ssh test for if the connection is ready for use.

## [1.23.0] - 02/22/2024
### Dependencies
- Bump `kubernetes` from 9.0.1 to 22.6.0 to match CSM 1.6 Kubernetes version
- Bump `cray-aee` from 1.15 to 1.16 for CSM 1.6

## [1.22.1] - 10/23/2023
### Fixed
- Fixed applying the configuration limit for layer 0

## [1.22.0] - 10/18/2023
### Added
- Added support for cloning from CFS sources

### Changed
- CFS session git-clone containers now use the cfs-operator image 

## [1.21.0] - 9/28/2023
### Changed
- Pull in upstream changes for AEE and associated ansible-galaxy mods

## [1.20.0] - 9/13/2023
### Added
- Added SOPS support to ansible.cfg file, as provided through helm chart
- Added CFS clean-up of IMS jobs that it creates for image customization.
### Changed
- Perform version bump to new version of ansible (1.15.x)

## [1.19.0] - 8/18/2023
### Changed
- Disabled concurrent Jenkins builds on same branch/commit
- Added build timeout to avoid hung builds
- Moved to the v3 CFS api

### Added
- Added debugging wait time for failed sessions
- Added support for special debug playbooks
- Added clusterrole permissions so cfs can view virtual services

### Fixed
- Fixed job labels that were longer than allowed by Kubernetes

## [1.18.3] - 7/25/2023
### Dependencies
- Use `update_external_versions` to get latest patch version of `liveness` Python module.
- Bumped dependency patch versions:
| Package                  | From     | To       |
|--------------------------|----------|----------|
| `bcrypt`                 | 3.1.4    | 3.1.7    |
| `cffi`                   | 1.14.3   | 1.14.6   |
| `coverage`               | 4.5.2    | 4.5.4    |
| `dictdiffer`             | 0.8.0    | 0.8.1    |
| `google-auth`            | 1.6.1    | 1.6.3    |
| `Jinja2`                 | 2.10.1   | 2.10.3   |
| `py`                     | 1.8.0    | 1.8.2    |
| `pyasn1`                 | 0.4.4    | 0.4.8    |
| `pyasn1-modules`         | 0.2.2    | 0.2.8    |
| `rsa`                    | 4.7      | 4.7.2    |
| `urllib3`                | 1.25.9   | 1.25.11  |

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

