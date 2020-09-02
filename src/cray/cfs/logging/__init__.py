# Copyright 2019, Cray Inc. All Rights Reserved.

"""
cray.cfs.logging - helper functions for logging in CFS
"""
import logging
import os

LOGGER = logging.getLogger(__name__)


def setup_logging(env_key='CFS_OPERATOR_LOG_LEVEL', default_level='INFO') -> None:
    """
    Setup the log level base on the environment variable in `env_key`. Fall back
    to the `default_level` if the key doesn't exist in the environment or if an
    invalid key is presented.
    """
    log_format = "%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get(env_key, default_level)
    log_level = logging.getLevelName(requested_log_level)

    bad_log_level = None
    if type(log_level) != int:
        bad_log_level = requested_log_level
        log_level = logging.getLevelName(default_level)
    logging.basicConfig(level=log_level, format=log_format)

    if bad_log_level:
        LOGGER.warning('Log level %r is not valid. Falling back to INFO', bad_log_level)
