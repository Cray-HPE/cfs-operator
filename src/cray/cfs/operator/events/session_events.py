# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
"""
Functions for handling CFS Session Events
"""
import json
import logging
import os
import threading
import uuid


from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

import cray.cfs.operator.cfs.sessions as cfs_sessions
from cray.cfs.operator.cfs.options import options
from cray.cfs.operator.cfs.configurations import get_configuration
from cray.cfs.operator.events.job_events import CFSJobMonitor
from cray.cfs.operator.kafka_utils import ConsumerWrapper

LOGGER = logging.getLogger('cray.cfs.operator.events.session_events')
DEFAULT_ANSIBLE_CONFIG = 'cfs-default-ansible-cfg'
DEFAULT_ANSIBLE_VERBOSITY = 0
SHARED_DIRECTORY = '/inventory'
VCS_USER_CREDENTIALS_DIR = '/etc/cray/vcs'

try:
    config.load_incluster_config()
except ConfigException:  # pragma: no cover
    config.load_kube_config()  # Development

_api_client = client.ApiClient()
k8sjobs = client.BatchV1Api(_api_client)

# Boilerplate code to wait for the envoy sidecar to open connections to the
# mesh. Calls within pods prior to this completing will fail with connection
# refused errors.
wait_for_envoy_boilerplate = 'until curl --head localhost:15000; ' \
                             'do echo Waiting for Sidecar; ' \
                             'sleep 3; ' \
                             'done; ' \
                             'echo Sidecar available'

# Boilerplate code to copy the certs created by cfs-trust/vault for use with live nodes
bootstrap_cfs_keys_boilerplate = 'mkdir -p /root/.ssh && ' \
                                 'until [ -f {0}/ssh/id_ecdsa ]; do sleep 1; done; ' \
                                 'cp -a {0}/ssh/* /root/.ssh/ && ' \
                                 'chmod 600 /root/.ssh/id_ecdsa && ' \
                                 'echo CFS trust keys migrated to /root/.ssh'.format(
                                     SHARED_DIRECTORY)

# Boilerplate code to copy the certs created by cfs-trust/vault for use with image customization
bootstrap_cfs_keys_boilerplate_image = 'mkdir -p /root/.ssh && ' \
                                       'until [ -f {0}/ssh/id_ecdsa ]; do sleep 1; done; ' \
                                       'until [ -f {0}/ssh/id_image ]; do sleep 1; done; ' \
                                       'cp -a {0}/ssh/* /root/.ssh/ && ' \
                                       'chmod 600 /root/.ssh/id_ecdsa && ' \
                                       'chmod 600 /root/.ssh/id_image && ' \
                                       'echo CFS trust keys migrated to /root/.ssh'.format(
                                           SHARED_DIRECTORY)


