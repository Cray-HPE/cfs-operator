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
Functions for handling Job Events related to CFS.
"""
import logging
import threading
import time

from requests.exceptions import HTTPError

from kubernetes import config, client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

import cray.cfs.operator.cfs.sessions as cfs_sessions

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8s_jobs = client.BatchV1Api(_api_client)

LOGGER = logging.getLogger('cray.cfs.operator.events.job_events')


class CFSJobMonitor:
    def __init__(self, env):
        self.namespace = env['RESOURCE_NAMESPACE']
        self.sessions = {}

    def _sync_sessions(self):
        # Load incomplete and unmonitored sessions
        session_list = cfs_sessions.get_sessions()
        for session in session_list:
            session_status = session.get('status', {}).get('session', {})
            if session['name'] not in self.sessions and \
                    session_status.get('job') and \
                    not session_status.get('status') == 'complete':
                self.add_session(session)

    def _run(self):  # pragma: no cover
        intervals = 0
        while True:
            try:
                self.monitor_sessions()
                if intervals >= 10:
                    # Periodically check for out of sync sessions
                    self._sync_sessions()
                    intervals = 0
            except Exception as e:
                LOGGER.warning('Exception monitoring sessions: {}'.format(e))
            intervals += 1
            time.sleep(30)

    def _run_cleanup(self):  # pragma: no cover
        while True:
            try:
                self.cleanup_jobs()
                time.sleep(60*60)
            except Exception as e:
                LOGGER.warning('Exception running cleanup: {}'.format(e))

    def run(self):  # pragma: no cover
        while True:
            try:
                self._sync_sessions()
            except Exception as e:
                LOGGER.warning('Exception during initial session sync: {}'.format(e))
                time.sleep(30)
            else:
                break
        threading.Thread(target=self._run).start()
        threading.Thread(target=self._run_cleanup).start()

    def monitor_sessions(self):
        try:
            completed_sessions = []
            # Use list(keys()) rather than .items() so that other threads can edit dict
            for name in list(self.sessions.keys()):
                if self.session_complete(self.sessions[name]):
                    completed_sessions.append(name)
            for name in completed_sessions:
                self.remove_session(name)
        except Exception as e:
            LOGGER.error('Exception encountered while monitoring jobs: {}'.format(e))

    def cleanup_jobs(self):
        try:
            jobs = self.get_jobs()
            sessions = cfs_sessions.get_sessions()
            session_jobs = self.get_session_jobs(sessions)
            i = 0
            for job in jobs:
                if job not in session_jobs:
                    self.delete_job(job)
                    i += 1
            if i:
                LOGGER.info('Cleanup removed {} orphaned cfs jobs'.format(i))
        except Exception as e:
            LOGGER.warning('Exception encountered while cleaning jobs: {}'.format(e))

    def add_session(self, session):
        self.sessions[session['name']] = session

    def remove_session(self, session_name):
        self.sessions.pop(session_name, None)

    def session_complete(self, session):
        session_name = session['name']
        if self._session_missing(session_name):
            LOGGER.warning('Session {} was being monitored but can no longer be found')
            return True

        job_name = session['status']['session'].get('job')
        if not job_name:
            # This shouldn't be able to happen.
            # Session jobs are only monitored if the job has been created.
            LOGGER.warning('No job is specified for session {}.  This is an invalid state.'.format(
                session['name']))
            return True
        try:
            job = k8s_jobs.read_namespaced_job(job_name, self.namespace)
        except ApiException as e:
            if getattr(e, 'status', None) == 404:
                LOGGER.warning('Job was deleted before CFS could determine success.')
                cfs_sessions.update_session_status(session_name, data={'status': 'complete',
                                                                       'succeeded': 'unknown'})
                return True
            else:
                LOGGER.warning("Unable to fetch Job=%s", job_name, e)
                return False
        session_status = session.get('status', {}).get('session', {})
        if job.status.start_time and session_status.get('status') == 'pending':
            LOGGER.info("EVENT: JobStart %s", session_name)
            cfs_sessions.update_session_status(session_name, data={'status': 'running'})
            # Set so that update_session_status is not called again for status
            session_status['status'] = 'running'
        if job.status.completion_time:
            LOGGER.info("EVENT: JobComplete %s", session_name)
            completion_time = job.status.completion_time.isoformat().split('+')[0]
            cfs_sessions.update_session_status(session_name,
                                               data={'status': 'complete',
                                                     'succeeded': 'true',
                                                     'completionTime': completion_time})
            return True
        elif job.status.failed:
            LOGGER.info("EVENT: JobFail %s", session_name)
            completion_time = job.status.conditions[0].last_transition_time
            completion_time = completion_time.isoformat().split('+')[0]
            cfs_sessions.update_session_status(session_name,
                                               data={'status': 'complete',
                                                     'succeeded': 'false',
                                                     'completionTime': completion_time})
            return True
        return False

    def _session_missing(self, session_name):
        try:
            cfs_sessions.get_session(session_name)
        except HTTPError as e:
            if e.response.status_code == 404:
                return True
        return False

    def get_session_jobs(self, sessions):
        jobs = []
        for session in sessions:
            job_name = session['status']['session'].get('job')
            if job_name:
                jobs.append(job_name)
        return jobs

    def get_jobs(self):
        jobs = k8s_jobs.list_namespaced_job(self.namespace,
                                            label_selector='app.kubernetes.io/name=cray-cfs-aee')
        job_names = [job.metadata.name for job in jobs.items]
        return job_names

    def delete_job(self, job_name):
        k8s_jobs.delete_namespaced_job(job_name, self.namespace)
