#!/usr/bin/env python3
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

# Intended to be called by Git via GIT_ASKPASS.

import os
import sys

from cray.cfs.utils.vault_utils import get_secret as get_vault_secret

def _get_git_credentials():
    secret_name = os.environ.get('SECRET_NAME')
    if not secret_name:
        username = os.environ['VCS_USERNAME'].strip()
        password = os.environ['VCS_PASSWORD'].strip()
        return username, password
    try:
        secret = get_vault_secret(secret_name)
    except Exception as e:
        raise Exception(f"Error loading Vault secret: {e}") from e
    try:
        username = secret["username"]
        password = secret["password"]
    except Exception as e:
        raise Exception(f"Error reading username and password from secret: {e}") from e
    return username, password

def main():
    username, password = _get_git_credentials()
    if 'username' in sys.argv[1].lower():
        print(username)
        exit()
    if 'password' in sys.argv[1].lower():
        print(password)
        exit()
    exit(1)

if __name__ == "__main__":
    main()
