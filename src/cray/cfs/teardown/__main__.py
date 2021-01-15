#!/usr/bin/env python3
# Copyright 2019-2020 Hewlett Packard Enterprise Development LP
"""
Watch the AEE container for an exit status. If this was an image customization
run, then call IMS to teardown the SSH jail environment and capture back the
image artifact that was generated from the image customization, assuming AEE
exited cleanly.

If AEE did not exit cleanly, tear down the jail environment and exit with the
same status as AEE.

This module is only used for image customization.
"""
from datetime import datetime
import json
from json.decoder import JSONDecodeError
import logging
from multiprocessing import Process, Queue
import os
from pkg_resources import get_distribution
import sys
import time
from typing import Mapping, Iterable, Tuple
import warnings

import paramiko
from redis import StrictRedis
import requests
import yaml

from cray.cfs.inventory.image import get_IMS_API
from cray.cfs.logging import setup_logging
import cray.cfs.operator.cfs.sessions as cfs_sessions
from cray.cfs.utils import wait_for_aee_finish_v1, wait_for_aee_finish_v2

LOGGER = logging.getLogger('cray.cfs.teardown')

# Paramiko/Cryptography so noisy
warnings.filterwarnings(action='ignore', module='.*paramiko.*')


def _get_targets_v1(cfs_name: str) -> Tuple[Iterable, Iterable]:
    """ Query Redis to get the images that passed/failed """
    redis_client = StrictRedis(
        host=os.environ['REDIS_IP'],
        port=os.environ['REDIS_PORT'],
        db=0,
        decode_responses=True
    )
    try:
        failed = redis_client.smembers('sessions/%s/failed' % cfs_name)
        success = redis_client.smembers('sessions/%s/success' % cfs_name)
        LOGGER.debug("Failed hosts for ConfigFrameworkSession=%s: %s", cfs_name, failed)
        LOGGER.debug("Successful hosts for ConfigFrameworkSession=%s: %s", cfs_name, success)
        return (failed, success)
    except Exception as err:
        LOGGER.error(
            "Unable to get target status from redis server for "
            "ConfigFrameworkSession=%s. Error: %s", cfs_name, err,
            exc_info=True
        )
        raise


def _get_targets_v2(session_succeeded: bool) -> Tuple[Iterable, Iterable]:
    success = []
    failed = []
    images = _get_image_to_job().keys()
    if session_succeeded:
        success = images
    else:
        failed = images
    return failed, success
    # parse the inventory file and assign success/failed based on previous layer success.


def _get_image_to_job() -> Mapping[str, str]:
    """ Return the mapping of image ids to job ids """
    with open('/inventory/image_to_job.yaml', 'r') as i2j_file:
        image_to_job = yaml.load(i2j_file)
    LOGGER.debug("Fetched image_to_job.yaml: %s", image_to_job)
    return image_to_job


def _finish_the_job(job_id: str, cfs_name: str) -> None:
    """
    Tell IMS to finish the job by touching the /tmp/complete file in the jail.

    An alternative to this would be CASMCMS-2762, where it could be possible to
    ask IMS to close the jail door for us.

    Args:
        job_id: The IMS job ID
        cfs_name: name of the CFS Session

    Returns:
        None
    """
    LOGGER.info("Calling IMS to finish job=%s for cfsession=%s", job_id, cfs_name)
    host, port, session = get_IMS_API()
    resp = session.get("http://{}:{}/jobs/{}".format(host, port, job_id))
    resp.raise_for_status()
    try:
        response = resp.json()
    except JSONDecodeError:
        LOGGER.error("Non-JSON response received from IMS: '%s'", response)
        raise
    for ssh_container in response['ssh_containers']:
        if ssh_container['name'] == cfs_name:
            ssh_host = ssh_container['connection_info']['cluster.local']['host']
            ssh_port = ssh_container['connection_info']['cluster.local']['port']
            key = paramiko.ecdsakey.ECDSAKey.from_private_key_file('/root/.ssh/id_ecdsa')
            pclient = paramiko.SSHClient()
            for x in range(20):
                try:
                    pclient.set_missing_host_key_policy(paramiko.WarningPolicy())
                    LOGGER.info("Remotely touching complete file for %s:%s", ssh_host,
                                str(ssh_port))
                    pclient.connect(
                        ssh_host, port=ssh_port, pkey=key, username='root',
                        password='',
                    )
                    pclient.exec_command('touch /tmp/complete')
                    break
                except Exception as e:
                    LOGGER.error(e)
                finally:
                    pclient.close()
                return


