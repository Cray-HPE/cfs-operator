# © Copyright 2020 Hewlett Packard Enterprise Development LP

import logging
import time

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from cray.cfs.operator.v1 import CFSV1Controller, CFSJobV1Controller
from cray.cfs.operator import RESOURCE_GROUP, RESOURCE_PLURAL

LOGGER = logging.getLogger('cray.cfs.operator.v1.reconciler')

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

v1_RESOURCE_VERSION = 'v1'


class Reconciler(object):
    """
    Handles reconciling missed events and jobs that are out of sync with their sessions.

    Runs every 5 minutes and only makes corrections if the same problem is detected twice
    (i.e. the problem exists for at least 5 minutes)to avoid conflicting with in flight events.
    All corrections are done using the existing event handlers so that state is a consistent
    as possible with correctly handled events.
    """
    def __init__(self, resource_namespace='services', cfs_env={}):
        self.resource_namespace = resource_namespace
        self.session_events = CFSV1Controller(cfs_env)
        self.job_events = CFSJobV1Controller(cfs_env)

        _api_client = client.ApiClient()
        self.k8sjobs = client.BatchV1Api(_api_client)
        self.k8scrds = client.CustomObjectsApi(_api_client)

        self.previous = []
        self.current = []

    def run(self):  # pragma: no cover
        LOGGER.info('Starting session reconciliation loop.')
        while True:
            time.sleep(300)
            self.run_once()

    def run_once(self):
        try:
            jobs = self.k8sjobs.list_namespaced_job(
                namespace=self.resource_namespace,
                label_selector='app.kubernetes.io/name=cray-cfs-aee').items
            crds = self.k8scrds.list_namespaced_custom_object(
                RESOURCE_GROUP, v1_RESOURCE_VERSION,
                self.resource_namespace, RESOURCE_PLURAL)['items']
            self._reconcile_state(jobs, crds)
            self.previous = self.current
            self.current = []
        except Exception as e:
            LOGGER.warning(e, exc_info=True)

    def _reconcile_state(self, jobs, sessions):
        job_map = {job.metadata.name: job.to_dict() for job in jobs}
        session_map = {session['metadata']['name']: session for session in sessions}
        missed_jobs = []

        for job_id, job in job_map.items():
            session_id = job['metadata'].get('labels', {}).get('cfsession', '')
            # Check for missed session delete events
            if session_id not in session_map:
                fake_session = {'metadata': {'labels': {'session-id': job_id[len('cfs-'):]}}}
                self._reconcile_action('session_events', '_handle_deleted',
                                       session_id, fake_session)
                continue

            session = session_map[session_id]
            session_info = session.get('spec', {}).get('status', {}).get('session', {})
            session_status = session_info.get('status', '')
            session_job_id = session_info.get('job', '')
            job_status = job.get('status', {})

            # Check for missed job added events
            if session_status == 'pending' and not session_job_id:
                self._reconcile_action('job_events', '_handle_added', job_id, job)
                missed_jobs.append(session_id)
                continue

            # Check for missed job modified events
            if session_status == 'running' and any((job_status.get(field) is not None)
                                                   for field in ['completion_time', 'failed']):
                self._reconcile_action('job_events', '_handle_modified', job_id, job)
                missed_jobs.append(session_id)
                continue

        # Check for missed session added events
        for session_id, session in session_map.items():
            job_id = session.get('spec', {}).get('status', {}).get('session', {}).get('job', '')
            if not job_id and session_id not in missed_jobs:
                self._reconcile_action('session_events', '_handle_added', session_id, session)

    def _reconcile_action(self, resource_type, action, resource_id, resource):
        key = ':'.join([resource_type, action, resource_id])
        if key in self.previous:
            LOGGER.info('Handling missed {} event for {}: {}'.format(action,
                                                                     resource_type, resource_id))
            handler = getattr(self, resource_type)
            handler_action = getattr(handler, action)
            kwargs = {}
            if action == '_handle_modified':
                kwargs['new'] = True
            try:
                handler_action(resource, resource_id, None, 'reconciler', None, **kwargs)
            except Exception as e:
                LOGGER.debug('Exception while attempting to reconcile {}'.format(e))
        else:
            self.current.append(key)
