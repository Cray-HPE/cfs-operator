# Copyright 2019, Cray Inc. All rights reserved.
"""
cray.cfs.inventory.repo - Generate an inventory from a file in the repository
"""
import errno
import logging
import os
import os.path

from cray.cfs.inventory import CFSInventoryBase

LOGGER = logging.getLogger(__name__)


class RepositoryInventory(CFSInventoryBase):
    """
    CFS Inventory class to "generate" an inventory from an existing file in the
    Ansible content repository. This class doesn't really generate an inventory,
    it mostly just checks to make sure an inventory exists as expected.
    """
    def generate(self):
        """
        Since this inventory should already exist, there is nothing to generate.
        """
        return None

    def write(self, **kwargs):
        """
        Since this inventory should already exist, no need to write anything.
        Just check that the file exists.
        """
        LOGGER.info(
            "Verifying inventory file %r exists for 'repo' inventory target.",
            self.inventory_file
        )
        if not os.path.exists(self.inventory_file):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), self.inventory_file
            )
