# © Copyright 2019-2020 Hewlett Packard Enterprise Development LP
"""
Functions for handling Kubernetes Job Events related to CFS (v1) CRDs.
"""
from datetime import datetime
import json
import logging

from dictdiffer import diff
from kubernetes import config, client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

from cray.cfs.k8s import CFSV1K8SConnector
from cray.cfs.operator.controller import BaseController
from cray.cfs.operator.utils import object2cfsName

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8ssvcs = client.CoreV1Api(_api_client)
k8sjobs = client.BatchV1Api(_api_client)

LOGGER = logging.getLogger('cray.cfs.operator.v1.job_events')
cfs_api = CFSV1K8SConnector(retries=10)


class CFSJobV1Controller(BaseController):

    def _handle_added(self, obj, name, obj_type, resource_version, event):
        # Update the associated CFS with job initial status, but only if this
        # Job is actually new (and this event isn't just because the operator
        # restarted)
        new = False
        if 'annotations' not in obj['metadata']:
            new = True
            body = {'spec': {'status': {'session': {
                'job': name,
                'status': 'pending',
                'succeeded': "none",
            }}}}
            self._update_cfs_status(obj, body)
            self._update_status_annotation(name, obj['status'])

        # In the case that the operator starts watching Kubernetes events when CFS jobs have
        # already been created, Kubernetes sends synthetic "Added" events that represent the current
        # state. If annotations exist, this is the case and we need to handle state
        # reconciliation.
        self._handle_modified(obj, name, obj_type, resource_version, event, new=new)

    def _handle_modified(self, obj, name, obj_type, resource_version, event, new=False):
        current_status = obj['status']
        LOGGER.debug("Job status %s: %s", name, current_status)

        # Existing job
        if new:
            last_status = {}
        else:
            last_status = json.loads(
                obj['metadata'].get('annotations', {}).get(
                    'cfs-operator.cray.com/last-known-status', {}))
        changes = diff(
            last_status,
            current_status
        )
        for op, _, items in changes:
            LOGGER.debug(
                "STATUS: Changed Job=%s: %s (version=%s)", name, (op, _, items), resource_version
            )

            # When the op is change, dict(items) below breaks
            if op == 'change':
                LOGGER.info(
                    "EVENT: Unhandled change operation: Job=%s: %s (version=%s)",
                    name, (op, _, items), resource_version
                )
                continue

            items = dict(items)

            # Job transitioned to running state, update CFS
            if op == 'add' and self._get_field('start_time', items) is not None:
                body = {'spec': {'status': {'session': {
                    'job': name,
                    'status': 'running',
                    'startTime': self._get_field('start_time', items)
                }}}}
                self._update_cfs_status(obj, body)

            # Job finished successfully
            if op == 'add' and self._get_field('completion_time', items) is not None:
                body = {'spec': {'status': {'session': {
                    'job': name,
                    'status': 'complete',
                    'succeeded': 'true',
                    'completionTime': self._get_field('completion_time', current_status)
                }}}}
                self._get_aggregate_status(obj)
                self._update_cfs_status(obj, body)

            # Job Failure
            if op == 'add' and self._get_field('failed', items) is not None:
                condition = current_status['conditions'][0]
                body = {'spec': {'status': {'session': {
                    'job': name,
                    'status': 'complete',
                    'succeeded': 'false',
                    'completionTime': self._get_field('last_transition_time', condition)
                }}}}
                self._get_aggregate_status(obj)
                self._update_cfs_status(obj, body)

        self._update_status_annotation(name, current_status)

    def _get_field(self, field, data):
        # Pass snake_case to check both snake and CamelCase.
        # Needed because k8s events are returned differently then resource lookups
        if field in data:
            return data[field]
        altfield = ''.join((word.title() if i != 0 else word)
                           for i, word in enumerate(field.split('_')))
        if altfield in data:
            return data[altfield]
        return None

    def _update_cfs_status(self, obj, body):
        """ Update the CFS associated with this job based on job events in `body` """
        cfs_name = object2cfsName(obj)
        try:
            resp = cfs_api.patch(cfs_name, body, namespace=self.env['RESOURCE_NAMESPACE'])
            LOGGER.debug(
                'Updated ConfigFrameworkSession=%s status. Response=%s',
                cfs_name, json.dumps(resp, indent=2)
            )
        except ApiException as err:
            if err.status == 404:
                LOGGER.warning(
                    "Unable to update ConfigFrameworkSession=%s status: not found", cfs_name
                )
            else:
                LOGGER.warning(
                    "Unable to update ConfigFrameworkSession=%s status: %s", cfs_name, err
                )

    def _update_status_annotation(self, name, status):
        """
        Update the job annotation with its current status for future diffs
        """
        body = {
            'metadata': {
                'annotations': {
                    'cfs-operator.cray.com/last-known-status': json.dumps(status)
                }
            }
        }
        try:
            k8sjobs.patch_namespaced_job(name, self.env['RESOURCE_NAMESPACE'], body)
        except ApiException as err:
            LOGGER.warning("Unable to update Job=%s status annotation: %s", name, err)

    def _get_aggregate_status(self, obj):
        """
        Fetch the 'running', 'failed', 'success' fields from the redis instance
        associated with this session
        """
        cfs_name = object2cfsName(obj)
        failed = None
        success = None
        running = None
        try:
            running = self.redis_client.scard('sessions/%s/running' % cfs_name)
            failed = self.redis_client.scard('sessions/%s/failed' % cfs_name)
            success = self.redis_client.scard('sessions/%s/success' % cfs_name)
        except Exception as err:
            # This is not a fatal error, just no session-level status is
            # reported in the CRD/API.
            LOGGER.warning(
                "Unable to get target status from redis server for ConfigFrameworkSession=%s: %s",
                cfs_name, err
            )

        # A job may fail Ansible, which means it completed and we should grab
        # the results.
        if all([failed is not None, success is not None, running is not None]):
            body = {'spec': {'status': {'targets': {
                'failed': failed, 'running': running, 'success': success
            }}}}
            self._update_cfs_status(obj, body)

        return
