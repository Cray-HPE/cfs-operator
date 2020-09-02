# © Copyright 2019-2020 Hewlett Packard Enterprise Development LP
""" Test the cray/cfs/operator/v1/job_events.py module """
import datetime
import json
import logging
from unittest.mock import patch

from kubernetes.client import BatchV1Api
from kubernetes.client.rest import ApiException
from redis import Redis

from cray.cfs.k8s import CFSV1K8SConnector
from cray.cfs.operator.v1.job_events import CFSJobV1Controller


def test__handle_added(job_added_event, job_event_obj, job_name, event_obj_type,
                       event_resource_version):
    """ Test the cray.cfs.operator.v1.job_events._handle_added method """
    # New Job
    expected = {'spec': {'status': {'session': {
        'job': job_name,
        'status': 'pending',
        'succeeded': "none",
    }}}}

    job_event_obj['status'] = 'foo'
    with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
        with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
                as usa_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_added(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_added_event
            )
            ucs_mock.assert_called_once_with(job_event_obj, expected)
            usa_mock.assert_called_once_with(job_name, job_event_obj['status'])

    # Existing Job (operator restart case)
    expected = {'spec': {'status': {'session': {
        'job': job_name,
        'status': 'running',
        'startTime': 'now'
    }}}}

    metadata = {
        'annotations': {
            'cfs-operator.cray.com/last-known-status': json.dumps({})
        }
    }
    job_added_event['raw_object']['metadata'] = metadata
    job_event_obj['status'] = {'startTime': 'now'}
    with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
        with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
                as usa_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_added(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_added_event
            )
            ucs_mock.assert_not_called()
            usa_mock.assert_not_called()


def test__handle_modified(job_modified_event, job_event_obj, job_name, event_obj_type,
                          event_resource_version, caplog):
    """ Test the cray.cfs.operator.v1.job_events._handle_modified method """
    # New job with no status yet
    job_event_obj['status'] = {'baz': 'zing'}
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        with patch.object(CFSJobV1Controller, '_update_cfs_status') as ucs_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_modified_event
            )
    usa_mock.assert_called_once_with(job_name, {'baz': 'zing'})
    ucs_mock.assert_not_called()

    # Existing Job - Job transitioned to running state
    start = datetime.datetime.now()
    old_status = {'baz': 'zing'}
    job_event_obj['metadata']['annotations'] = {
        'cfs-operator.cray.com/last-known-status': json.dumps(old_status)
    }
    job_event_obj['status'] = {
        'active': 1,
        'completion_time': None,
        'failed': None,
        'startTime': start,
        'succeeded': None,
    }
    expected = {'spec': {'status': {'session': {
        'job': job_name,
        'status': 'running',
        'startTime': start
    }}}}
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_modified_event
            )
    usa_mock.assert_called_once_with(job_name, job_event_obj['status'])
    ucs_mock.assert_called_once_with(job_event_obj, expected)

    # Existing Job - Job change
    caplog.set_level(logging.INFO)
    job_event_obj['metadata']['annotations'] = {
        'cfs-operator.cray.com/last-known-status': json.dumps(old_status)
    }
    job_event_obj['status'] = {
        'baz': 'bar',
    }
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
            job_event_obj, job_name, event_obj_type, event_resource_version,
            job_modified_event
        )
    usa_mock.assert_called_once_with(job_name, job_event_obj['status'])
    for record in caplog.records:
        assert 'EVENT: Unhandled change' in record.message

    # Existing Job - Job finished successfully
    complete = datetime.datetime.now()
    job_event_obj['metadata']['annotations'] = {
        'cfs-operator.cray.com/last-known-status': json.dumps(old_status)
    }
    job_event_obj['status'] = {
        'completionTime': complete,
        'startTime': start,
        'succeeded': 1,
    }
    expected = {'spec': {'status': {'session': {
        'job': job_name,
        'succeeded': 'true',
    }}}}
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_modified_event
            )
    usa_mock.assert_called_once_with(job_name, job_event_obj['status'])
    ucs_mock.assert_called_once_with(job_event_obj, expected)

    # Existing Job - Job failure
    job_event_obj['metadata']['annotations'] = {
        'cfs-operator.cray.com/last-known-status': json.dumps(old_status)
    }
    job_event_obj['status'] = {
        'failed': 1,
    }
    expected = {'spec': {'status': {'session': {
        'job': job_name,
        'status': 'complete',
        'succeeded': 'false',
    }}}}
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
            CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
                job_event_obj, job_name, event_obj_type, event_resource_version, job_modified_event
            )
    usa_mock.assert_called_once_with(job_name, job_event_obj['status'])
    ucs_mock.assert_called_once_with(job_event_obj, expected)

    # Existing Job - Job completed
    old_status = {'baz': 'zing', 'active': 1}
    complete = datetime.datetime.now()
    job_event_obj['metadata']['annotations'] = {
        'cfs-operator.cray.com/last-known-status': json.dumps(old_status)
    }
    job_event_obj['status'] = {}
    with patch.object(CFSJobV1Controller, '_update_status_annotation', return_value=None) \
            as usa_mock:
        with patch.object(CFSJobV1Controller, '_update_cfs_status', return_value=None) as ucs_mock:
            with patch.object(CFSJobV1Controller, '_get_aggregate_status', return_value=None) \
                    as gas_mock:
                CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._handle_modified(
                    job_event_obj, job_name, event_obj_type, event_resource_version,
                    job_modified_event
                )
    usa_mock.assert_called_once_with(job_name, job_event_obj['status'])
    ucs_mock.assert_called_once()
    gas_mock.assert_called_once_with(job_event_obj)


