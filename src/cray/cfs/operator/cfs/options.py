#
# MIT License
#
# (C) Copyright 2020-2026 Hewlett Packard Enterprise Development LP
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
import logging
import threading
import time
from typing import Optional

from csm_utils.logging import exc_type_msg
import ujson as json
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from . import requests_retry_session
from . import ENDPOINT as BASE_ENDPOINT

LOGGER = logging.getLogger(__name__)
ENDPOINT = "%s/%s" % (BASE_ENDPOINT, __name__.lower().split('.')[-1])

DEFAULTS = {
    'session_ttl': '7d',
    'additional_inventory_url': '',
    'additional_inventory_source': '',
    'logging_level': 'INFO',
    'debug_wait_time': 3600
}

# How often (in seconds) to refresh the option values
OPTIONS_UPDATE_INTERVAL = 15


class Options:
    """
    Handler for reading configuration options from the CFS API

    This caches the options so that frequent use of these options do not all
    result in network calls.
    """
    def __init__(self):
        self.options = DEFAULTS
        # Last time CFS was called to update the options
        self._last_update: Optional[float] = None
        # Prevent multiple threads from updating options at the same time
        self._update_lock = threading.Lock()

    def update(self, force: bool=True) -> None:
        """
        If force is true OR if the options have not been updated
        within OPTIONS_UPDATE_INTERVAL, then calls _update() to
        refresh the cached options data
        """
        if not force and not self._update_needed:
            # force option not specified, and we have a recent
            # refresh, so return
            return
        # Take the options update lock
        with self._update_lock:
            # Check again if it's still needed (it's possible
            # another thread updated them in the meantime)
            if not force and not self._update_needed:
                # force option not specified, and we have a recent
                # refresh, so return
                return
            # Update the options
            self._update()

    def _update(self) -> None:
        """Refreshes the cached options data -- assumes lock is held"""
        LOGGER.debug("Refreshing cached options data")
        options = self._read_options()
        self.options.update(options)
        patch = {}
        lower_options = [key.lower() for key in options.keys()]
        for key, value in DEFAULTS.items():
            if key.lower() not in lower_options:
                LOGGER.info("Setting option {} to {}.".format(key, str(value)))
                patch[key] = value
        # Update the last-updated timestamp
        self._last_update = time.time()
        if patch:
            self._patch_options(patch)

    def _read_options(self):
        """Retrieves the current options from the CFS API"""
        session = requests_retry_session()
        try:
            response = session.get(ENDPOINT)
            response.raise_for_status()
            return json.loads(response.text)
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to CFS: %s", exc_type_msg(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from CFS: %s", exc_type_msg(e))
        except json.JSONDecodeError as e:
            LOGGER.error("Non-JSON response from CFS: %s", exc_type_msg(e))
        return {}

    def _patch_options(self, obj):
        """Add missing options to the CFS API"""
        session = requests_retry_session()
        try:
            response = session.patch(ENDPOINT, json=obj)
            response.raise_for_status()
        except (ConnectionError, MaxRetryError) as e:
            LOGGER.error("Unable to connect to CFS: %s", exc_type_msg(e))
        except HTTPError as e:
            LOGGER.error("Unexpected response from CFS: %s", exc_type_msg(e))

    def get_option(self, key, type):
        return type(self.options[key])

    @property
    def _update_needed(self) -> bool:
        if self._last_update is None:
            return True
        return time.time() - self._last_update >= OPTIONS_UPDATE_INTERVAL

    @property
    def session_ttl(self):
        return self.get_option('session_ttl', str)

    @property
    def default_playbook(self):
        return self.get_option('default_playbook', str)

    @property
    def default_ansible_config(self):
        return self.get_option('default_ansible_config', str)

    @property
    def additional_inventory_url(self):
        return self.get_option('additional_inventory_url', str)

    @property
    def additional_inventory_source(self):
        return self.get_option('additional_inventory_source', str)

    @property
    def logging_level(self):
        return self.get_option('logging_level', str)

    @property
    def debug_wait_time(self):
        return self.get_option('debug_wait_time', str)


options = Options()
