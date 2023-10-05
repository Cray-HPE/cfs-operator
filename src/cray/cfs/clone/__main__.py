#!/usr/bin/env python
#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
CFS Clone - module to clone down git content as part of a CFS Session for use with
the Ansible Execution Environment.
"""
import logging
import os
import sys
import time

import git

from cray.cfs.logging import setup_logging, update_logging
import cray.cfs.operator.cfs.configurations as cfs_configurations
import cray.cfs.operator.cfs.sources as cfs_sources
import cray.cfs.operator.cfs.options as cfs_options
from cray.cfs.utils import apply_configuration_limit
from cray.cfs.utils.kubernetes_utils import get_configmap

LOGGER = logging.getLogger("cray.cfs.clone")

SHARED_DIRECTORY = "/inventory"


def main():
    LOGGER.info("Starting CFS Clone")
    retry_limit=int(os.environ.get("GIT_RETRY_MAX", 60))
    retry_delay=int(os.environ.get("GIT_RETRY_DELAY", 10))

    configuration_name = os.environ["SESSION_CONFIGURATION_NAME"]
    configuration_limit = os.environ["SESSION_CONFIGURATION_LIMIT"]
    try:
        configuration = cfs_configurations.get_configuration(configuration_name)
    except Exception as e:
        if configuration_name.startswith("debug_"):
            # There is nothing to clone for debug playbooks
            return
        raise e

    configuration_layers = configuration.get("layers", [])
    repos = [("layer"+i, layer) for i, layer in apply_configuration_limit(configuration_layers, configuration_limit)]

    additional_inventory = configuration.get("additional_inventory", {})
    if not additional_inventory:
        if cfs_options.options.additional_inventory_source:
            additional_inventory = {"source": cfs_options.options.additional_inventory_source, "commit": ""}
        elif cfs_options.options.additional_inventory_url:
            additional_inventory = {"clone_url": cfs_options.options.additional_inventory_source, "commit": ""}
    if additional_inventory:
        repos.append(("hosts", additional_inventory))

    for repo_dir, repo_info in repos:
        source_name = repo_info.get("source")
        source = None
        if source_name:
            source = cfs_sources.get_source(source_name)
            clone_url = source["clone_url"]
        else:
            clone_url = repo_info["clone_url"]
        commit = repo_info.get("commit")
        clone_repo(clone_url, repo_dir, commit=commit, source=source, retry_limit=retry_limit, retry_delay=retry_delay)

    return 0


def clone_repo(clone_url, repo_directory, commit=None, source=None, retry_limit=1, retry_delay=10):
    try:
        ssl_info = _get_ssl_info(source)
    except Exception as e:
        LOGGER.error(f"Error retrieving git CA cert info: {e}")
        raise

    project_dir = os.path.dirname(os.path.abspath(__file__))
    git_askpass = os.path.join(project_dir, "askpass.py")
    clone_env = {"GIT_ASKPASS": git_askpass, "GIT_SSL_CAINFO": ssl_info}
    if source:
         clone_env["SECRET_NAME"] = source.get("credentials").get("secret_name", "")

    x = 1
    while True:
        try:
            repo = git.Repo.clone_from(clone_url, os.path.join(SHARED_DIRECTORY, repo_directory), env=clone_env)
            LOGGER.info(f"Successfully cloned repo {clone_url}")
            break
        except Exception as e:
            if x == 1:
                LOGGER.warning(e)
            if x < retry_limit:
                LOGGER.info("Cloning failed - Retrying")
                x = x + 1
                time.sleep(retry_delay)
            else:
                LOGGER.error("Cloning exceeded retry limit")
                raise

    if commit:
        try:
            repo.git.checkout(commit)
        except Exception as e:
            LOGGER.error(f"Exception checking out commit {commit} for repo {clone_url}")
            raise
        LOGGER.info(f"Successfully checked out commit {commit} for repo {clone_url}")


def _get_ssl_info(source=None, tmp_dir="/tmp"):
    if source and source.get("ca_cert"):
        cert_info = source.get("ca_cert")
        configmap_name = cert_info["configmap_name"]
        configmap_namespace = cert_info.get("configmap_namespace")
        if configmap_namespace:
            response = get_configmap(configmap_name, configmap_namespace)
        else:
            response = get_configmap(configmap_name)
        data = response.data
        file_name = list(data.keys())[0]
        file_path = os.path.join(tmp_dir, file_name)
        with open(file_path, "w") as f:
            f.write(data[file_name])
        return file_path
    else:
        return os.environ["GIT_SSL_CAINFO"]


if __name__ == "__main__":
    setup_logging()
    update_logging(update_options=True)
    exit_code = 0
    try:
        exit_code = main()
    except Exception as e:
        LOGGER.exception(e)
        exit_code = 1
    sys.exit(exit_code)