def do_failed(image_id: str, job_id: str, cfs_name: str, queue) -> None:
    """
    Handle the IMS ssh jails that ended up failing Ansible configuration.
    If a failure is encountered, send the failure to the queue for handling
    by the parent process.

    Args:
        image_id: The IMS image id
        job_id: The IMS job ID
        cfs_name: name of the CFS Session
        queue: queue.Queue

    Returns:
        None
    """
    try:
        _finish_the_job(job_id, cfs_name)
    except Exception as err:
        queue.put(
            ('error', image_id, job_id, err)
        )

    queue.put(('complete', image_id, job_id, None))


def do_success(image_id: str, job_id: str, cfs_name: str, cfs_namespace: str, queue) -> None:
    """
    Handle the IMS ssh jails that succeeded in Ansible configuration. Finish the
    IMS job and get the new image id that resulted.

    If a failure is encountered, send the failure to the queue for handling
    by the parent process.

    Args:
        image_id: The IMS image id
        job_id: The IMS job ID
        cfs_name: name of the CFS Session
        cfs_namespace: the namespace that CFS CRDs are a part of
        queue: queue.Queue

    Returns:
        None
    """
    try:
        _finish_the_job(job_id, cfs_name)
    except Exception as err:
        queue.put(
            ('error', image_id, job_id, err)
        )

    # Wait for the resultant image id
    host, port, session = get_IMS_API()
    resultant_image_id = None
    start_time = datetime.now()
    attempt_count = 0
    while True:
        attempt_count += 1
        try:
            resp = session.get("http://{}:{}/jobs/{}".format(host, port, job_id))
            resp.raise_for_status()
        except requests.exceptions.RequestException as reqexception:
            LOGGER.warning("Non-standard response from IMS: %s" % (reqexception))
            quiesce = attempt_count * 2 + 1
            LOGGER.warning("Attempt %s will proceed after %s second quiesce."
                           % (attempt_count, quiesce))
            time.sleep(quiesce)
            continue
        try:
            response = json.loads(resp.text)
        except JSONDecodeError as jde:
            LOGGER.error("Non-JSON response from IMS: '%s'; requerying...", resp.text)
            LOGGER.error(jde)
            queue.put(('error', image_id, job_id, jde))
            break

        LOGGER.info(
            "Waiting for resultant image of job=%s; IMS status=%s; elapsed time=%ss",
            job_id, response['status'], (datetime.now() - start_time).seconds
        )

        if response['status'].lower() == 'error':
            err = RuntimeError(
                "IMS reported an error when packaging artifacts for job=%s."
                "Consult the IMS logs to determine the cause of failure."
                "IMS response: %s", job_id, response
            )
            queue.put(('error', image_id, job_id, err))
            break

        resultant_image_id = response['resultant_image_id']
        if resultant_image_id is not None:
            LOGGER.info(
                "Resultant image=%s from customization of image=%s", image_id, resultant_image_id
            )
            queue.put(('result', image_id, job_id, resultant_image_id))
            break

        time.sleep(5)

    return


def _update_cfs_with_result(cfs_name: str, image_id: str, result_image_id: str) -> None:
    """
    Update the CFS session with the resulting artifacts
    """
    LOGGER.info(
        "Updating cfsession=%s artifacts with image=%s result=%s",
        cfs_name, image_id, result_image_id
    )
    artifacts = [{
        "image_id": image_id,
        "result_id": result_image_id,
        "type": "ims_customized_image"
    }]
    body = {
        "status": {"artifacts": artifacts}
    }
    cfs_sessions.update_session(cfs_name, body)
    return


