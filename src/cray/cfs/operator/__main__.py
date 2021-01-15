#!/usr/bin/env python
# Copyright 2019-2020 Hewlett Packard Enterprise Development LP
"""
CFS Operator - A Python operator for the Cray Configuration Framework Service.
"""

import logging
import threading
import os
from pkg_resources import get_distribution
import time
from urllib3.exceptions import MaxRetryError

from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException

from .events import CFSSessionController
from cray.cfs.operator.cfs.options import options
import cray.cfs.operator.cfs.sessions as sessions
from cray.cfs.operator.liveness.timestamp import Timestamp


LOGGER = logging.getLogger('cray.cfs.operator')
try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8sjobs = client.BatchV1Api(_api_client)


def session_cleanup():
    """
    Periodically deletes all completed sessions older than the set ttl.
    """
    while True:
        time.sleep(60 * 5)  # Run every 5 minutes
        options.update()
        ttl = options.session_ttl
        if ttl:
            sessions.delete_sessions(status='complete', age=ttl)


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


def main(env):
    """ Spawn watch processes of relevant Kubernetes objects """
    # Periodically checks for and removes sessions older than the TTL
    cleanup = threading.Thread(
        target=session_cleanup,
        args=(),
        name="cfs_session_cleanup",
    )
    cleanup.start()

    # Always periodically heartbeat, even when there isn't work to be
    # done.
    heartbeat = threading.Thread(target=monotonic_liveliness_heartbeat,
                                 args=())
    heartbeat.start()

    controller = CFSSessionController(env)
    controller.run()


def _init_logging():
    # Format logs for stdout
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get('CFS_OPERATOR_LOG_LEVEL', 'INFO')
    log_level = logging.getLevelName(requested_log_level)

    if type(log_level) != int:
        LOGGER.warning('Log level %r is not valid. Falling back to INFO', requested_log_level)
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format=log_format)


def _init_env():
    # CFS Environment Variables
    cfs_environment = {k: v for k, v in os.environ.items() if 'CFS' in k}

    # Ensure the namespace is in the environment
    resource_namespace = cfs_environment.get('CRAY_CFS_NAMESPACE', 'services')
    cfs_environment['RESOURCE_NAMESPACE'] = resource_namespace

    for k, v in cfs_environment.items():
        LOGGER.info('CFS Operator runtime environment: %s=%s', k, v)
    return cfs_environment


def _wait_for_networking_setup():
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


if __name__ == '__main__':
    Timestamp()  # Initialize our watch timestamp
    _init_logging()
    env = _init_env()
    _wait_for_networking_setup()

    version = get_distribution('cray-cfs').version
    LOGGER.info('Starting CFS Operator version=%s', version)
    main(env)
