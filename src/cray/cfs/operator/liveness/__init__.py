# Copyright 2019-2020, Cray Inc.
import os

WORKING_DIRECTORY = '/var/'
TIMESTAMP_PATH = os.path.join(WORKING_DIRECTORY, 'timestamp')

os.makedirs(WORKING_DIRECTORY, exist_ok=True)
