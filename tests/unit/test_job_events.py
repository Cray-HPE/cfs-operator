# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
""" Test the cray/cfs/operator/v1/job_events.py module """
from unittest.mock import patch, Mock

from kubernetes.client import BatchV1Api
from kubernetes import config
config.load_incluster_config = Mock()
config.load_kube_config = Mock()

from cray.cfs.operator.events.session_events import CFSJobMonitor


def test__sync_sessions(session_complete, session_running):
    with patch('cray.cfs.operator.cfs.sessions.get_sessions') as get_sessions:
        get_sessions.return_value = [session_complete, session_running]
        monitor = CFSJobMonitor({'RESOURCE_NAMESPACE': 'foo'})
        monitor._sync_sessions()
        assert(len(monitor.sessions) == 1)
        assert(list(monitor.sessions.keys())[0] == session_running['name'])


def test_monitor_sessions(read_job_mock, session_waiting_for_start, session_waiting_for_complete):
    with patch.object(BatchV1Api, 'read_namespaced_job', read_job_mock):
        with patch('cray.cfs.operator.cfs.sessions.update_session_status'):
            with patch('cray.cfs.operator.cfs.sessions.get_session'):
                monitor = CFSJobMonitor({'RESOURCE_NAMESPACE': 'foo'})
                sessions = [session_waiting_for_start, session_waiting_for_complete]
                monitor.sessions = {session['name']: session for session in sessions}
                monitor.monitor_sessions()
                assert(len(monitor.sessions) == 1)
                assert(list(monitor.sessions.keys())[0] == session_waiting_for_start['name'])


def test_session_complete(read_job_mock, session_no_job, session_missing_job,
                          session_waiting_for_start, session_waiting_for_complete,
                          session_waiting_for_fail, caplog):
    with patch.object(BatchV1Api, 'read_namespaced_job', read_job_mock):
        with patch('cray.cfs.operator.cfs.sessions.update_session_status'):
            with patch('cray.cfs.operator.cfs.sessions.get_session'):
                monitor = CFSJobMonitor({'RESOURCE_NAMESPACE': 'foo'})

                caplog.clear()
                complete = monitor.session_complete(session_no_job)
                assert(complete)
                for record in caplog.records:
                    assert 'This is an invalid state' in record.message

                caplog.clear()
                complete = monitor.session_complete(session_missing_job)
                assert(complete)
                for record in caplog.records:
                    assert 'Job was deleted before CFS could determine success' in record.message

                complete = monitor.session_complete(session_waiting_for_start)
                assert(not complete)

                complete = monitor.session_complete(session_waiting_for_complete)
                assert(complete)

                complete = monitor.session_complete(session_waiting_for_fail)
                assert(complete)


def test_cleanup_jobs(job_completed, job_started, session_waiting_for_complete):
    jobs = Mock()
    jobs.items = [job_completed, job_started]
    with patch.object(BatchV1Api, 'list_namespaced_job', return_value=jobs):
        with patch.object(BatchV1Api, 'delete_namespaced_job'):
            with patch('cray.cfs.operator.cfs.sessions.get_sessions',
                       return_value=[session_waiting_for_complete]):
                monitor = CFSJobMonitor({'RESOURCE_NAMESPACE': 'foo'})
                monitor.cleanup_jobs()
                BatchV1Api.delete_namespaced_job.assert_called_once()