def main() -> None:  # noqa: C901

    # Two parameters must always be passed in; the name of the invoking CFS,
    # and the namespace it exists within.
    try:
        cfs_name = os.environ['SESSION_NAME']
        cfs_namespace = os.environ['RESOURCE_NAMESPACE']
    except KeyError:
        sys.exit("SESSION_NAME and RESOURCE_NAMESPACE must be present as environment variables.")

    version = get_distribution('cray-cfs').version
    LOGGER.info('Starting CFS IMS Teardown version=%s, namespace=%s', version, cfs_namespace)
    LOGGER.info("Waiting for `ansible` container to finish.")
    if 'LAYER_PREVIOUS' in os.environ:
        v2 = True
        ansible_status = wait_for_aee_finish_v2(os.environ['LAYER_PREVIOUS'])
    else:
        v2 = False
        ansible_status = wait_for_aee_finish_v1(cfs_name, cfs_namespace)
    LOGGER.info("AEE container has exited with code=%s", ansible_status)
    teardown_success = True

    # Check Redis for image status, if the image was customized correctly:
    #  1) call IMS to teardown the jail(s)
    #  2) wait for IMS to report the resulting image id
    #  3) update the CFS Session with the resulting image id
    #
    # If the image was not customized correctly,
    #  1) call IMS to teardown the jail(s)
    # No further actions are taken.
    #
    # After all is said and done, exit with the same status as the
    # Ansible run unless an error occurs during the calls to IMS.

    # Read in the winners and losers from Redis
    if v2:
        failed, success = _get_targets_v2(ansible_status == 0)
    else:
        try:
            failed, success = _get_targets_v1(cfs_name)
        except Exception:
            teardown_success = False
            failed = []
            success = []

    # Read in the images and their associated jobs from the breadcrumb
    image_to_job = _get_image_to_job()

    # Kick off processing tasks for the images ssh jails. Failed and successful
    # hosts/targets are handled separately.
    pq = Queue()
    all_image_ids = list()
    processes = []
    for image_name in failed:
        if image_name not in image_to_job:
            # This can happen if a host other than the image is referenced in
            # the Ansible playbook
            LOGGER.info("image_name %r could not be found in image_to_job", image_name)
            continue
        job_id = image_to_job[image_name]['job_id']
        image_id = image_to_job[image_name]['image_id']
        all_image_ids.append(image_id)
        processes.append(
            Process(
                target=do_failed,
                args=(image_id, job_id, cfs_name, pq)
            )
        )
    for image_name in success:
        if image_name not in image_to_job:
            # This can happen if a host other than the image is referenced in
            # the Ansible playbook
            LOGGER.info("image_name %r could not be found in image_to_job", image_name)
            continue
        job_id = image_to_job[image_name]['job_id']
        image_id = image_to_job[image_name]['image_id']
        all_image_ids.append(image_id)
        processes.append(
            Process(
                target=do_success,
                args=(image_id, job_id, cfs_name, cfs_namespace, pq)
            )
        )

    for p in processes:
        p.start()

    # As the jobs finish or error out, capture the queue messages and
    # report as necessary
    try:
        while all_image_ids:
            LOGGER.debug("all_image_ids=%s", all_image_ids)
            result, image_id, job_id, response = pq.get()
            LOGGER.debug(
                "Received %r event from image=%s job=%s", result, image_id, job_id
            )

            # An error occurred when attempting to complete the job
            if result == 'error':
                teardown_success = False
                LOGGER.error(
                    "Failed to teardown image customization of image=%s"
                    "in job=%s. Error was %r", image_id, job_id, response
                )

            # The job completed, but there was no resultant image because the
            # Ansible run failed.
            elif result == 'complete':
                LOGGER.info(
                    "Completed teardown of image customization after failed Ansible run for "
                    "image=%s, job=%s", image_id, job_id
                )
                pass
            # Update the CFS Session with the resultant image after successful
            # Ansible run and teardown for this image
            else:
                try:
                    _update_cfs_with_result(cfs_name, image_id, response)
                except Exception as err:
                    teardown_success = False
                    LOGGER.error(
                        "Unable to update cfsession=%s with image=%s, result=%s. Error: %s",
                        image_id, response, err
                    )

            all_image_ids.remove(image_id)
            LOGGER.debug(
                "Removing image=%s from processing queue. Remaining: %s",
                image_id, all_image_ids
            )

    except Exception as err:
        teardown_success = False
        LOGGER.error(
            "An unhandled exception has occurred while tearing down "
            "the image customization jobs. Error: %s", err,
            exc_info=True
        )

    finally:
        for p in processes:
            p.terminate()

    # Exit with the same status as the AEE container, or exit 1 if
    # something in the teardown failed.
    if not teardown_success:
        sys.exit(1)
    else:
        sys.exit(ansible_status)


if __name__ == '__main__':
    setup_logging()
    main()
