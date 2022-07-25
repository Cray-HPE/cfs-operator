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
cray.cfs.inventory.dynamic - Generate an inventory from HSM data.
"""
import logging
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from collections import defaultdict

from cray.cfs.inventory import CFSInventoryBase

LOGGER = logging.getLogger(__name__)


class DynamicInventory(CFSInventoryBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME TODO CASMCMS-2777
        self.hsm_host = os.getenv('CRAY_SMD_SERVICE_HOST', 'cray-smd')
        self.ca_cert = os.getenv('SSL_CAINFO')
        LOGGER.debug('API Gateway is: %s', self.hsm_host)
        LOGGER.debug('CA Cert location is: %s', self.ca_cert)
        self._init_session()

    def generate(self):
        """
        Generate from HSM.
        """
        groups = self._get_groups()
        groups.update(self._get_partitions())
        groups.update(self._get_components())
        LOGGER.info('Dynamic inventory found a total of %d groups', len(groups))
        LOGGER.debug('Dynamic inventory found the following groups: %s', ','.join(groups.keys()))

        inventory = {
            'all': {
                'children': groups
            }
        }
        return inventory

    def _init_session(self, retries=10, connect=10, backoff_factor=0.5,
                      status_forcelist=(500, 502, 503, 504)):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http', adapter)

    def _get_groups(self):
        inventory = {}
        try:
            data = self._get_data('groups')
            for group in data:
                members = group['members']['ids']
                hosts = {}
                hosts['hosts'] = {str(member): {} for member in members}
                inventory[str(group['label'])] = hosts
            return inventory
        except Exception as e:
            LOGGER.error('Encountered an unknown exception getting groups data: {}'.format(e))
        return inventory

    def _get_partitions(self):
        inventory = {}
        try:
            data = self._get_data('partitions')
            for group in data:
                members = group['members']['ids']
                hosts = {}
                hosts['hosts'] = {str(member): {} for member in members}
                inventory[str(group['name'])] = hosts
            return inventory
        except Exception as e:
            LOGGER.error('Encountered an unknown exception getting partitions data: {}'.format(e))
        return inventory

    def _get_components(self):
        try:
            hosts = defaultdict(dict)
            data = self._get_data('State/Components?type=node')
            for component in data['Components']:
                role = ''
                if 'Role' in component:
                    role = str(component['Role'])
                    hosts[role][str(component['ID'])] = {}
                if 'SubRole' in component:
                    subrole = str(component['SubRole'])
                    hosts[role + '_' + subrole][str(component['ID'])] = {}
            return {group: {'hosts': host} for group, host in hosts.items()}
        except Exception as e:
            LOGGER.error('Encountered an unknown exception getting component data: {}'.format(e))
        return {}

    def _get_data(self, endpoint):
        url = 'http://{}/hsm/v2/{}'.format(self.hsm_host, endpoint)
        LOGGER.debug('Querying %s for inventory data.', url)
        r = self.session.get(url, verify=self.ca_cert)
        r.raise_for_status()
        return r.json()
