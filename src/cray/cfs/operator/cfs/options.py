# Copyright 2020 Hewlett Packard Enterprise Development LP

import logging
import json
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from . import requests_retry_session
from . import ENDPOINT as BASE_ENDPOINT

LOGGER = logging.getLogger(__name__)
ENDPOINT = "%s/%s" % (BASE_ENDPOINT, __name__.lower().split('.')[-1])

DEFAULTS = {
    'sessionTTL': '7d',
    'additionalInventoryUrl': ''
}


class Options:
    """
    Handler for reading configuration options from the CFS api

    This caches the options so that frequent use of these options do not all
    result in network calls.
    """
    def __init__(self):
        self.options = DEFAULTS

    def update(self):
        """Refreshes the cached options data"""
        options = self._read_options()
        self.options.update(options)
        patch = {}
        lower_options = [key.lower() for key in options.keys()]
        for key, value in DEFAULTS.items():
            if key.lower() not in lower_options:
                LOGGER.info("Setting option {} to {}.".format(key, str(value)))
                patch[key] = value
        if patch:
            self._patch_options(patch)

    def _read_options(self):
        """Retrieves the current options from the CFS api"""
        session = requests_retry_session()
        try:
            response = session.get(ENDPOINT)
            response.raise_for_status()
            return json.loads(response.text)
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to CFS: {}".format(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from CFS: {}".format(e))
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from CFS: {}".format(e))
        return {}

    def _patch_options(self, obj):
        """Add missing options to the CFS api"""
        session = requests_retry_session()
        try:
            response = session.patch(ENDPOINT, json=obj)
            response.raise_for_status()
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to CFS: {}".format(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from CFS: {}".format(e))

    def get_option(self, key, type):
        return type(self.options[key])

    @property
    def session_ttl(self):
        return self.get_option('sessionTTL', str)

    @property
    def default_playbook(self):
        return self.get_option('defaultPlaybook', str)

    @property
    def default_ansible_config(self):
        return self.get_option('defaultAnsibleConfig', str)

    @property
    def additional_inventory_url(self):
        return self.get_option('additionalInventoryUrl', str)


options = Options()
