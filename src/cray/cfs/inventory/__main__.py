#!/usr/bin/env python
# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
"""
CFS Inventory - module to generate inventory from a CFS Session for use with
the Ansible Execution Environment.
"""
import logging
import os
from pkg_resources import get_distribution
import sys

from cray.cfs.inventory import CFSInventoryFactory, CFSInventoryError
from cray.cfs.inventory.image import ImageRootInventory
from cray.cfs.inventory.spec import ExplicitInventory
from cray.cfs.inventory.repo import RepositoryInventory
from cray.cfs.inventory.dynamic import DynamicInventory
from cray.cfs.logging import setup_logging
import cray.cfs.operator.cfs.sessions as cfs_sessions

LOGGER = logging.getLogger('cray.cfs.inventory')
INVENTORY_COMPLETE_FILE = "/inventory/complete"


def mark_completed(exit_code=0):
    """ Actions to take when the inventory generation is complete """
    with open(INVENTORY_COMPLETE_FILE, 'w') as f:
        f.write(str(exit_code))


def main():
    try:
        cfs_name = os.environ['SESSION_NAME']
        cfs_namespace = os.environ['RESOURCE_NAMESPACE']
    except KeyError:
        LOGGER.error(
            "SESSION_NAME and RESOURCE_NAMESPACE must be present as environment variables."
        )
        raise

    version = get_distribution('cray-cfs').version
    LOGGER.info(
        'Starting CFS Inventory version=%s, namespace=%s', version, cfs_namespace
    )

    factory = CFSInventoryFactory()
    factory.register('image', ImageRootInventory)
    factory.register('spec', ExplicitInventory)
    factory.register('repo', RepositoryInventory)
    factory.register('dynamic', DynamicInventory)

    cfs_session = cfs_sessions.get_session(cfs_name)
    inventory_target = cfs_session['target']['definition']
    LOGGER.info("Inventory target=%s for cfsession=%s", inventory_target, cfs_name)

    try:
        inventory_generator = factory.create(inventory_target, cfs_session, namespace=cfs_namespace)
    except ValueError as err:
        LOGGER.error("%s is not a valid inventory target definition.", inventory_target)
        raise CFSInventoryError('Inventory generation failed') from err

    # Catch and log exceptions, but don't fail on them so that the complete
    # file that the Ansible container is waiting for continues rather than
    # blocking the job
    try:
        inventory_generator.write(inventory=inventory_generator.generate())
    except CFSInventoryError as err:
        LOGGER.error(
            "An error occurred while attempting to generate the inventory. "
            "Error: %s", err
        )
        raise
    except Exception as err:
        LOGGER.error("An unknown exception occurred: {}".format(err))
        raise


if __name__ == "__main__":
    setup_logging()
    exit_code = 0
    try:
        exit_code = main()
    except Exception:
        exit_code = 1
    mark_completed(exit_code)
    sys.exit(exit_code)
