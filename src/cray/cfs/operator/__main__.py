#!/usr/bin/env python
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
from cray.cfs.logging import setup_logging, update_logging
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
        try:
            options.update()
            update_logging()
            ttl = options.session_ttl
            if ttl:
                sessions.delete_sessions(status='complete', min_age=ttl)
        except Exception as e:
            LOGGER.warning('Exception during session cleanup: {}'.format(e))


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
    setup_logging()
    env = _init_env()
    _wait_for_networking_setup()

    version = get_distribution('cray-cfs').version
    LOGGER.info('Starting CFS Operator version=%s', version)
    main(env)
