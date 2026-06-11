#
# MIT License
#
# (C) Copyright 2019, 2021-2022, 2026 Hewlett Packard Enterprise Development LP
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
cray.cfs.logging - helper functions for logging in CFS
"""
import logging
import datetime
import os
import threading
import sys

from csm_utils.logging import exc_type_msg

from cray.cfs.operator.cfs.options import options


LOGGER = logging.getLogger(__name__)

# Prevent multiple threads from updating the log level at the same time
# (mainly to avoid noise in the log)
_LogLevelUpdateLock = threading.Lock()


def setup_logging(env_key='STARTING_LOG_LEVEL', default_level='INFO') -> None:
    """
    Setup the log level base on the environment variable in `env_key`. Fall back
    to the `default_level` if the key doesn't exist in the environment or if an
    invalid key is presented.
    """
    log_format = "%(asctime)-15s - %(process)d - %(thread)d - %(levelname)-7s - %(name)s - %(message)s"
    requested_log_level = os.environ.get(env_key, default_level)
    log_level = logging.getLevelName(requested_log_level)

    bad_log_level = None
    if type(log_level) != int:
        bad_log_level = requested_log_level
        log_level = logging.getLevelName(default_level)
    logging.basicConfig(level=log_level, format=log_format)

    if bad_log_level:
        LOGGER.warning('Log level %r is not valid. Falling back to INFO', bad_log_level)


def update_logging(update_options=False) -> None:
    """ Updates the current logging level base on the value in the options database """
    try:
        options.update(force=update_options)
    except Exception as e:
        LOGGER.error('Error updating options (force=%s): %s', update_options, exc_type_msg(e))
        return
    try:
        if not options.logging_level:
            LOGGER.debug('options.logging_level is falsey/not set')
            return
    except Exception as e:
        LOGGER.error('Error checking options.logging_level: %s', exc_type_msg(e))
        return
    try:
        desired_level_str = options.logging_level.upper()
        desired_level_int = logging.getLevelName(desired_level_str)
        current_level_int = LOGGER.getEffectiveLevel()
        if current_level_int == desired_level_int:
            # No update needed
            return
        # Take a lock to prevent multiple threads from doing this
        with _LogLevelUpdateLock:
            current_level_str = logging.getLevelName(current_level_int)
            LOGGER.log(current_level_int, 'Changing logging level from %s to %s',
                       current_level_str, desired_level_str)
            logging.getLogger().setLevel(desired_level_int)
            LOGGER.log(desired_level_int, 'Logging level changed from %s to %s',
                       current_level_str, desired_level_str)
    except Exception as e:
        LOGGER.error('Error updating logging level: %s', exc_type_msg(e))
