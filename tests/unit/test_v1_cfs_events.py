# Copyright 2019-2020, Cray Inc. All Rights Reserved.
""" Test the cray/cfs/operator/v1/cfs_events.py module """
import json
import logging
from unittest.mock import patch, Mock

from kubernetes.client import BatchV1Api, AppsV1Api, NetworkingV1Api, CoreV1Api, CustomObjectsApi
from kubernetes.client.rest import ApiException

from kubernetes import config
config.load_incluster_config = Mock()
config.load_kube_config = Mock()
from cray.cfs.k8s import CFSV1K8SConnector                   # pylint: disable=E402
from cray.cfs.operator.v1.cfs_events import CFSV1Controller  # pylint: disable=E402
from cray.cfs.operator.utils import cfs2sessionId, cfs2objectName  # pylint: disable=E402


def test__handle_added(added_event, event_obj_name, event_resource_version,
                       event_obj_type, event_obj, k8s_svc, random_value):
    """ Test the cray.cfs.operator.v1.cfs_events._handle_added method """
    # Existing Job (operator restart case)
    existing = {
        'spec': {
            'status': {
                'session': {
                    'job': 'foo'
                }
            }
        }
    }
    added_event['raw_object'] = existing
    with patch.object(CFSV1K8SConnector, 'patch') as cfsk8spatch:
        with patch.object(CFSV1Controller, '_create_k8s_job') as cfs_job:
            conn = CFSV1Controller({})
            conn._handle_added(
                existing, event_obj_name, event_obj_type, event_resource_version,
                added_event
            )
            cfsk8spatch.assert_not_called()
            cfs_job.assert_not_called()

    # New CFS Event
    added_event['raw_object'] = event_obj
    body = {
        'metadata': {
            'labels': {
                'session-id': cfs2sessionId(event_obj)
            },
            'annotations': {
                'cfs-operator.cray.com/last-known-status': json.dumps({})
            }
        }
    }
    with patch.object(CFSV1K8SConnector, 'patch', return_value='bar') as cfsk8spatch:
        with patch.object(CFSV1Controller, '_create_k8s_job') as cfs_job:
            conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
            conn._handle_added(
                event_obj, event_obj_name, event_obj_type, event_resource_version,
                added_event
            )
            cfsk8spatch.assert_called_once_with(event_obj_name, body, namespace='foo')
            cfs_job.assert_called_once_with('bar')


def test__handle_modified(modified_event, event_obj_name, event_resource_version, event_obj_type,
                          event_obj, caplog):
    """ Test the cray.cfs.operator.v1.cfs_events._handle_modified method """
    caplog.set_level(logging.WARNING)
    # No Changes
    with patch.object(CFSV1K8SConnector, 'patch') as cfsk8spatch:
        conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
        conn._handle_modified(
            event_obj, event_obj_name, event_obj_type, event_resource_version,
            modified_event
        )
        cfsk8spatch.assert_not_called()

    # A Change
    event_obj['spec']['status'] = {"foo": "bar"}
    modified_event['raw_object'] = event_obj
    with patch.object(CFSV1K8SConnector, 'patch') as cfsk8spatch:
        conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
        conn._handle_modified(
            event_obj, event_obj_name, event_obj_type, event_resource_version,
            modified_event
        )
        cfsk8spatch.assert_called_with(
            event_obj_name,
            {'metadata': {'annotations': {
                'cfs-operator.cray.com/last-known-status': json.dumps(event_obj['spec']['status'])
            }}},
            namespace='foo'
        )
        for record in caplog.records:
            assert 'STATUS: Changed' in record.message


def test__handle_deleted(deleted_event, event_obj_name, event_resource_version, event_obj_type,
                         event_obj):
    """ Test the cray.cfs.operator.v1.cfs_events._handle_deleted method """
    with patch.object(CFSV1Controller, '_delete_job'):
        conn = CFSV1Controller({})
        conn._handle_deleted(
            event_obj, event_obj_name, event_obj_type, event_resource_version,
            deleted_event
        )
        conn._delete_job.assert_called_once_with(event_obj, event_obj_name)


def test__delete_job(event_obj, event_obj_name, k8s_api_response, caplog):
    """ Test the cray.cfs.operator/v1/cfs_events._delete_job method """
    caplog.set_level(logging.WARNING)
    # Successful response
    with patch.object(BatchV1Api, 'delete_namespaced_job', return_value=k8s_api_response()):
        conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
        conn._delete_job(event_obj, event_obj_name)
        BatchV1Api.delete_namespaced_job.assert_called_once_with(
            cfs2objectName(event_obj),
            'foo',
            propagation_policy='Background'
        )
        for record in caplog.records:
            assert 'Job deleted' in record.message

    # Missing Job
    caplog.clear()
    with patch.object(BatchV1Api, 'delete_namespaced_job', side_effect=ApiException(status=404)):
        conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
        conn._delete_job(event_obj, event_obj_name)
        for record in caplog.records:
            assert 'Job not deleted; not found' in record.message

    # Some other API error
    caplog.clear()
    with patch.object(BatchV1Api, 'delete_namespaced_job', side_effect=ApiException(status=500)):
        conn = CFSV1Controller({'RESOURCE_NAMESPACE': 'foo'})
        conn._delete_job(event_obj, event_obj_name)
        for record in caplog.records:
            assert 'Exception calling BatchV1Api->delete_namespaced_job' in record.message


def test__create_k8s_job(event_obj, k8s_api_response, aee_env, caplog):
    """ Test the cray.cfs.operator/v1/cfs_events._create_k8s_job method """
    caplog.set_level(logging.DEBUG)
    # Successful response
    with patch.object(BatchV1Api, 'create_namespaced_job', return_value=k8s_api_response()):
        conn = CFSV1Controller(aee_env)
        conn._create_k8s_job(event_obj)
        BatchV1Api.create_namespaced_job.assert_called_once()
    for record in caplog.records:
        assert 'Job request created' in record.message

    # Some other API error
    caplog.clear()
    with patch.object(BatchV1Api, 'create_namespaced_job', side_effect=ApiException(status=500)):
        conn = CFSV1Controller(aee_env)
        conn._create_k8s_job(event_obj)
        BatchV1Api.create_namespaced_job.assert_called_once()
    for record in caplog.records:
        assert 'Unable to create Job' in record.message


def test__create_k8s_job_image_customization(event_obj, k8s_api_response, aee_env, caplog):
    """ Test the cray.cfs.operator/v1/cfs_events._create_k8s_job method when target/def = image """
    caplog.set_level(logging.DEBUG)
    # Successful response
    event_obj['spec']['target']['definition'] = 'image'
    with patch.object(BatchV1Api, 'create_namespaced_job', return_value=k8s_api_response()):
        conn = CFSV1Controller(aee_env)
        conn._create_k8s_job(event_obj)
        BatchV1Api.create_namespaced_job.assert_called_once()
    for record in caplog.records:
        assert 'Job request created' in record.message
