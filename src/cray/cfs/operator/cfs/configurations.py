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

import json
import logging
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from . import requests_retry_session
from . import ENDPOINT as BASE_ENDPOINT

LOGGER = logging.getLogger(__name__)
ENDPOINT = "%s/%s" % (BASE_ENDPOINT, __name__.lower().split('.')[-1])


def get_configuration(id):
    """Get information for a single configuration stored in CFS"""
    url = ENDPOINT + '/' + id
    configuration = {}
    session = requests_retry_session()
    try:
        response = session.get(url)
        response.raise_for_status()
        configuration = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to CFS: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from CFS: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from CFS: {}".format(e))
        raise e
    return configuration
