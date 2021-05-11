# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)
import json
import logging

from kafka import KafkaConsumer

from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException

LOGGER = logging.getLogger(__name__)

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8ssvcs = client.CoreV1Api(_api_client)
KAFKA_PORT = '9092'
KAFKA_HEARTBEAT = 1000  # The default of 3000 was not sufficient during testing
KAFKA_TIMEOUT = 20000  # The default was not sufficient during testing


class ConsumerWrapper:
    """A wrapper around a Kafka connection"""

    def __init__(self, topic=None, group_id=None, enable_auto_commit=True):
        svc_obj = k8ssvcs.read_namespaced_service("cray-shared-kafka-kafka-bootstrap", "services")
        kafka_host = svc_obj.spec.cluster_ip
        self.topic = topic
        self.consumer = KafkaConsumer(topic, group_id=group_id,
                                      bootstrap_servers=[kafka_host+':'+KAFKA_PORT],
                                      enable_auto_commit=enable_auto_commit,
                                      heartbeat_interval_ms=KAFKA_HEARTBEAT,
                                      session_timeout_ms=KAFKA_TIMEOUT,
                                      value_deserializer=lambda m: json.loads(m.decode('utf-8')))
