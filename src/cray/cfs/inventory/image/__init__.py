#
# MIT License
#
# (C) Copyright 2019, 2021-2023 Hewlett Packard Enterprise Development LP
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
cray.cfs.inventory.image - Generate an inventory from the targets specification
in a CFS session object when the target definition is 'image' for the purposes
of image customization.
"""
from datetime import datetime
import json
import logging
from multiprocessing import Queue, Process
import os
import paramiko
from paramiko.ssh_exception import SSHException
import socket
import time
from typing import Tuple, Iterable, Dict
from urllib.parse import ParseResult, urlunparse

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from yaml import safe_dump

from cray.cfs.inventory import CFSInventoryBase, CFSInventoryError
import cray.cfs.operator.cfs.configurations as cfs_configurations

LOGGER = logging.getLogger('cray.cfs.inventory.image')

# Suppress stack traces while waiting for ssh to be available
# Paramiko also raises these errors which we catch and log in a clearer way
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8score = client.CoreV1Api(_api_client)


IMAGE_HOST_GROUP = "cfs_image"


def get_IMS_API() -> Tuple[str, str, requests.Session]:
    """
    Retrieve the IMS service host and port and a resilient/retry session object,
    attempt to contact it
    """
    port = os.environ.get('CRAY_IMS_SERVICE_PORT', 80)
    host = os.environ.get('CRAY_IMS_SERVICE_HOST', 'cray-ims')

    if port is None or host is None:
        raise CFSInventoryError(
            "Unable to determine IMS Host/Port. Ensure that the following"
            "variables are defined: CRAY_IMS_SERVICE_PORT, CRAY_IMS_SERVICE_HOST"
        )

    # Attempt to contact IMS to ensure it is available
    retries = Retry(total=20, backoff_factor=2, status_forcelist=[502, 503, 504])
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=retries))
    ims_url = ParseResult(
        scheme="http", netloc="cray-ims:80", path="images",
        params=None, query=None, fragment=None
    )
    resp = session.get(urlunparse(ims_url))
    if resp.ok:
        return host, port, session
    else:
        raise CFSInventoryError(
            "Unable to talk with IMS to gather inventory data. Tried url=%s" % urlunparse(ims_url)
        )


class ImageRootInventory(CFSInventoryBase):
    """
    CFS Inventory class to generate an inventory from the target groups
    specified as IMS UUIDs in a CFS object.
    """
    image_to_job = {}

    def generate(self):
        images_groups = self.get_members_groups()

        # Request IMS customization SSH containers for each image
        ssh_containers = self._setup_ssh_containers(images_groups)

        # Create an inventory file with the IMS images, their groups, and
        # connection information, leave a breadcrumb of image to job info too.
        inventory = {}
        inventory[IMAGE_HOST_GROUP] = {}
        inventory[IMAGE_HOST_GROUP]['hosts'] = {}
        self.image_to_job = {}
        for group, images in self.get_groups_members().items():
            inventory[group] = {}
            inventory[group]['hosts'] = {}
            for image in images:
                job_id, image_name, host, port = ssh_containers[image]
                self.image_to_job[image_name] = {
                    'job_id': job_id,
                    'image_id': image,
                }
                inventory[group]['hosts'][image] = {}
                inventory[IMAGE_HOST_GROUP]['hosts'][image] = {
                    'ansible_host': host,
                    'ansible_port': port,
                    'cray_cfs_image': True,
                    'ansible_python_interpreter': '/usr/bin/env python3',
                    'ansible_ssh_private_key_file': '/etc/ansible/ssh/id_image',
                }

        LOGGER.info("Generated image to job mapping=%s ", json.dumps(self.image_to_job, indent=2))
        LOGGER.info("Inventory generated: %s ", json.dumps(inventory, indent=2))
        return inventory

    def write(self, inventory=None):
        # Write out the inventory
        super(ImageRootInventory, self).write(inventory=inventory)

        # Also write out the image_to_job mapping for the teardown phase
        with open('/inventory/image_to_job.yaml', 'w') as i2j_file:
            safe_dump(self.image_to_job, i2j_file, default_flow_style=False, indent=2)

    def _setup_ssh_containers(
            self, image_groups: Dict[str, Iterable]
            ) -> Dict[str, Tuple[str, str, str, int]]:
        """
        Given a mapping of IMS UUIDs as keys, ask IMS to create an SSH container
        for each. Use the public_key to establish passwordless ssh connection to
        the established host.

        Returns a mapping of IMS UUIDs to (job id, image name, host, port) tuples
        used for ssh connections to the created ssh containers.
        """
        key_uuid = ImageRootInventory._upload_public_key(self.cfs_name, self.cfs_namespace)
        ssh_containers = {}
        processes = []
        mpq = Queue()
        require_dkms = configuration_requires_dkms(self.session.get("configuration").get("name"))

        try:
            for ims_id in image_groups.keys():
                LOGGER.info("Requesting access to IMS image=%r", ims_id)
                processes.append(
                    Process(
                        target=ImageRootInventory._request_ims_ssh,
                        args=(mpq, ims_id, self.cfs_name, key_uuid, self.session['target'], require_dkms)
                    )
                )

            for process in processes:
                process.start()

            for process in processes:
                process.join()

            # Process results into dictionary
            launched = set(image_groups)
            completed = set()
            # We have already joined all processes, we can iterate until empty
            while not mpq.empty():
                returned_ims_id, job_id, image_name, host, port = mpq.get()
                LOGGER.info(
                    "Received ssh container result=%s",
                    (returned_ims_id, job_id, image_name, host, port)
                )
                ssh_containers.update({returned_ims_id: (job_id, image_name, host, port)})
                LOGGER.debug("ssh_containers= %s", ssh_containers)
                completed.add(returned_ims_id)

            if completed != launched:
                raise CFSInventoryError('One or more IMS jobs failed to launch.')

            return ssh_containers

        finally:
            # All ssh_containers are setup; revoke public key from IMS
            self._remove_public_key(key_uuid)

    @staticmethod
    def _request_ims_ssh(mpq, ims_id: str, cfs_session: str, public_key_id: str,
                         session_target: dict, require_dkms: bool = False) -> None:
        """ Kick off IMS customization job and request an SSH jailed container """
        host, port, session = get_IMS_API()

        archive_name = ""
        image_map = session_target.get("imageMap") or []
        for mapping in image_map:
            if mapping.get("sourceId", "") == ims_id:
                archive_name = mapping.get("resultName")
                break
        else:
            # Call IMS to get the image name
            LOGGER.debug("Retrieving IMS image name for id=%s", ims_id)
            try:
                resp = session.get("http://{}:{}/images/{}".format(host, port, ims_id))
                resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise CFSInventoryError(
                    'Unable to determine the name of IMS image=%r. Reason: %s' % (ims_id, err)
                ) from err
            archive_name = resp.json()['name'] + "_cfs_" + cfs_session

        # Call IMS to kick off a customization job
        body = {
            "job_type": "customize",
            "image_root_archive_name": archive_name,
            "artifact_id": ims_id,
            "public_key_id": public_key_id,
            "ssh_containers": [
                {
                    "name": cfs_session,
                    "jail": True
                }
            ],
        }
        if require_dkms:
            body["require_dkms"] = True
        LOGGER.debug("Submitting IMS job with parameters: %s", body)
        try:
            resp = requests.post("http://{}:{}/jobs".format(host, port), json=body)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise CFSInventoryError(
                'Unable to create an IMS customization job for IMS image=%r. '
                'Reason: %s. See the IMS logs for more information.' % (ims_id, err)
            )

        # Wait for the SSH container to become available, put the resulting SSH
        # connection information into the processing queue.
        job_id = resp.json()['id']
        mpq.put(ImageRootInventory._wait_for_ssh_container(ims_id, job_id, cfs_session))

    @staticmethod  # noqa: C901
    def _wait_for_ssh_container(  # noqa: C901
            ims_id: str, job_id: str, cfs_session: str, poll: int = 5
            ) -> Tuple[str, str, str, str, str]:
        """
        Poll IMS to determine when the SSH container is ready for use. Return a
        tuple of the (Image ID, job id, image name, host, port).

        Raises CFSInventoryError if anything goes wrong in the process.
        """
        host, port, session = get_IMS_API()
        start_time = datetime.now()
        LOGGER.debug("Retrieving IMS job status for job=%s image=%s", job_id, ims_id)
        while True:
            try:
                resp = session.get("http://{}:{}/jobs/{}".format(host, port, job_id))
                resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise CFSInventoryError(
                    'Unable to get IMS job status for IMS image=%r. Reason: %s', ims_id, err
                )

            response = resp.json()

            # Eureka!
            if response['status'] == 'waiting_on_user':
                for ssh_container in response['ssh_containers']:
                    if ssh_container['name'] == cfs_session:
                        try:
                            host = ssh_container['connection_info']['cluster.local']['host']
                            port = ssh_container['connection_info']['cluster.local']['port']
                        except KeyError as err:
                            raise CFSInventoryError(
                                "Unable to retrieve IMS ssh container connection information. "
                                "Error=%r. SSH Container=%s" % (err, ssh_container)
                            )

                        ImageRootInventory._wait_for_ssh_available(host, port, poll)
                        return (
                            ims_id, job_id, response['image_root_archive_name'], host, port
                        )
                # Not so fast
                else:
                    raise CFSInventoryError(
                        "IMS status=waiting_on_user for IMS image=%r job=%r, but SSH"
                        "container was not created." % (ims_id, job_id)
                    )
            # Ruh roh
            elif response['status'] == 'error':
                raise CFSInventoryError(
                    "IMS status=error for IMS image=%r job=%r, SSH container was not created.",
                    ims_id, job_id
                )

            # What the ?! Success means the job completed, but we haven't done
            # anything yet.
            elif response['status'] == 'success':
                raise CFSInventoryError(
                    "IMS status=success for IMS image=%r job=%r, SSH container was "
                    "not created. Expected 'waiting_on_user' status.",
                    ims_id, job_id
                )

            # Move along, nothing to see here
            else:
                elapsed = (datetime.now() - start_time).seconds
                LOGGER.info(
                    "IMS status=%s for IMS image=%r job=%r. Elapsed time=%ss", response['status'],
                    ims_id, job_id, elapsed
                )

            time.sleep(poll)

    @staticmethod
    def _wait_for_ssh_available(host: str, port: str, poll: int = 5):
        """
        Poll IMS to determine when the SSH container is ready for use.

        Raises CFSInventoryError if anything goes wrong in the process.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        start_time = datetime.now()
        LOGGER.info("Checking ssh availability")
        while True:
            elapsed = (datetime.now() - start_time).seconds
            LOGGER.info(
                "Waiting for SSH to be available at %s:%s. Elapsed time=%ss", host,
                port, elapsed
            )
            time.sleep(2)
            try:
                client.connect(host, port=int(port), password="", timeout=poll)
            except paramiko.AuthenticationException:
                # SSH is up even though we cannot authenticate
                client.close()
                return
            except (socket.timeout, SSHException) as e:
                LOGGER.info("Error while waiting for SSH to be available: {}. Retrying..".format(e))
                continue
            except Exception as e:
                raise CFSInventoryError("Unexpected error connecting to the IMS container", e)

            client.close()
            return

    @staticmethod
    def _upload_public_key(cfs_session: str, namespace: str) -> str:
        """
        Upload the public SSH key to IMS and name it after the CFS session.

        Return: The Key UUID as returned from IMS.
        """
        # Create Public Key
        host, port, session = get_IMS_API()
        with open('/inventory/ssh/id_image.pub', 'r') as key_file:
            key = key_file.read()

        LOGGER.info("Uploading public key to IMS for SSH container access.")
        try:
            resp = session.post(
                "http://{}:{}/public-keys".format(host, port),
                json={'name': 'cfs_' + cfs_session, 'public_key': key},
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise CFSInventoryError('Unable to upload a public key to IMS. Reason: %s' % err)

        return resp.json()['id']

    @staticmethod
    def _remove_public_key(key_uuid: str) -> None:
        """
        Removes a `key_uuid` from IMS (UUID).
        """
        host, port, session = get_IMS_API()
        LOGGER.info("Removing public key from IMS.")
        try:
            resp = session.delete(
                "http://{}:{}/public-keys/{}".format(host, port, key_uuid)
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            LOGGER.warning('Unable to delete a public key to IMS. Reason: %s' % err)


def configuration_requires_dkms(configuration_name):
    try:
        configuration = cfs_configurations.get_configuration(configuration_name)
    except Exception as e:
        LOGGER.error(f"Error loading the CFS configuration to check dkms requirements: {e}")
        return False
    for layer in configuration.get("layers", []):
        if layer.get("specialParameters", {}).get("imsRequireDkms", False):
            return True
    return False
