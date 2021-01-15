# Copyright 2019, Cray Inc. All rights reserved.
"""
cray.cfs.inventory.spec - Generate an inventory from the targets specification
in a CFS session object.
"""
import logging
import json

from cray.cfs.inventory import CFSInventoryBase

LOGGER = logging.getLogger(__name__)


class ExplicitInventory(CFSInventoryBase):
    """
    CFS Inventory class to generate an inventory from the target groups
    specified in a CFS object.
    """
    def generate(self):
        inventory = self._dict2AnsibleInventory(self.get_groups_members())
        LOGGER.info("Inventory generated: %s ", json.dumps(inventory, indent=2))
        return inventory
