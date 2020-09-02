# © Copyright 2020 Hewlett Packard Enterprise Development LP
""" Test the cray/cfs/operator/v1/reconciler.py module """
from unittest.mock import patch, Mock

from cray.cfs.operator.v1 import Reconciler


def test_missed_session_delete():
    """ Test the cray.cfs.operator.v1.reconciler for missed session delete events """

    r = Reconciler()
    with patch.object(r.k8sjobs, 'list_namespaced_job', return_value=_get_mock_jobs()):
        with patch.object(r.k8scrds, 'list_namespaced_custom_object',
                          return_value=_get_mock_sessions()):
            with patch.object(r.session_events, '_handle_deleted') as action_mock:
                r.run_once()
                action_mock.assert_not_called()
                r.run_once()
                action_mock.assert_called_once()


def test_missed_job_added():
    """ Test the cray.cfs.operator.v1.reconciler for missed job added events """

    r = Reconciler()
    with patch.object(r.k8sjobs, 'list_namespaced_job', return_value=_get_mock_jobs()):
        with patch.object(r.k8scrds, 'list_namespaced_custom_object',
                          return_value=_get_mock_sessions(status='pending')):
            with patch.object(r.job_events, '_handle_added') as action_mock:
                r.run_once()
                action_mock.assert_not_called()
                r.run_once()
                action_mock.assert_called_once()


def test_missed_job_modified():
    """ Test the cray.cfs.operator.v1.reconciler for missed job modified events """

    r = Reconciler()
    with patch.object(r.k8sjobs, 'list_namespaced_job', return_value=_get_mock_jobs()):
        with patch.object(r.k8scrds, 'list_namespaced_custom_object',
                          return_value=_get_mock_sessions(status='running')):
            with patch.object(r.job_events, '_handle_modified') as action_mock:
                r.run_once()
                action_mock.assert_not_called()
                r.run_once()
                action_mock.assert_called_once()


def test_missed_session_added():
    """ Test the cray.cfs.operator.v1.reconciler for missed session added events """
    mock_job_response = Mock()
    mock_job_response.items = []

    r = Reconciler()
    with patch.object(r.k8sjobs, 'list_namespaced_job', return_value=mock_job_response):
        with patch.object(r.k8scrds, 'list_namespaced_custom_object',
                          return_value=_get_mock_sessions(status='running')):
            with patch.object(r.session_events, '_handle_added') as action_mock:
                r.run_once()
                action_mock.assert_not_called()
                r.run_once()
                action_mock.assert_called_once()


def _get_mock_jobs():
    mock_job = Mock()
    mock_job.metadata.name = 'test_job'
    mock_job.to_dict.return_value = {
        'metadata': {
            'labels': {
                'cfsession': 'test_session'
            }
        },
        'status': {
            'completion_time': 'now'
        }
    }
    mock_job_response = Mock()
    mock_job_response.items = [mock_job]
    return mock_job_response


def _get_mock_sessions(status=None):
    if status is None:
        return {'items': []}

    mock_session = {
        'metadata': {
            'name': 'test_session'
        },
        'spec': {
            'status': {
                'session': {
                    'status': status
                }
            }
        }
    }
    return {'items': [mock_session]}
