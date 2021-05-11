# Cray Configuration Framework Service Operator

A Kubernetes for managing Ansible Execution Environments through the
[Cray Configuration Framework Service](https://stash.us.cray.com/projects/SCMS/repos/config-framework-service/browse).
A Config Framework Sessions manages the setup, launch, and teardown of
[Ansible Execution Environments](https://stash.us.cray.com/projects/SCMS/repos/ansible-execution-environment/browse)
(AEE) and provides status information from the AEE runs.

Overall architecture of Shasta Configuration Management can be found in its
[design document](https://connect.us.cray.com/confluence/x/ZKmfBw).

## Getting Started

### Prerequisites

1. A Python 3.x-based virtual environment,
2. The Python requirements,
3. A Kubernetes cluster to connect to (virtual or physical) to run the operator.
   This is not necessary for development or running the tests.
4. Docker (for building the image locally)

```bash
$ python3.6 -m venv ~/Documents/venv/cfs-operator
$ source ~/Documents/venv/cfs-operator/bin/activate
(cfs-operator) $ which python
/Users/jdeveloper/Documents/venv/cfs-operator/bin/python
```

Once in the `cfs-operator` virtual environment, install the project requirements:

```bash
(cfs-operator) $ pip install -r requirements-dev.txt
...
(cfs-operator) $ pip install -r requirements.txt
...
```

__NOTE__: If you receive errors about `gcc` failing due to OpenSSL issues on a
Mac, export the following FLAGS and retry:

```bash
(cfs-operator) $ CPPFLAGS=-I/usr/local/opt/openssl/include
(cfs-operator) $ LDFLAGS=-L/usr/local/opt/openssl/lib
```

To run the operator in a Kubernetes cluster, download the Kube config file from
the cluster (located in `/etc/kubernetes/admin.conf` on Cray Shasta systems).

```bash
(cfs-operator) $ mkdir ~/.kube
(cfs-operator) $ ssh root@<sms-1>:/etc/kubernetes/admin.conf ~/.kube/config
```

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

## Contributing

Requests for Enhancement and Bugs can be filed in the [CASMCMS Jira project](https://connect.us.cray.com/jira/CreateIssue!default.jspa?selectedProjectKey=CASMCMS).

Members of the CASMCMS team should provide a pull request to master. External
Crayons should fork this repository and provide a pull request to the current release branch.

## Versioning

We use [SemVer](semver.org) for versioning. The version is located in the [.version](.version) file. Other files either
read the version string from this file or have this version string written to them at build time using the 
[update_versions.sh](update_versions.sh) script, based on the information in the 
[update_versions.conf](update_versions.conf) file.

## Authors

* __Randy Kleinman__ - Q1 2019 - _Initial Work_ - rkleinman@cray.com
* (Add your name here for praise or blame later)

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
