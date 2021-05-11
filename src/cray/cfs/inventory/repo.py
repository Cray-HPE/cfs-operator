# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)
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
            "Verifying inventory directory %r exists for 'repo' inventory target.",
            self.inventory_dir
        )
        if not os.path.exists(self.inventory_dir):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), self.inventory_dir
            )
