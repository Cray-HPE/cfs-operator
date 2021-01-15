# Cray Configuration Framework Service Operator

A Kubernetes custom resource definition (CRD) and operator for managing Ansible
Execution Environments through the [Cray Configuration Framework Service](https://stash.us.cray.com/projects/SCMS/repos/config-framework-service/browse).
The `ConfigFrameworkSession` CRD manages the setup, launch, and teardown of
[Ansible Execution Environments](https://stash.us.cray.com/projects/SCMS/repos/ansible-execution-environment/browse)
(AEE) and provides status information from the AEE runs.

Overall architecture of Shasta Configuration Management can be found in its
[design document](https://connect.us.cray.com/confluence/x/ZKmfBw).

## Getting Started

These instructions will get you a copy of the project up and running on your
local machine for development and testing purposes. See deployment for notes on
how to deploy the project on a live system.

### Prerequisites

1. A Python 3.6-based virtual environment,
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

### Running the Operator Locally

A development version of the operator can be run locally within the context of
an external Kubernetes cluster.

__WARNING__: _Ensure that no other instance of the operator is running
simultaneously in the cluster._

__NOTE__: When running the operator off-cluster, you will not be able to capture
results from the Redis instances since the IP address of the Redis service is
not accessible externally.

Build the operator Docker image locally:

```bash
docker build --rm -f "Dockerfile" -t cray-cfs-operator:dev .
```

and run the image locally in a container:

```bash
docker run --rm \
    -v /Users/$USER/.kube/:/root/.kube/ \
    -e "CFS_OPERATOR_LOG_LEVEL=INFO" \
    -e "CRAY_CFS_CA_PUBLIC_KEY=certificate_authority.crt" \
    -e "CRAY_CFS_CONFIGMAP_PUBLIC_KEY=cray-configmap-ca-public-key" \
    -e "CRAY_CFS_AEE_IMAGE=dtr.dev.cray.com:443/cray/cray-aee:latest" \
    -e "CRAY_CFS_UTIL_IMAGE=dtr.dev.cray.com:443/alpine/git:1.0.7" \
    -e "CRAY_CFS_AEE_PRIVATE_KEY=cray-cfs-aee-privatekey" \
    -e "CRAY_CFS_IMS_IMAGE=cray-cfs-operator:dev" \
    -e "CRAY_CFS_SERVICE_ACCOUNT=cray-cfs" \
    -e "CRAY_CFS_REDIS_IMAGE=dtr.dev.cray.com/library/redis:5.0-alpine" \
    cray-cfs-operator:dev
```

The command above gives the minimum required parameters to be able to create
AEEs with the operator. Debug logging can be introduced with
`CFS_OPERATOR_LOG_LEVEL=DEBUG`. The other parameters should be cross-referenced
with the values in the `cray_cfs_operator` Ansible role defaults
[main.yml](./ansible/roles/cray_cfs_operator/defaults/main.yml) file for the
keys in the [operator template file](./ansible/roles/cray_cfs_operator/templates/cray-cfs-operator.yaml.j2).

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

The operator is deployed as part of the [L3 Installer](https://stash.us.cray.com/projects/SCMS/repos/l3-installer/browse)
on Cray Shasta systems.

## Built With

* [Python 3](https://docs.python.org/3/)
* [Kubernetes Python Client](https://github.com/kubernetes-client/python)
* [Redis](https://redis-py.readthedocs.io/en/latest/)
* [Ansible](https://docs.ansible.com)

## Contributing

Requests for Enhancement and Bugs can be filed in the [CASMCMS Jira project](https://connect.us.cray.com/jira/CreateIssue!default.jspa?selectedProjectKey=CASMCMS).

Members of the CASMCMS team should provide a pull request to master. External
Crayons should fork this repository and provide a pull request to master.

## Versioning

We use [SemVer](semver.org) for versioning. The version should be changed in the
following locations:

1. the repository [`.version`](./.version) file
2. the `cray.cfs.operator` Python package [`setup.py`](./src/setup.py) file

## Authors

* __Randy Kleinman__ - Q1 2019 - _Initial Work_ - rkleinman@cray.com
* (Add your name here for praise or blame later)

## License

Copyright 2019, Cray Inc. All Rights Reserved.
