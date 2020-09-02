# Copyright 2020, Cray Inc.
'''
A set of routines for creating or reading from an existing timestamp file.
Created on Mar 26, 2020

@author: jsl
'''
import logging
from datetime import timedelta

from liveness.timestamp import Timestamp as BaseTimestamp

LOGGER = logging.getLogger(__name__)


class Timestamp(BaseTimestamp):
    @property
    def max_age(self):
        """
        The maximum amount of time that can elapse before we consider the timestamp
        as invalid. 

        This value is returned as a timedelta object.
        """
        computation_time = timedelta(seconds=20)
        return computation_time
