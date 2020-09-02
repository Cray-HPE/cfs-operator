#!/usr/bin/env python
# © Copyright 2019-2020 Hewlett Packard Enterprise Development LP
"""
CFS Operator - A Python implementation of a Kubernetes Operator for the
Cray Configuration Framework Service.
"""

import logging
import threading
import os
from pkg_resources import get_distribution
import random
import time
from urllib3.exceptions import MaxRetryError
import queue

from kubernetes import config, watch, client
from kubernetes.config.config_exception import ConfigException

# CRD Imports
from . import RESOURCE_GROUP, RESOURCE_PLURAL

# CRD version v1 imports
from .v1 import CFSV1Controller, CFSJobV1Controller, Reconciler
from .v1 import RESOURCE_VERSION as v1_RESOURCE_VERSION
from cray.cfs.operator.liveness.timestamp import Timestamp


LOGGER = logging.getLogger('cray.cfs.operator')
try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8sjobs = client.BatchV1Api(_api_client)
k8scrds = client.CustomObjectsApi(_api_client)

def _capture_stream_wrapper(watch_fcn, wfcn_args, wfcn_kwargs, handler, queue):
    """
    Wrapper for the stream events function that handles errors and ensures that
    streams that fail are restarted.
    """
    while True:
        Timestamp()
        try:
            _capture_stream(watch_fcn, wfcn_args, wfcn_kwargs, handler, queue)
        except Exception as e:
            thread_name = threading.current_thread().name
            LOGGER.error(
                'Capture stream {} encountered an exception: {}'.format(thread_name, e),
                exc_info=True
            )
        # Short sleep to prevent rapid retries causing other problems.
        time.sleep(1)


def _capture_stream(watch_fcn, wfcn_args, wfcn_kwargs, handler, queue):
    """
    Generic function to stream events from the Kubernetes API and place
    them into the processing queue

    This also handles error events, logging them and potentially restarting the stream.
    Some errors reoccur if the stream is restarted, and others reoccur if we continue watching.
    At this time there is no clear pattern to these errors, so rather than following a set of
    rules, randomly choosing between the two options guarantees we will break out of any error loops
    eventually.  Leans towards not restarting, as restarting is more impactful.
    """
    w = watch.Watch()
    stream = w.stream(watch_fcn, *wfcn_args, **wfcn_kwargs)
    thread_name = threading.current_thread().name
    for event in stream:
        Timestamp()
        LOGGER.debug('Capture stream: {} received an event: {}'.format(thread_name, event))
        if event['type'] == "ERROR":
            LOGGER.warning('Capture stream: {} encountered an error event'.format(thread_name))
            # Randomize choice to ensure we break out of error loops regardless of error.
            if random.random() < .05:
                LOGGER.warning('Raising an exception for the error event')
                raise RuntimeError(event)
            continue
        queue.put((handler, event))


def wait_for_networking_setup():
    # This is an arbitrary kubernetes call to test connectivity
    while True:
        try:
            k8sjobs.get_api_resources()
        except MaxRetryError:
            LOGGER.info('Waiting for pod networking to complete setup')
            time.sleep(1)
            continue
        LOGGER.info('Networking is available.  Continuing with startup')
        return


def monotonic_liveliness_heartbeat():
    """
    Periodically add a timestamp to disk; this allows for reporting of basic
    health at a minimum rate. This prevents the pod being marked as dead if
    a period of no events have been monitored from k8s for an extended
    period of time.
    """
    while True:
        Timestamp()
        time.sleep(10)


def main(resource_namespace, cfs_env):
    """ Spawn watch processes of relevant Kubernetes objects """

    wait_for_networking_setup()

    # Start a process to handle events placed in the event queue
    event_queue = queue.Queue()

    # Watch ConfigFrameworkSession Custom Resource (v1) events
    cfsv1_informer = threading.Thread(
        target=_capture_stream_wrapper,
        args=(
            k8scrds.list_namespaced_custom_object,
            (RESOURCE_GROUP, v1_RESOURCE_VERSION, resource_namespace, RESOURCE_PLURAL),
            {},
            CFSV1Controller(cfs_env).handle_event,
            event_queue
        ),
        name="cfsv1_informer",
    )
    cfsv1_informer.start()

    # Watch Kubernetes Job events with the CFS label
    cfsv1_job_informer = threading.Thread(
        target=_capture_stream_wrapper,
        args=(
            k8sjobs.list_namespaced_job,
            (resource_namespace,),
            {'label_selector': 'app.kubernetes.io/name=cray-cfs-aee'},
            CFSJobV1Controller(cfs_env).handle_event,
            event_queue
        ),
        name="cfsv1_job_informer",
    )
    cfsv1_job_informer.start()

    # Periodically checks for and fixes out of sync sessions
    session_reconciliation = threading.Thread(
        target=Reconciler().run,
        args=(),
        name="cfs_session_reconciliation",
    )
    session_reconciliation.start()

    # Always periodically heartbeat, even when there isn't work to be
    # done.
    heartbeat = threading.Thread(target=monotonic_liveliness_heartbeat,
                                 args=())
    heartbeat.start()

    # Process events from the queue; kill everything if errors show up
    try:
        while True:
            Timestamp()
            try:
                handler, event = event_queue.get(True, 30)
            except queue.Empty:
                LOGGER.debug('No events on event_queue')
                continue
            LOGGER.debug('Pulling event from event_queue: {}'.format(event))
            handler(event)

    except Exception as err:
        LOGGER.error(
            "Unhandled exception occurred while processing event queue: %s", err,
            exc_info=True
        )
        raise

    except KeyboardInterrupt:
        LOGGER.warning("Exiting event queue processing per user input.")


if __name__ == '__main__':

    # CFS Environment Variables
    CFS_ENVIRONMENT = {k: v for k, v in os.environ.items() if 'CFS' in k}

    # Initialize our watch timestamp
    Timestamp()

    # Format logs for stdout
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = CFS_ENVIRONMENT.get('CFS_OPERATOR_LOG_LEVEL', 'INFO')
    log_level = logging.getLevelName(requested_log_level)

    bad_log_level = None
    if type(log_level) != int:
        bad_log_level = requested_log_level
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format=log_format)

    if bad_log_level:
        LOGGER.warning('Log level %r is not valid. Falling back to INFO', bad_log_level)

    # Ensure the namespace is in the environment
    resource_namespace = CFS_ENVIRONMENT.get('CRAY_CFS_NAMESPACE', 'services')
    CFS_ENVIRONMENT['RESOURCE_NAMESPACE'] = resource_namespace

    version = get_distribution('cray-cfs').version
    LOGGER.info(
        'Starting CFS Operator version=%s, namespace=%s', version, resource_namespace
    )

    for k, v in CFS_ENVIRONMENT.items():
        LOGGER.info('CFS Operator runtime environment: %s=%s', k, v)

    # CASMCMS-4396: Adds support for debugging a running operator
    # Imported here so that the logging has already been initialized
    import cray.cfs.operator.debugging  # noqa: F401

    # Watch events and handle them
    main(resource_namespace, CFS_ENVIRONMENT)
