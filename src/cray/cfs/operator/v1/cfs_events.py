# Copyright 2019-2020, Cray Inc.
"""
Functions for handling CFS CRD (v1) Events
"""
import json
import logging
import os

from dictdiffer import diff
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

from cray.cfs.k8s import CFSV1K8SConnector
from cray.cfs.operator.controller import BaseController
from cray.cfs.operator.utils import cfs2objectName, k8sObj2name, \
    cfs2sessionId, generateSessionId

LOGGER = logging.getLogger('cray.cfs.operator.v1.cfs_events')
DEFAULT_PLAYBOOK = 'site.yml'
DEFAULT_ANSIBLE_CONFIG = 'cfs-default-ansible-cfg'
DEFAULT_ANSIBLE_VERBOSITY = 0
SHARED_DIRECTORY = '/inventory'

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8sapps = client.AppsV1Api(_api_client)
k8ssvcs = client.CoreV1Api(_api_client)
k8sjobs = client.BatchV1Api(_api_client)
k8snets = client.NetworkingV1Api(_api_client)
k8scrds = client.CustomObjectsApi(_api_client)
cfs_api = CFSV1K8SConnector(retries=10)


class CFSV1Controller(BaseController):
    def _handle_added(self, obj, name, obj_type, resource_version, event):
        # When the controller starts or restarts and CRs exist already, they
        # will be logged with ADDED events. If the CR has a job name in the
        # spec.status.session location, we can skip creating a job for it.
        job_exists = obj['spec'].get('status', {}).get('session', {}).get('job', False)

        # Prime the spec.status and annotations for this new object
        if not job_exists:
            status = obj['spec'].get('status', {})
            body = {
                'metadata': {
                    'labels': {
                        'session-id': generateSessionId(obj)
                    },
                    'annotations': {
                        'cfs-operator.cray.com/last-known-status': json.dumps(status)
                    }
                }
            }
            LOGGER.debug("Updating annotations on ConfigframeworkSession=%s: %s", name, body)
            patched = cfs_api.patch(name, body, namespace=self.env['RESOURCE_NAMESPACE'])
            self._create_k8s_job(patched)
            return

        # In the case that the operator starts watching Kubernetes events when CFS sessions have
        # already been created, Kubernetes sends synthetic "Added" events that represent the current
        # state. If the job was already created, this is the case and we need to handle state
        # reconciliation.
        self._handle_modified(obj, name, obj_type, resource_version, event)

    def _handle_modified(self, obj, name, obj_type, resource_version, event):
        # TODO: Kill any running Jobs associated with it?
        # TODO: is there modification that shouldn't kill running jobs?
        # Status updates shouldn't kill it, but repo url, branch, secrets should
        current_status = obj['spec']['status']
        last_status = json.loads(
            obj['metadata']['annotations']['cfs-operator.cray.com/last-known-status'])

        changes = list(diff(
            last_status,
            current_status
        ))
        for change in changes:
            LOGGER.debug(
                "STATUS: Changed ConfigFrameworkSessions=%s: %s (version=%s)",
                name, change, resource_version
            )
        if changes:
            body = {
                'metadata': {
                    'annotations': {
                        'cfs-operator.cray.com/last-known-status': json.dumps(current_status)
                    }
                }
            }
            cfs_api.patch(name, body, namespace=self.env['RESOURCE_NAMESPACE'])

    def _handle_deleted(self, obj, name, obj_type, resource_version, event):
        """
        Delete any K8S objects associated with the ConfigFrameworkSession Resource
        """
        self._delete_job(obj, name)
        self._delete_redis_status(obj, name)

    def _delete_redis_status(self, obj, name):
        """ Delete the status keys in the redis database for this session """
        try:
            for key in self.redis_client.scan_iter('sessions/%s/*' % name):
                self.redis_client.delete(key)
            LOGGER.info("Redis status deleted for ConfigFrameworkSession=%s", name)
        except:  # noqa: E722
            # Not deleting these keys is mostly harmless
            LOGGER.warning(
                "Exception calling redis_client.delete for ConfigFrameworkSession=%s",
                name, exc_info=True
            )

    def _delete_job(self, obj, name):
        """ Delete the Job """
        try:
            resp = k8sjobs.delete_namespaced_job(
                cfs2objectName(obj), self.env['RESOURCE_NAMESPACE'], propagation_policy='Background'
            )
            LOGGER.info("Job deleted for ConfigFrameworkSession=%s", name)
            LOGGER.debug(
                'Job "%s" deletion response: %s', cfs2objectName(obj),
                json.dumps(resp.to_dict(), indent=2)
            )
        except ApiException as err:
            if err.status == 404:
                LOGGER.warning("Job not deleted; not found for ConfigFrameworkSession=%s", name)
                LOGGER.debug('Job "%s" deletion response: %s', cfs2objectName(obj), err)
            else:
                LOGGER.warning("Exception calling BatchV1Api->delete_namespaced_job", exc_info=True)
                # Kubernetes already deleted the CR, so we just have to let
                # this become an orphan

    def _create_k8s_job(self, cfs_obj):
        """
        When a ConfigFrameworkSession resource is created, kick off the k8s job.
        """
        wait_for_envoy_boilerplate = 'until curl --head localhost:15000; ' \
                                     'do echo Waiting for Sidecar; ' \
                                     'sleep 3; ' \
                                     'done; ' \
                                     'echo Sidecar available;'

        repo_spec = cfs_obj['spec']['repo']
        if repo_spec.get('commit', ''):
            git_command = 'git clone {0} {2} && cd {2} && git checkout {1}'.format(
                repo_spec['cloneUrl'], repo_spec['commit'],
                SHARED_DIRECTORY)
        else:
            git_command = 'git clone {} --branch {} --single-branch {}'.format(
                repo_spec['cloneUrl'], repo_spec['branch'],
                SHARED_DIRECTORY)

        git_retry = 'RETRIES={}; '\
                    'DELAY={}; '\
                    'COUNT=1; '\
                    'while true; do '\
                    '{}; '\
                    'if [ $? -eq 0 ]; then '\
                    'echo "Cloning successful"; '\
                    'exit 0; '\
                    'fi; '\
                    'if [ $COUNT -gt $RETRIES ]; then '\
                    'echo "Cloning exceeded retry limit - Stopping"; '\
                    'exit 1; '\
                    'fi; '\
                    'echo "Cloning failed - Retrying"; '\
                    'let COUNT=$COUNT+1; '\
                    'sleep $DELAY; '\
                    'done'.format(
                        self.env.get('CFS_GIT_RETRY_MAX', 60),
                        self.env.get('CFS_GIT_RETRY_DELAY', 10),
                        git_command)

        git_clone_container = client.V1Container(
            name='git-clone',
            image=self.env['CRAY_CFS_UTIL_IMAGE'],
            volume_mounts=[
                client.V1VolumeMount(
                    name='config-vol',
                    mount_path=SHARED_DIRECTORY,
                ),
                client.V1VolumeMount(
                    name='ca-pubkey',
                    mount_path='/etc/cray/ca',
                    read_only=True,
                ),
            ],  # V1VolumeMount
            env=[
                client.V1EnvVar(
                    name='GIT_SSL_CAINFO',
                    value='/etc/cray/ca/certificate_authority.crt'
                ),
            ],  # env
            command=["/bin/sh", "-c"],  # command
            args=[git_retry],  # args
        )  # V1Container

        copy_ansible_cfg_cmd = "cp /tmp/ansible/ansible.cfg /inventory/;"
        inventory_container = client.V1Container(
            name='inventory',
            image=self.env['CRAY_CFS_IMS_IMAGE'],
            volume_mounts=[
                client.V1VolumeMount(
                    name='config-vol',
                    mount_path=SHARED_DIRECTORY,
                ),
                client.V1VolumeMount(
                    name='ansible-config',
                    mount_path='/tmp/ansible',
                ),
                client.V1VolumeMount(
                    name='ca-pubkey',
                    mount_path='/etc/cray/ca',
                    read_only=True,
                ),
            ],  # V1VolumeMount
            env=[
                client.V1EnvVar(
                    name='CFS_OPERATOR_LOG_LEVEL',
                    value=self.env['CFS_OPERATOR_LOG_LEVEL']
                ),
                client.V1EnvVar(
                    name='SESSION_NAME',
                    value=k8sObj2name(cfs_obj)
                ),
                client.V1EnvVar(
                    name='RESOURCE_NAMESPACE',
                    value=self.env['RESOURCE_NAMESPACE']
                ),
                client.V1EnvVar(
                    name='SSL_CAINFO',
                    value='/etc/cray/ca/certificate_authority.crt'
                ),
            ],  # env
            command=['/bin/bash', '-c'],
            args=[
                wait_for_envoy_boilerplate + \
                copy_ansible_cfg_cmd + \
                ' python3 -m cray.cfs.inventory'
            ],
        )  # V1Container

        playbook = DEFAULT_PLAYBOOK
        ansible_config = DEFAULT_ANSIBLE_CONFIG
        ansible_args = []
        if 'ansible' in cfs_obj['spec']:
            ansible_spec = cfs_obj['spec']['ansible']
            playbook = ansible_spec.get('playbook', playbook)
            ansible_config = ansible_spec.get('config', DEFAULT_ANSIBLE_CONFIG)

            ansible_vint = ansible_spec.get('verbosity', DEFAULT_ANSIBLE_VERBOSITY)
            ansible_verbosity = '-' + 'v' * ansible_vint if ansible_vint else None
            if ansible_verbosity:
                ansible_args.append(ansible_verbosity)

            limit = ansible_spec.get('limit', None)
            if limit:
                ansible_args.append('--limit')
                ansible_args.append(limit)

        if not playbook.startswith('/etc/ansible/'):
            playbook = os.path.join('/etc/ansible/', playbook)
        ansible_command = ['ansible-playbook', playbook, *ansible_args]

        ansible_execution_environment_container = client.V1Container(
            name='ansible',
            image=self.env['CRAY_CFS_AEE_IMAGE'],
            resources=client.V1ResourceRequirements(
                limits={'memory': '6Gi'},
                requests={'memory': '4Gi'}
            ),
            env=[
                client.V1EnvVar(
                    name='SESSION_NAME',
                    value=k8sObj2name(cfs_obj),
                ),
                client.V1EnvVar(
                    name="REDIS_IP",
                    value=self.env['CRAY_CFS_API_DB_SERVICE_HOST']
                ),
                client.V1EnvVar(
                    name="REDIS_PORT",
                    value=self.env['CRAY_CFS_API_DB_SERVICE_PORT_REDIS']
                ),
                client.V1EnvVar(
                    name='SESSION_CLONE_URL',
                    value=cfs_obj['spec']['repo']['cloneUrl']
                ),
                client.V1EnvVar(
                    name='SESSION_PLAYBOOK',
                    value=cfs_obj['spec'].get('ansible', {}).get('playbook', DEFAULT_PLAYBOOK)
                )
            ],  # env
            volume_mounts=[
                client.V1VolumeMount(
                    name='config-vol',
                    mount_path=SHARED_DIRECTORY,
                ),
                client.V1VolumeMount(
                    name='ssh-private-key',
                    mount_path='/secret',
                    read_only=True,
                ),
            ],  # volume_mounts
            args=ansible_command
        )  # V1Container

        teardown_args = [wait_for_envoy_boilerplate + ' python3 -m cray.cfs.teardown']

        ims_teardown_container = client.V1Container(
            name='teardown',
            image=self.env['CRAY_CFS_IMS_IMAGE'],
            volume_mounts=[
                client.V1VolumeMount(
                    name='config-vol',
                    mount_path=SHARED_DIRECTORY,
                ),
                client.V1VolumeMount(
                    name='ssh-private-key',
                    mount_path='/secret',
                    read_only=True,
                ),
            ],  # V1VolumeMount
            env=[
                client.V1EnvVar(
                    name='CFS_OPERATOR_LOG_LEVEL',
                    value=self.env['CFS_OPERATOR_LOG_LEVEL']
                ),
                client.V1EnvVar(
                    name="REDIS_IP",
                    value=self.env['CRAY_CFS_API_DB_SERVICE_HOST']
                ),
                client.V1EnvVar(
                    name="REDIS_PORT",
                    value=self.env['CRAY_CFS_API_DB_SERVICE_PORT_REDIS']
                ),
                client.V1EnvVar(
                    name='SESSION_NAME',
                    value=k8sObj2name(cfs_obj)
                ),
                client.V1EnvVar(
                    name='RESOURCE_NAMESPACE',
                    value=self.env['RESOURCE_NAMESPACE']
                ),
            ],  # env
            command=['/bin/bash', '-c'],
            args=teardown_args,
        )  # V1Container

        init_containers = [git_clone_container, ]
        containers = [inventory_container, ansible_execution_environment_container, ]

        # If this is image customization, add the IMS staging and teardown
        # containers
        if cfs_obj['spec']['target']['definition'] == "image":
            containers.append(ims_teardown_container)

        v1_job = client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(
                name=cfs2objectName(cfs_obj),
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        name=cfs2objectName(cfs_obj),
                        labels={
                            'cfsession': k8sObj2name(cfs_obj),
                            'session-id': cfs2sessionId(cfs_obj),
                            'app.kubernetes.io/name': 'cray-cfs-aee',
                            'aee': k8sObj2name(cfs_obj),
                        },
                    ),  # V1ObjectMeta
                    spec=client.V1PodSpec(
                        service_account_name=self.env['CRAY_CFS_SERVICE_ACCOUNT'],
                        restart_policy="Never",
                        volumes=[
                            client.V1Volume(
                                name='ca-pubkey',
                                config_map=client.V1ConfigMapVolumeSource(
                                    name=self.env['CRAY_CFS_CONFIGMAP_PUBLIC_KEY'],
                                    items=[
                                        client.V1KeyToPath(
                                            key=self.env['CRAY_CFS_CA_PUBLIC_KEY'],
                                            path='certificate_authority.crt'
                                        )  # V1KeyToPath
                                    ],  # items
                                ),  # V1ConfigMapVolumeSource
                            ),  # V1Volume
                            client.V1Volume(
                                name='config-vol',
                                empty_dir=client.V1EmptyDirVolumeSource(
                                    medium="Memory"
                                )  # V1EmptyDirVolumeSource
                            ),  # V1Volume
                            client.V1Volume(
                                name='ansible-config',
                                config_map=client.V1ConfigMapVolumeSource(
                                    name=ansible_config,
                                    items=[
                                        client.V1KeyToPath(
                                            key='ansible.cfg',
                                            path='ansible.cfg'
                                        )  # V1KeyToPath
                                    ],  # items
                                ),  # V1ConfigMapVolumeSource
                            ),  # V1Volume
                            client.V1Volume(
                                name='ssh-private-key',
                                secret=client.V1SecretVolumeSource(
                                    secret_name=self.env['CRAY_CFS_AEE_PRIVATE_KEY'],
                                    default_mode=256,
                                    items=[
                                        client.V1KeyToPath(
                                            key='key',
                                            path='key'
                                        )  # V1KeyToPath
                                    ],  # items
                                ),  # V1SecretVolumeSource
                            )  # V1Volume
                        ],  # volumes
                        init_containers=init_containers,
                        containers=containers,
                    )  # V1PodSpec
                )  # V1PodTemplateSpec
            )  # V1JobSpec
        )  # V1Job

        try:
            job = k8sjobs.create_namespaced_job(self.env['RESOURCE_NAMESPACE'], v1_job)
            LOGGER.info(
                "Job request created for ConfigFrameworkSession=%s", cfs_obj['metadata']['name']
            )
            return job
        except ApiException as err:
            LOGGER.error("Unable to create Job=%s: %s", cfs2objectName(cfs_obj), err)
            # TODO: fixme - transition CFS to error state?
