# Copyright 2019, Cray Inc. All rights reserved.
"""
cray.cfs.inventory - Base class and factory for generating inventories from a
CFS Session for use with the Ansible Execution Environment.

HT: https://realpython.com/factory-method-python/
"""
from collections import defaultdict
import logging
from pathlib import Path
from typing import Dict, Iterable

from yaml import safe_dump

LOGGER = logging.getLogger(__name__)


class CFSInventoryError(Exception):
    """
    A generic error for CFS inventory generation
    """
    pass


class CFSInventoryFactory(object):
    """
    Factory for classes that generate CFS Inventories
    """
    def __init__(self):
        self._generators = {}

    def register(self, key, generator):
        """ Register a generator with the factory """
        self._generators[key] = generator

    def create(self, key, cfs_obj, **kwargs):
        """ Instantiate and return an inventory generator """
        generator = self._generators.get(key)
        if not generator:
            raise ValueError(key)
        return generator(cfs_obj, **kwargs)


class CFSInventoryBase(object):
    """ Base class for inventory generators """
    inventory_file = "/inventory/hosts"
    inventory_complete_file = "/inventory/complete"

    def __init__(self, cfs_obj, inventory_file=None, namespace=None, inventory_complete_file=None):
        self.inventory_file = inventory_file or self.inventory_file
        self.cfs_obj = cfs_obj
        self.cfs_namespace = namespace
        self.inventory_complete_file = inventory_complete_file or self.inventory_complete_file
        self.cfs_name = self.cfs_obj['metadata']['name']

    def _dict2AnsibleInventory(self, grp_members: Dict[str, Iterable]):
        """
        Convert a dictionary of {'group': [members, ]} to the format that
        Ansible requires for its YAML parser plugin
        """
        inventory = {}
        for group, members in grp_members.items():
            inventory[group] = {}
            inventory[group]['hosts'] = {}
            for member in members:
                inventory[group]['hosts'][member] = {}

        return inventory

    def generate(self):
        """ Generate the inventory and return it """
        pass

    def complete(self):
        """ Actions to take when the inventory generation is complete """
        return Path(self.inventory_complete_file).touch()

    def write(self, inventory=None):
        LOGGER.info("Writing out the inventory to %s", self.inventory_file)
        with open(self.inventory_file, 'w') as inventory_file:
            safe_dump(inventory, inventory_file, default_flow_style=False, indent=2)

    def get_groups_members(self) -> Dict[str, Iterable]:
        """
        Get the CFS object with the groups/membership information.

        Returns a dictionary of group names and a list of host members
        associated with them. Opposite of CFSInventoryBase.get_members_groups.
        """
        groups_members = defaultdict(list)
        for group in self.cfs_obj['spec']['target']['groups']:
            groups_members[group['name']].extend(group['members'])

        LOGGER.debug(
            "Groups/members retrieved from cfsession=%s: %s",
            self.cfs_name, groups_members
        )
        return groups_members

    def get_members_groups(self) -> Dict[str, Iterable]:
        """
        Get the CFS object with the groups/membership information.

        Returns a dictionary of members and a set of groups associated with
        them. Opposite of CFSInventoryBase.get_groups_members.
        """
        members_groups = defaultdict(set)
        for group in self.cfs_obj['spec']['target']['groups']:
            for member in group['members']:
                members_groups[member].add(group['name'])

        LOGGER.debug(
            "Members/Groups retrieved from cfsession=%s: %s",
            self.cfs_name, members_groups
        )
        return members_groups