class CFSSessionController:
    def __init__(self, env):
        self.env = env
        self.job_monitor = CFSJobMonitor(env)

    def run(self):  # pragma: no cover
        self.job_monitor.run()
        threading.Thread(target=self._run).start()

    def _run(self):  # pragma: no cover
        kafka = ConsumerWrapper('cfs-session-events',
                                group_id='cfs-operator',
                                enable_auto_commit=False)
        while True:
            try:
                for event in kafka.consumer:
                    self._handle_event(event.value, kafka)
            except Exception as e:
                LOGGER.warning('Exception handling kafka event: {}'.format(e))

    def _handle_event(self, event, kafka):
        try:
            event_type = event.get('type')
            event_data = event.get('data')
            session_name = event_data.get('name')
            LOGGER.info("EVENT: %s %s", event_type, session_name)
            LOGGER.debug("RAW OBJECT: %s %s", session_name, json.dumps(event_data, indent=2))

            if event_type == 'CREATE':
                self._handle_added(event_data)
            elif event_type == 'DELETE':
                self._handle_deleted(event_data)
            else:
                LOGGER.warning('Invalid event type detected: {}'.format(event))
            kafka.consumer.commit()
        except Exception as e:
            LOGGER.error("EVENT: Exception while handling cfs-operator event: {}".format(e))

    def _handle_added(self, event_data):
        job_id = 'cfs-' + str(uuid.uuid4())
        session_data = cfs_sessions.update_session_status(event_data['name'], {'job': job_id})
        self._create_k8s_job(session_data, job_id)
        self.job_monitor.add_session(session_data)
        return

    def _handle_deleted(self, event_data):
        """ Delete any K8S objects associated with the CFS Session """
        session_name = event_data['name']
        job_id = event_data.get('status', {}).get('session', {}).get('job')
        if job_id:
            self._delete_job(session_name, job_id)

    def _delete_job(self, session_name, job_id):
        """ Delete the Job """
        try:
            resp = k8sjobs.delete_namespaced_job(
                job_id, self.env['RESOURCE_NAMESPACE'], propagation_policy='Background'
            )
            LOGGER.info("Job deleted for CFS Session=%s", session_name)
            LOGGER.debug(
                'Job "%s" deletion response: %s', job_id, json.dumps(resp.to_dict(), indent=2)
            )
        except ApiException as err:
            if err.status == 404:
                LOGGER.warning("Job not deleted; not found for CFS Session=%s", session_name)
                LOGGER.debug('Job "%s" deletion response: %s', job_id, err)
            else:
                LOGGER.warning("Exception calling BatchV1Api->delete_namespaced_job", exc_info=True)

    def _set_environment_variables(self, session_data):
        """
        Set environment variables used in the session job
        """
        self._job_env = {}
        self._job_env['GIT_SSL_CAINFO'] = client.V1EnvVar(
            name='GIT_SSL_CAINFO',
            value='/etc/cray/ca/certificate_authority.crt'
        )
        self._job_env['CFS_OPERATOR_LOG_LEVEL'] = client.V1EnvVar(
            name='CFS_OPERATOR_LOG_LEVEL',
            value=self.env['CFS_OPERATOR_LOG_LEVEL']
        )
        self._job_env['SESSION_NAME'] = client.V1EnvVar(
            name='SESSION_NAME',
            value=session_data['name']
        )
        self._job_env['RESOURCE_NAMESPACE'] = client.V1EnvVar(
            name='RESOURCE_NAMESPACE',
            value=self.env['RESOURCE_NAMESPACE']
        )
        self._job_env['SSL_CAINFO'] = client.V1EnvVar(
            name='SSL_CAINFO',
            value='/etc/cray/ca/certificate_authority.crt'
        )
        self._job_env['VCS_USER'] = client.V1EnvVar(
            name='VCS_USER',
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    key='vcs_username',
                    name=self.env.get('VCS_USER_CREDENTIALS', 'vcs-user-credentials'),
                    optional=False
                )
            )
        )
        self._job_env['VCS_PASSWORD'] = client.V1EnvVar(
            name='VCS_PASSWORD',
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    key='vcs_password',
                    name=self.env.get('VCS_USER_CREDENTIALS', 'vcs-user-credentials'),
                    optional=False
                )
            )
        )

    def _set_volume_mounts(self):
        """
        Set volume mount objects used by various containers in the session job
        """
        self._job_volume_mounts = {}
        self._job_volume_mounts['CONFIG_VOL'] = client.V1VolumeMount(
            name='config-vol',
            mount_path=SHARED_DIRECTORY,
        )
        self._job_volume_mounts['CA_PUBKEY'] = client.V1VolumeMount(
            name='ca-pubkey',
            mount_path='/etc/cray/ca',
            read_only=True,
        )
        self._job_volume_mounts['ANSIBLE_CONFIG'] = client.V1VolumeMount(
            name='ansible-config',
            mount_path='/tmp/ansible',
        )
        self._job_volume_mounts['CFS_TRUST_KEYS'] = client.V1VolumeMount(
            name='cfs-trust-keys',
            mount_path='/secret-keys',
            read_only=True,
        )
        self._job_volume_mounts['CFS_TRUST_CERTIFICATE'] = client.V1VolumeMount(
            name='cfs-trust-certificate',
            mount_path='/secret-certs',
            read_only=True,
        )

    def _set_volumes(self, ansible_config):
        """ Set volume objects used in the session job """
        self._job_volumes = {}
        self._job_volumes['CA_PUBKEY'] = client.V1Volume(
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
        )  # V1Volume

        self._job_volumes['CONFIG_VOL'] = client.V1Volume(
            name='config-vol',
            empty_dir=client.V1EmptyDirVolumeSource(
                medium="Memory"
            )  # V1EmptyDirVolumeSource
        )  # V1Volume

        self._job_volumes['ANSIBLE_CONFIG'] = client.V1Volume(
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
        )  # V1Volume

        self._job_volumes['CFS_TRUST_KEYS'] = client.V1Volume(
            name='cfs-trust-keys',
            secret=client.V1SecretVolumeSource(
                secret_name=self.env['CRAY_CFS_TRUST_KEY_SECRET'],
                items=[
                    client.V1KeyToPath(
                        key='public',
                        path='id_ecdsa.pub'
                    ),  # V1KeyToPath
                    client.V1KeyToPath(
                        key='private',
                        path='id_ecdsa'
                    ),  # V1KeyToPath
                ],  # items
            ),  # V1SecretVolumeSource
        )  # V1Volume

        self._job_volumes['CFS_TRUST_CERTIFICATE'] = client.V1Volume(
            name='cfs-trust-certificate',
            secret=client.V1SecretVolumeSource(
                secret_name=self.env['CRAY_CFS_TRUST_CERT_SECRET'],
                items=[
                    client.V1KeyToPath(
                        key='certificate',
                        path='id_ecdsa-cert.pub'
                    ),  # V1KeyToPath
                ],  # items
            ),  # V1SecretVolumeSource
        )  # V1Volume

    def _get_clone_containers(self, configuration, additional_inventory):
        """
        Create the list of containers to clone repos in the configurations
        for this session.
        """
        clone_containers = []
        repos = [(i, layer['cloneUrl'], layer['commit']) for i, layer in configuration]
        if additional_inventory:
            repos.append(('hosts', additional_inventory['cloneUrl'], additional_inventory['commit']))
        elif options.additional_inventory_url:
            repos.append(('hosts', options.additional_inventory_url, 'master'))
        for i, clone_url, commit in repos:
            directory = SHARED_DIRECTORY + '/layer' + i
            if i == 'hosts':
                directory = SHARED_DIRECTORY + '/hosts'

            git_command = 'mkdir -p {2} && git clone {0} {2} && cd {2} && git checkout {1}'.format(
                clone_url, commit, directory)

            split_url = clone_url.split('/')
            git_credentials_helper = 'git config --global credential.helper store'
            git_credentials_setup = 'echo "{}" > ~/.git-credentials'.format(
                ''.join([split_url[0], '//${VCS_USER}:${VCS_PASSWORD}@', split_url[2]])
            )

            git_retry = 'RETRIES={}; '\
                        'DELAY={}; '\
                        'COUNT=1; '\
                        '{}; '\
                        '{}; '\
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
                            git_credentials_setup,
                            git_credentials_helper,
                            git_command)

            git_clone_container = client.V1Container(
                name='git-clone-' + i,
                image=self.env['CRAY_CFS_UTIL_IMAGE'],
                volume_mounts=[
                    self._job_volume_mounts['CONFIG_VOL'],
                    self._job_volume_mounts['CA_PUBKEY']
                ],  # V1VolumeMount
                env=[self._job_env['GIT_SSL_CAINFO'],
                     self._job_env['VCS_USER'],
                     self._job_env['VCS_PASSWORD']],  # env
                command=["/bin/sh", "-c"],  # command
                args=[git_retry],  # args
            )  # V1Container
            clone_containers.append(git_clone_container)

        return clone_containers

    def _get_inventory_container(self, session_data):
        """
        Create the inventory container object
        """
        create_ssh_dir_cmd = 'mkdir -p {}/ssh '.format(SHARED_DIRECTORY)

        # For live nodes, use the signed keys from vault with a cert generated
        # by the CFS trust mechanisms
        create_ssh_keys_cmd = 'cp /secret-keys/* {0}/ssh/ && ' \
                              'cp /secret-certs/* {0}/ssh/ '.format(SHARED_DIRECTORY)

        boostrap_keys = bootstrap_cfs_keys_boilerplate
        # For image customization, generate some keys for use with Ansible
        if session_data['target']['definition'] == "image":
            create_ssh_keys_cmd += ' && ssh-keygen -t ecdsa -N "" -f {}/ssh/id_image '.format(
                SHARED_DIRECTORY)
            boostrap_keys = bootstrap_cfs_keys_boilerplate_image

        copy_ansible_cfg_cmd = 'cp /tmp/ansible/ansible.cfg {}/ '.format(SHARED_DIRECTORY)
        run_inventory_cmd = 'python3 -m cray.cfs.inventory'
        command = [
            create_ssh_dir_cmd + ' && ' +
            create_ssh_keys_cmd + ' && ' +
            boostrap_keys + ' && ' +
            copy_ansible_cfg_cmd + ' && ' +
            wait_for_envoy_boilerplate + ' && ' +
            run_inventory_cmd
        ]

        return client.V1Container(
            name='inventory',
            image=self.env['CRAY_CFS_IMS_IMAGE'],
            volume_mounts=[
                self._job_volume_mounts['CONFIG_VOL'],
                self._job_volume_mounts['ANSIBLE_CONFIG'],
                self._job_volume_mounts['CA_PUBKEY'],
                self._job_volume_mounts['CFS_TRUST_KEYS'],
                self._job_volume_mounts['CFS_TRUST_CERTIFICATE']
            ],  # V1VolumeMount
            env=[
                self._job_env['CFS_OPERATOR_LOG_LEVEL'],
                self._job_env['SESSION_NAME'],
                self._job_env['RESOURCE_NAMESPACE'],
                self._job_env['SSL_CAINFO']
            ],  # env
            command=['/bin/bash', '-c'],
            args=command,
        )  # V1Container

    def _get_ansible_containers(self, session_data, configuration):
        """
        Get the list of Ansible containers to be run in the job
        """
        options.update()
        ansible_containers = []
        ansible_config = options.default_ansible_config
        ansible_args = []
        if 'ansible' in session_data:
            ansible_spec = session_data['ansible']
            ansible_config = ansible_spec.get('config', ansible_config)

            # This creates a flag equal the the specified number of v's.
            # e.g if ansible_vint = 3, ansible_verbosity="-vvv"
            # The range of values is validated in the api spec.
            ansible_vint = ansible_spec.get('verbosity', DEFAULT_ANSIBLE_VERBOSITY)
            ansible_verbosity = '-' + 'v' * ansible_vint if ansible_vint else None
            if ansible_verbosity:
                ansible_args.append(ansible_verbosity)

            limit = ansible_spec.get('limit', None)
            if limit:
                ansible_args.append('--limit')
                ansible_args.append(limit)

        previous = ''
        for i, layer in configuration:
            playbook = layer.get('playbook', '')
            if not playbook:
                playbook = options.default_playbook

            layer_path = os.path.join('/etc/ansible/', 'layer' + i)
            roles_path = os.path.join(layer_path, 'roles')
            playbook_path = os.path.join(layer_path, playbook)
            ansible_command = ['ansible-playbook', playbook_path] + ansible_args

            ansible_execution_environment_container = client.V1Container(
                name='ansible-' + str(i),
                image=self.env['CRAY_CFS_AEE_IMAGE'],
                resources=client.V1ResourceRequirements(
                    limits={'memory': '6Gi', 'cpu': '8'},
                    requests={'memory': '4Gi', 'cpu': '500m'}
                ),
                env=[
                    self._job_env['SESSION_NAME'],
                    client.V1EnvVar(
                        name='SESSION_CLONE_URL',
                        value=layer['cloneUrl']
                    ),
                    client.V1EnvVar(
                        name='SESSION_PLAYBOOK',
                        value=playbook
                    ),
                    client.V1EnvVar(
                        name='LAYER_CURRENT',
                        value=i
                    ),
                    client.V1EnvVar(
                        name='LAYER_PREVIOUS',
                        value=previous
                    ),
                    client.V1EnvVar(
                        name='ANSIBLE_ROLES_PATH',
                        value=roles_path
                    )
                ],  # env
                volume_mounts=[
                    self._job_volume_mounts['CONFIG_VOL'],
                ],  # volume_mounts
                args=ansible_command,
            )  # V1Container
            ansible_containers.append(ansible_execution_environment_container)
            previous = i

        return ansible_containers

    def _get_teardown_container(self, session_data, configuration):
        """
        For image customization runs (session.target = 'image'), create a
        teardown container to wrap the IMS image back up and put a bow on it.
        """
        teardown_args = [
            bootstrap_cfs_keys_boilerplate + ' && ' +
            wait_for_envoy_boilerplate + ' && ' +
            ' python3 -m cray.cfs.teardown'
        ]

        return client.V1Container(
            name='teardown',
            image=self.env['CRAY_CFS_IMS_IMAGE'],
            volume_mounts=[
                self._job_volume_mounts['CONFIG_VOL'],
            ],  # V1VolumeMount
            env=[
                self._job_env['CFS_OPERATOR_LOG_LEVEL'],
                self._job_env['SESSION_NAME'],
                self._job_env['RESOURCE_NAMESPACE'],
                client.V1EnvVar(
                    name='LAYER_PREVIOUS',
                    value=configuration[-1][0]
                )
            ],  # env
            command=['/bin/bash', '-c'],
            args=teardown_args,
        )  # V1Container

    def _create_k8s_job(self, session_data, job_id):  # noqa: C901
        """
        When a CFS Session is created, kick off the k8s job.
        """
        options.update()
        if 'configuration' in session_data:
            configuration_name = session_data['configuration']['name']
            cfs_config = get_configuration(configuration_name)
            configuration = cfs_config.get('layers', [])
            configuration_limit = session_data['configuration'].get('limit', '')
            additional_inventory = cfs_config.get('additional_inventory', {})
        else:  # DEPRECATED v1
            repo_data = session_data['repo']
            configuration = [{'commit': repo_data.get('commit', repo_data.get('branch')),
                              'cloneUrl': repo_data['cloneUrl'],
                              'playbook': session_data['ansible'].get('playbook', 'site.yml')}]
            configuration_limit = ''

        if configuration_limit:
            limits = configuration_limit.split(',')
            if all([x.isdigit() for x in limits]):
                limits = [int(x) for x in limits]
                configuration = [(str(x), configuration[x]) for x in sorted(limits)
                                 if x < len(configuration)]
            else:
                configuration = [(str(i), layer) for i, layer in enumerate(configuration)
                                 if layer.get('name', '') in configuration_limit]
        else:
            configuration = [(str(i), layer) for i, layer in enumerate(configuration)]

        ansible_config = options.default_ansible_config
        if 'ansible' in session_data:
            ansible_spec = session_data['ansible']
            ansible_config = ansible_spec.get('config', ansible_config)

        # Set the env, vol mount, and volume objects used in the session job
        self._set_environment_variables(session_data)
        self._set_volume_mounts()
        self._set_volumes(ansible_config)

        # Git clone containers
        clone_containers = self._get_clone_containers(configuration, additional_inventory)

        # Inventory container
        inventory_container = self._get_inventory_container(session_data)

        # Ansible containers
        ansible_containers = self._get_ansible_containers(session_data, configuration)

        # Assemble the containers, if this is image customization, add the IMS
        # teardown containers to the list
        containers = [inventory_container] + ansible_containers
        if session_data['target']['definition'] == "image":
            containers.append(self._get_teardown_container(session_data, configuration))

        v1_job = client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(
                name=job_id,
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        name=job_id,
                        labels={
                            'cfsession': session_data['name'],
                            'cfsversion': 'v2',
                            'app.kubernetes.io/name': 'cray-cfs-aee',
                            'aee': session_data['name'],
                        },
                    ),  # V1ObjectMeta
                    spec=client.V1PodSpec(
                        service_account_name=self.env['CRAY_CFS_SERVICE_ACCOUNT'],
                        restart_policy="Never",
                        volumes=[
                            self._job_volumes['CA_PUBKEY'],
                            self._job_volumes['CONFIG_VOL'],
                            self._job_volumes['ANSIBLE_CONFIG'],
                            self._job_volumes['CFS_TRUST_KEYS'],
                            self._job_volumes['CFS_TRUST_CERTIFICATE']
                        ],  # volumes
                        init_containers=clone_containers,
                        containers=containers,
                    )  # V1PodSpec
                )  # V1PodTemplateSpec
            )  # V1JobSpec
        )  # V1Job

        try:
            job = k8sjobs.create_namespaced_job(self.env['RESOURCE_NAMESPACE'], v1_job)
            LOGGER.info(
                "Job request created for CFS Session=%s", session_data['name']
            )
            return job
        except ApiException as err:
            LOGGER.error("Unable to create Job=%s: %s", job_id, err)
            # TODO: fixme - transition CFS to error state?
