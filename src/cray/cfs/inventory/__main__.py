#!/usr/bin/env python
# Copyright 2019, Cray Inc. All rights reserved.
"""
CFS Inventory - module to generate inventory from a CFS Session for use with
the Ansible Execution Environment.
"""
import logging
import os
from pkg_resources import get_distribution
import sys

from cray.cfs.k8s import CFSV1K8SConnector
from cray.cfs.inventory import CFSInventoryFactory, CFSInventoryError
from cray.cfs.inventory.image import ImageRootInventory
from cray.cfs.inventory.spec import ExplicitInventory
from cray.cfs.inventory.repo import RepositoryInventory
from cray.cfs.inventory.dynamic import DynamicInventory
from cray.cfs.logging import setup_logging

LOGGER = logging.getLogger('cray.cfs.inventory')


def main():
    try:
        cfs_name = os.environ['SESSION_NAME']
        cfs_namespace = os.environ['RESOURCE_NAMESPACE']
    except KeyError:
        LOGGER.error(
            "SESSION_NAME and RESOURCE_NAMESPACE must be present as environment variables."
        )
        return 1

    version = get_distribution('cray-cfs').version
    LOGGER.info(
        'Starting CFS Inventory version=%s, namespace=%s', version, cfs_namespace
    )

    factory = CFSInventoryFactory()
    factory.register('image', ImageRootInventory)
    factory.register('spec', ExplicitInventory)
    factory.register('repo', RepositoryInventory)
    factory.register('dynamic', DynamicInventory)

    cfs_api = CFSV1K8SConnector(namespace=cfs_namespace)
    cfs_obj = cfs_api.get(cfs_name)
    inventory_target = cfs_obj['spec']['target']['definition']
    LOGGER.info("Inventory target=%s for cfsession=%s", inventory_target, cfs_name)

    try:
        inventory_generator = factory.create(inventory_target, cfs_obj, namespace=cfs_namespace)
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
    except Exception as err:
        LOGGER.error("An unknown exception occurred: {}".format(err))

    inventory_generator.complete()


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
