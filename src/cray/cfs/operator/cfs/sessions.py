# Copyright 2020 Hewlett Packard Enterprise Development LP

import json
import logging
from requests.exceptions import HTTPError, ConnectionError
from urllib3.exceptions import MaxRetryError

from . import requests_retry_session
from . import ENDPOINT as BASE_ENDPOINT

LOGGER = logging.getLogger(__name__)
ENDPOINT = "%s/%s" % (BASE_ENDPOINT, __name__.lower().split('.')[-1])


def get_session(session_id):
    """Get information for a single CFS session"""
    url = ENDPOINT + '/' + session_id
    session = requests_retry_session()
    try:
        response = session.get(url)
        response.raise_for_status()
        cfs_session = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to CFS: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from CFS: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from CFS: {}".format(e))
        raise e
    return cfs_session


def get_sessions():
    """Get information for all CFS sessions"""
    url = ENDPOINT
    session = requests_retry_session()
    try:
        response = session.get(url)
        response.raise_for_status()
        cfs_sessions = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to CFS: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from CFS: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from CFS: {}".format(e))
        raise e
    return cfs_sessions


def update_session(session_id, data):
    """Update information for a single CFS session"""
    url = ENDPOINT + '/' + session_id
    session = requests_retry_session()
    try:
        response = session.patch(url, json=data)
        response.raise_for_status()
        cfs_session = json.loads(response.text)
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to CFS: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from CFS: {}".format(e))
        raise e
    except json.JSONDecodeError as e:
        LOGGER.error("Non-JSON response from CFS: {}".format(e))
        raise e
    return cfs_session


def delete_sessions(status=None, age=None):
    """Get information for a single CFS session"""
    url = ENDPOINT
    params = {}
    if status:
        params['status'] = status
    if age:
        params['age'] = age
    session = requests_retry_session()
    try:
        response = session.delete(url, params=params)
        response.raise_for_status()
    except (ConnectionError, MaxRetryError) as e:
        LOGGER.error("Unable to connect to CFS: {}".format(e))
        raise e
    except HTTPError as e:
        LOGGER.error("Unexpected response from CFS: {}".format(e))
        raise e


def update_session_status(session_id, data):
    """Helper specifically for updating session status"""
    session_status = {'status': {'session': data}}
    return update_session(session_id, session_status)
