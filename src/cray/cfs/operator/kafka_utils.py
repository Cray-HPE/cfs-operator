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
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaTimeoutError

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
KAFKA_SESSION_TIMEOUT = 20000  # The default was not sufficient during testing
KAFKA_PRODUCE_TIMEOUT = 2


class KafkaWrapper:
    """A wrapper around a Kafka connection"""

    def __init__(self, topic=None, group_id=None, enable_auto_commit=True):
        self.topic = topic
        self.kafka_host = None
        self.consumer = None
        self.producer = None
        while not self.kafka_host:
            self._init_kafka_host()
        self._init_consumer(group_id, enable_auto_commit)
        self._init_producer()

    def _init_kafka_host(self):
        svc_obj = k8ssvcs.read_namespaced_service("cray-shared-kafka-kafka-bootstrap",
                                                  "services")
        host = svc_obj.spec.cluster_ip
        self.kafka_host = host+':'+KAFKA_PORT

    def _init_consumer(self, group_id, enable_auto_commit):
        self.consumer = KafkaConsumer(self.topic, group_id=group_id,
                                      bootstrap_servers=[self.kafka_host],
                                      enable_auto_commit=enable_auto_commit,
                                      heartbeat_interval_ms=KAFKA_HEARTBEAT,
                                      session_timeout_ms=KAFKA_SESSION_TIMEOUT,
                                      value_deserializer=lambda m: json.loads(m.decode('utf-8')))

    def _init_producer(self, retry=True):
        if self.producer:
            try:
                self.producer.close(timeout=KAFKA_PRODUCE_TIMEOUT)
            except KafkaTimeoutError as e:
                LOGGER.warning('Unable to close previous Kafka producer: {}'.format(e))
            self.producer = None
        while not self.producer:
            self._init_kafka_host()
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=[self.kafka_host],
                    value_serializer=lambda m: json.dumps(m).encode('utf-8'),
                    retries=5)
            except Exception as e:
                LOGGER.error('Error initializing Kafka producer: {}'.format(e))
                if not retry:
                    return
                time.sleep(5)

    def produce(self, event):
        try:
            self._produce(self.topic, event)
            return
        except KafkaTimeoutError:
            # The networking may have changed, causing writing to hang.
            LOGGER.warning('There was a timeout while writing to Kafka.'
                           'Restarting the kafka producer and retrying...')
            self._init_producer()
            self._produce(self.topic, event)

    def _produce(self, topic, data):
        self.producer.send(topic, data)
        self.producer.flush(timeout=KAFKA_PRODUCE_TIMEOUT)
