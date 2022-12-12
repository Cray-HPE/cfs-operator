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
cray.cfs.utils - helper functions for CFS
"""

import json
import logging
import time
from urllib3.exceptions import HTTPError, MaxRetryError

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

LOGGER = logging.getLogger('cray.cfs.utils')


def wait_for_aee_finish(cfs_name, cfs_namespace):  # noqa: C901
    """
    Consults k8s API for status information about our CFS/AEE instance; returns
    its exit code.
    """
    try:
        config.load_incluster_config()
    except ConfigException:  # pragma: no cover
        config.load_kube_config()  # Development
    _api_client = client.ApiClient()
    k8score = client.CoreV1Api(_api_client)

    ansible_status = None
    # Wait for the AEE pod to finish up for this CFS Session
    while not ansible_status:
        # Create a stream of events and changes from k8s
        stream = None
        while not stream:
            try:
                stream = watch.Watch().stream(
                    k8score.list_namespaced_pod,
                    cfs_namespace,
                    label_selector="aee=%s" % cfs_name)
            except (HTTPError, MaxRetryError, ApiException) as e:
                LOGGER.warning("Unable to chat with k8s API to obtain\
                    an event stream: %s" % (e))
                time.sleep(5)
                continue
        LOGGER.info("Obtained an event stream from k8s...")
        # Process all events in the obtained stream; NOTE: we cannot rely on
        # the MODIFIED event types, because the event in the stream may have
        # already passed before we started watching or between stream initialization
        try:
            for event in stream:
                LOGGER.debug("RAW OBJECT: %s", json.dumps(event['raw_object'], indent=2))
                obj = event['object']
                # Check the container status
                # Container status is not guaranteed to exists, so check before iterating.
                if not obj.status.container_statuses:
                    continue
                for cs in obj.status.container_statuses:
                    if cs.name == "ansible":
                        if cs.state.terminated:
                            ansible_status = cs.state.terminated
                            break
                # Status is set, no longer process events
                if ansible_status:
                    break
        except (HTTPError, MaxRetryError, ApiException) as e:
            LOGGER.warning("Failed processing event stream from k8s; "
                           "established event stream terminated: %s" % (e))
            time.sleep(5)
            continue
    return ansible_status.exit_code