def test__update_cfs_status(job_event_obj, event_obj_name, caplog):
    """ Test the cray.cfs.operator.v1.job_events._update_cfs_status method """
    # All good
    with patch.object(CFSV1K8SConnector, 'patch', return_value='bar') as cfsk8spatch:
        body = {'foo': 'bar'}
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._update_cfs_status(job_event_obj, body)
        cfsk8spatch.assert_called_once_with(event_obj_name, body, namespace='foo')
        for record in caplog.records:
            assert 'Updated ConfigFrameworkSession' in record.message

    # Not found API error retrieving service information
    with patch.object(CFSV1K8SConnector, 'patch', side_effect=ApiException(status=404)) \
            as cfsk8spatch:
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._update_cfs_status(job_event_obj, body)
        cfsk8spatch.assert_called_once_with(event_obj_name, body, namespace='foo')
        for record in caplog.records:
            assert 'Unable to update ConfigFrameworkSession' in record.message

    # Other API error retrieving service information
    with patch.object(CFSV1K8SConnector, 'patch', side_effect=ApiException(status=500)) \
            as cfsk8spatch:
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._update_cfs_status(job_event_obj, body)
        cfsk8spatch.assert_called_once_with(event_obj_name, body, namespace='foo')
        for record in caplog.records:
            assert 'Unable to update ConfigFrameworkSession' in record.message


def test__update_status_annotation(job_name, caplog):
    """ Test the cray.cfs.operator.v1.job_events._update_status_annotation method """
    state = {'foo': 'bar'}
    expected = {
        'metadata': {
            'annotations': {
                'cfs-operator.cray.com/last-known-status': json.dumps(state)
            }
        }
    }
    with patch.object(BatchV1Api, 'patch_namespaced_job', side_effect=ApiException(status=500)) \
            as client_mock:
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._update_status_annotation(job_name, state)
        client_mock.assert_called_once_with(job_name, 'foo', expected)
        for record in caplog.records:
            assert 'Unable to update Job' in record.message


def test__get_aggregate_status(job_event_obj, caplog, event_obj_name, k8s_svc_list):
    """
    Test the cray.cfs.operator.v1.job_events._get_aggregate_status method when
    an API error occurs
    """
    # Successfully retrieved service information, Redis error
    with patch.object(Redis, 'scard', side_effect=Exception):
        CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})._get_aggregate_status(job_event_obj)
        for record in caplog.records:
            assert 'Unable to get target status' in record.message

    # All good
    caplog.clear()
    expected = {'spec': {'status': {'targets': {
                'running': 1, 'failed': 2, 'success': 3,
                }}}}
    with patch.object(Redis, 'scard', side_effect=[1, 2, 3]):
        with patch.object(CFSJobV1Controller, '_update_cfs_status'):
            conn = CFSJobV1Controller({'RESOURCE_NAMESPACE': 'foo'})
            conn._get_aggregate_status(job_event_obj)
            conn._update_cfs_status.assert_called_once_with(job_event_obj, expected)
