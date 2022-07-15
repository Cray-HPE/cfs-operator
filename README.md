# Cray Configuration Framework Service Operator

A Kubernetes deployment for managing Ansible Execution Environments through the
[Cray Configuration Framework Service](https://github.com/Cray-HPE/config-framework-service).
A Config Framework Session manages the setup, launch, and teardown of
[Ansible Execution Environments](https://github.com/Cray-HPE/ansible-execution-environment)
(AEE) and provides status information from the AEE runs.

## Testing & Code Quality

### Unit Testing and Code Coverage

Unit tests are run via [nox](https://nox.thea.codes/en/stable/index.html) using
[pytest](https://docs.pytest.org/en/latest/).

```bash
(cfs-operator) $ nox -s unittests
```

Unit tests are located in the [tests/unit](./tests/unit) directory and should be added for all code in this repository.
Code coverage is calculated during this nox session as well.

__NOTE__: Pipeline builds and local runs of the unit tests will fail if the
coverage is less than 95%.

### Linting

Code style is checked with [flake8](http://flake8.pycqa.org/en/latest/) using nox:

```bash
(cfs-operator) $ nox -s lint
```

The flake8 configuration file is located in [.flake8](./.flake8).

__NOTE__: Pipeline builds and local runs of flake8 will fail if linting issues
are present.

## Deployment

The operator is deployed as part of the CSM System Management manifest
on Cray Shasta systems.

## Built With

* [Python 3](https://docs.python.org/3/)
* [Kubernetes Python Client](https://github.com/kubernetes-client/python)
* [Redis](https://redis-py.readthedocs.io/en/latest/)
* [Kafka](https://kafka.apache.org)
* [Ansible](https://docs.ansible.com)

## Dependency: cray-aee
cfs-operator uses the cray-aee image built by the ansible-execution-environment repo.
We specify which major and minor version of the image we want with the 
[update_external_versions.conf](update_external_versions.conf) file.
At build time the latest version with that major and minor number is found.

When creating a new release branch, be sure to update this file to specify the
desired major and minor number of the image for the new release.

## Build Helpers
This repo uses some build helpers from the 
[cms-meta-tools](https://github.com/Cray-HPE/cms-meta-tools) repo. See that repo for more details.

## Local Builds
If you wish to perform a local build, you will first need to clone or copy the contents of the
cms-meta-tools repo to `./cms_meta_tools` in the same directory as the `Makefile`. When building
on github, the cloneCMSMetaTools() function clones the cms-meta-tools repo into that directory.

For a local build, you will also need to manually write the .version, .docker_version (if this repo
builds a docker image), and .chart_version (if this repo builds a helm chart) files. When building
on github, this is done by the setVersionFiles() function.

## Versioning
The version of this repo is generated dynamically at build time by running the version.py script in 
cms-meta-tools. The version is included near the very beginning of the github build output. 

In order to make it easier to go from an artifact back to the source code that produced that artifact,
a text file named gitInfo.txt is added to Docker images built from this repo. For Docker images,
it can be found in the / folder. This file contains the branch from which it was built and the most
recent commits to that branch. 

For helm charts, a few annotation metadata fields are appended which contain similar information.

For RPMs, a changelog entry is added with similar information.

## New Release Branches
When making a new release branch:
    * Be sure to set the `.x` and `.y` files to the desired major and minor version number for this repo for this release. 
    * If an `update_external_versions.conf` file exists in this repo, be sure to update that as well, if needed.

## Contributing

Members of the CASMCMS team should provide a pull request to master and/or a release branch.
Others should fork this repository and provide a pull request to the current release branch.

## Authors

* __Randy Kleinman__ - Q1 2019 - _Initial Work_ - rkleinman@cray.com
* (Add your name here for praise or blame later)

## Changelog

See the [CHANGELOG](CHANGELOG.md) for changes. This file uses the [Keep A Changelog](https://keepachangelog.com)
format.

## Copyright and License
This project is copyrighted by Hewlett Packard Enterprise Development LP and is under the MIT
license. See the [LICENSE](LICENSE) file for details.

When making any modifications to a file that has a Cray/HPE copyright header, that header
must be updated to include the current year.

When creating any new files in this repo, if they contain source code, they must have
the HPE copyright and license text in their header, unless the file is covered under
someone else's copyright/license (in which case that should be in the header). For this
purpose, source code files include Dockerfiles, Ansible files, RPM spec files, and shell
scripts. It does **not** include Jenkinsfiles, OpenAPI/Swagger specs, or READMEs.

When in doubt, provided the file is not covered under someone else's copyright or license, then
it does not hurt to add ours to the header.
