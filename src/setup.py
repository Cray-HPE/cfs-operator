# setup.py for cray-cfs-operator
# Copyright 2019-2020 Hewlett Packard Enterprise Development LP
from setuptools import setup, find_namespace_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="cray-cfs",
    version="1.0.0",
    author="Cray Inc.",
    author_email="sps@cray.com",
    description="Cray Configuration Framework Service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://stash.us.cray.com/projects/SCMS/repos/cfs-operator/browse",
    packages=find_namespace_packages(
        include=(
            'cray.cfs.inventory',
            'cray.cfs.inventory.image',
            'cray.cfs.logging',
            'cray.cfs.operator',
            'cray.cfs.operator.cfs',
            'cray.cfs.operator.liveness',
            'cray.cfs.operator.events',
            'cray.cfs.teardown',
            'cray.cfs.utils',
        )
    ),
    keywords="cray kubernetes configuration management",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: Other/Proprietary License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
)
