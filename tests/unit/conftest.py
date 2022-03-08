#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Shared pytest fixtures for cfs-operator
"""
import copy
import datetime
import secrets
from unittest.mock import MagicMock, Mock
from kubernetes.client.rest import ApiException

import pytest


@pytest.fixture()
def random_value():
    return secrets.token_hex(8)


# Fake Kubernetes Objects and Exceptions
@pytest.fixture()
def k8s_api_response():
    """ Return an object that looks like an API response from Kubernetes. """
    class FauxK8sResponse(object):
        def to_dict(self, *args, **kwargs):
            return {}

    def _make_response():
        return FauxK8sResponse()

    yield _make_response


# Environment Test Data
@pytest.fixture()
def aee_env():
    return {
        'CRAY_CFS_CONFIGMAP_PUBLIC_KEY': 'foo',
        'CRAY_CFS_CA_PUBLIC_KEY': 'bar',
        'CRAY_CFS_AEE_PRIVATE_KEY': 'baz',
        'CRAY_CFS_UTIL_IMAGE': 'zing',
        'CRAY_CFS_AEE_IMAGE': 'zork',
        'CRAY_CFS_IMS_IMAGE': 'zap',
        'RESOURCE_NAMESPACE': 'zang',
        'CRAY_CFS_SERVICE_ACCOUNT': 'zoom',
        'CRAY_CFS_API_DB_SERVICE_HOST': 'zaz',
        'CRAY_CFS_API_DB_SERVICE_PORT_REDIS': '12345',
        'CFS_OPERATOR_LOG_LEVEL': 'INFO',
        'CRAY_CFS_TRUST_KEY_SECRET': 'boo',
        'CRAY_CFS_TRUST_CERT_SECRET': 'dew'
    }


# Event Test Data
@pytest.fixture()
def session_name():
    return secrets.token_hex(8)


@pytest.fixture()
def job_id():
    return secrets.token_hex(8)


@pytest.fixture()
def session_data_v2(session_name, job_id):
    return {
        'name': session_name,
        'target': {
            'definition': '',
            'groups': [],
        },
        'ansible': {
            'config': 'foo',
            'verbosity': 2,
            'limit': None,
        },
        'status': {
            'session': {
                'job': job_id,
                'status': 'pending'
            }
        },
        'configuration': {
            'name': 'test',
            'limit': '',
        }
    }


@pytest.fixture()
def session_data_v1(session_name, job_id):
    return {
        'name': session_name,
        'target': {
            'definition': '',
            'groups': [],
        },
        'ansible': {
            'playbook': 'foo.yml',
            'config': 'foo',
            'verbosity': 2,
            'limit': None,
        },
        'status': {
            'session': {
                'job': job_id,
                'status': 'pending'
            }
        },
        'repo': {
            'branch': 'testbranch',
            'cloneUrl': 'https://testurl/repo',
        }
    }


@pytest.fixture()
def create_event_v2(session_data_v2):
    return {'type': 'CREATE', 'data': session_data_v2}


@pytest.fixture()
def create_event_v1(session_data_v1):
    return {'type': 'CREATE', 'data': session_data_v1}


@pytest.fixture()
def delete_event(session_data_v2):
    return {'type': 'DELETE', 'data': session_data_v2}


@pytest.fixture()
def session_complete(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['status'] = 'complete'
    data['name'] = 'complete'
    return data


@pytest.fixture()
def session_running(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['status'] = 'running'
    data['name'] = 'incomplete'
    return data


@pytest.fixture()
def session_no_job(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['job'] = None
    data['name'] = 'no_job'
    return data


@pytest.fixture()
def session_missing_job(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['job'] = 'missing'
    data['name'] = 'missing_job'
    return data


@pytest.fixture()
def session_waiting_for_start(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['job'] = 'start'
    data['name'] = 'wait_for_start'
    return data


@pytest.fixture()
def session_waiting_for_complete(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['job'] = 'complete'
    data['name'] = 'wait_for_complete'
    return data


@pytest.fixture()
def session_waiting_for_fail(session_data_v2):
    data = copy.deepcopy(session_data_v2)
    data['status']['session']['job'] = 'fail'
    data['name'] = 'wait_for_fail'
    return data


@pytest.fixture()
def job_started():
    job = Mock()
    job.metadata.name = 'start'
    job.status.start_time = datetime.datetime.now()
    job.status.completion_time = None
    job.status.failed = None
    return job


@pytest.fixture()
def job_completed():
    job = Mock()
    job.metadata.name = 'complete'
    job.status.start_time = None
    job.status.completion_time = datetime.datetime.now()
    job.status.failed = None
    return job


@pytest.fixture()
def job_failed():
    job = Mock()
    job.status.start_time = None
    job.status.completion_time = None
    job.status.failed = True
    con = Mock()
    con.last_transition_time = datetime.datetime.now()
    job.status.conditions = [con]
    return job


@pytest.fixture()
def read_job_mock(job_started, job_completed, job_failed):
    def read_job(self, job_name, *args):
        jobs = {
            'start': job_started,
            'complete': job_completed,
            'fail': job_failed,
        }
        try:
            job = jobs[job_name]
            return job
        except KeyError:
            e = ApiException()
            e.status = 404
            raise e
    return read_job


@pytest.fixture()
def config_response():
    return {
        'name': 'testconfig',
        'layers': [
            {
                'commit': 'testcommit',
                'cloneUrl': 'https://testurl/repo',
                'playbook': 'foo.yml'
            }
        ]
    }


@pytest.fixture()
def mock_options():
    options = MagicMock(default_ansible_config='testconfig',
                        additional_inventory_url='https://testurl/additional')
    return options
