# Copyright 2019-2020, Cray Inc.
import json
import logging

from redis import Redis

LOGGER = logging.getLogger('cray.cfs.operator.base_controller')


class BaseController(object):
    """ Class interface for handling Kubernetes events """
    def __init__(self, env):
        self.env = env
        self._create_db_client()

    def _create_db_client(self):
        """ Create a redis db client for the controllers to use """
        self.redis_client = Redis(
            host=self.env.get('CRAY_CFS_API_DB_SERVICE_HOST', 'cray-cfs-api-db'),
            port=self.env.get('CRAY_CFS_API_DB_SERVICE_PORT_REDIS', 6379),
            db=0
        )

    def handle_event(self, event):
        try:
            """ Handle a Kubernetes event """
            etype = event['type']

            # The schema for ERROR events in different from ADDED/MODIFIED/DELETED.
            # Handle this event differently that the others
            if etype == "ERROR":
                self._handle_error(event)
                return

            obj = event['raw_object']
            name = obj['metadata']['name']
            obj_type = obj['kind']
            resource_version = obj['metadata']['resourceVersion']
            LOGGER.info("EVENT: %s %s=%s (version=%s)", etype, obj_type, name, resource_version)
            LOGGER.debug("RAW OBJECT: %s=%s %s", obj_type, name, json.dumps(obj, indent=2))

            if etype == 'ADDED':
                self._handle_added(obj, name, obj_type, resource_version, event)
            elif etype == 'MODIFIED':
                self._handle_modified(obj, name, obj_type, resource_version, event)
            elif etype == 'DELETED':
                self._handle_deleted(obj, name, obj_type, resource_version, event)
        except Exception:
            LOGGER.exception("EVENT: Exception while handling cfs-operator event.")

    def _handle_added(self, obj, name, obj_type, resource_version, event):
        pass

    def _handle_modified(self, obj, name, obj_type, resource_version, event):
        pass

    def _handle_deleted(self, obj, name, obj_type, resource_version, event):
        pass

    def _handle_error(self, event):
        # This happens when the CRD changes, nothing we can do but restart
        # as Kubernetes just streams this with vengeance forever.
        LOGGER.error('EVENT: ERROR={}'.format(event))
