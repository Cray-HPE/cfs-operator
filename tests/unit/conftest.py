# Copyright 2019-2020, Cray Inc. All Rights Reserved.
"""
Shared pytest fixtures for cfs-operator
"""
import secrets
from unittest.mock import MagicMock
import uuid

import pytest

from cray.cfs.operator.utils import k8sObj2name, cfs2objectName  # pylint: disable=E402


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


@pytest.fixture
def k8s_svc(random_value):
    svc = MagicMock()
    type(svc).spec = MagicMock(cluster_ip=random_value)
    return svc


@pytest.fixture()
def k8s_svc_list(k8s_svc):
    return MagicMock(items=[k8s_svc])


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
        'CFS_OPERATOR_LOG_LEVEL': 'INFO'
    }


# Event Test Data
@pytest.fixture()
def event_obj_name():
    return secrets.token_hex(8)


@pytest.fixture()
def event_resource_version():
    return secrets.token_hex(8)


@pytest.fixture()
def event_obj_type():
    return secrets.token_hex(8)


@pytest.fixture()
def event_obj_branch():
    return secrets.token_hex(8)


@pytest.fixture()
def event_obj_cloneUrl():
    return secrets.token_hex(8)


@pytest.fixture()
def event_obj(event_obj_name, event_resource_version, event_obj_type,
              event_obj_branch, event_obj_cloneUrl):
    return {
        'metadata': {
            'name': event_obj_name,
            'resourceVersion': event_resource_version,
            'labels': {
                "session-id": str(uuid.uuid4())
            },
            'annotations': {
                'cfs-operator.cray.com/last-known-status': '{}'
            }
        },
        'kind': event_obj_type,
        'spec': {
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
            'status': {},
            'repo': {
                'branch': event_obj_branch,
                'cloneUrl': event_obj_cloneUrl,
            }
        }
    }


@pytest.fixture()
def error_event(event_obj):
    return {'type': 'ERROR', 'raw_object': event_obj}


@pytest.fixture()
def added_event(event_obj):
    return {'type': 'ADDED', 'raw_object': event_obj}


@pytest.fixture()
def modified_event(event_obj):
    return {'type': 'MODIFIED', 'raw_object': event_obj}


@pytest.fixture()
def deleted_event(event_obj):
    return {'type': 'DELETED', 'raw_object': event_obj}


@pytest.fixture()
def job_name(event_obj):
    return cfs2objectName(event_obj)


@pytest.fixture()
def job_event_obj(event_obj, event_obj_type):
    return {
        'metadata': {
            'name': cfs2objectName(event_obj),
            'labels': {
                'cfsession': k8sObj2name(event_obj)
            }
        },
        'kind': event_obj_type,
        'spec': {}
    }


@pytest.fixture()
def job_added_event(job_event_obj):
    return {'type': 'ADDED', 'raw_object': job_event_obj}


@pytest.fixture()
def job_modified_event(job_event_obj):
    return {'type': 'ADDED', 'raw_object': job_event_obj}
