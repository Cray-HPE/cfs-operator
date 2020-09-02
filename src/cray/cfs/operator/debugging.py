# Copyright 2019, Cray Inc. All rights reserved.
""" Special debugging functions to help track CASMCMS-4396 """

import logging
import os
import signal
import sys
import threading
import time
import traceback

LOGGER = logging.getLogger('cray.cfs.debugging')
WATCH_FILE = '/tmp/debug'


def log_level_watcher():
    try:
        starting_log_level = LOGGER.getEffectiveLevel()
        LOGGER.info('Starting debug thread.  Watching file {}.  Starting log level is {}'.format(
            WATCH_FILE, logging.getLevelName(starting_log_level)))
        if starting_log_level == logging.DEBUG:
            return
        while True:
            time.sleep(1)
            current_log_level = LOGGER.getEffectiveLevel()
            if os.path.isfile(WATCH_FILE) and current_log_level != logging.DEBUG:
                update_log_level(logging.DEBUG)
            elif not os.path.isfile(WATCH_FILE) and current_log_level == logging.DEBUG:
                update_log_level(starting_log_level)
    finally:
        LOGGER.info('Exiting debug thread')


def update_log_level(new_level):
    current_level = LOGGER.getEffectiveLevel()
    if current_level != new_level:
        LOGGER.log(current_level, 'Changing logging level from {} to {}'.format(
            logging.getLevelName(current_level), logging.getLevelName(new_level)))
        logger = logging.getLogger()
        logger.setLevel(new_level)
        LOGGER.log(new_level, 'Logging level changed from {} to {}'.format(
            logging.getLevelName(current_level), logging.getLevelName(new_level)))


def dumpstacks(signum, frame):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId, ""), threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    LOGGER.warning('\n'.join(code))


signal.signal(signal.SIGINT, dumpstacks)
debug_thread = threading.Thread(
    target=log_level_watcher,
    name="debug",
)
debug_thread.start()
