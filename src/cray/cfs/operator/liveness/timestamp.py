# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)
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
