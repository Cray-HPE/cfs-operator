# Copyright 2020 Hewlett Packard Enterprise Development LP
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

PROTOCOL = 'http'
API_VERSION = 'v2'
SERVICE_NAME = 'cray-cfs-api'
ENDPOINT = "%s://%s/%s" % (PROTOCOL, SERVICE_NAME, API_VERSION)

LOGGER = logging.getLogger(__name__)


def requests_retry_session(retries=10, connect=10, backoff_factor=0.5,
                           status_forcelist=(500, 502, 503, 504),
                           session=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    # Must mount to http://
    # Mounting to only http will not work!
    session.mount("%s://" % PROTOCOL, adapter)
    return session


class RetryWithLogs(Retry):
    """
    This is a urllib3.utils.Retry adapter that allows us to modify the behavior of
    what happens during retry. By overwriting the superclassed method increment, we
    can provide the user with information about how frequently we are reattempting
    an endpoint.

    Providing this feedback to the user allows us to dramatically increase the number
    of retry operations within the provided call to an attempted upstream API, and
    gives users a chance to intervene on behalf of the slower upstream service. This
    behavior is consistent with existing retry behavior that is expected by all of our
    API interactions, as well, gives us a more immediate sense of feedback for overall
    system instability and network congestion.
    """
    def __init__(self, *args, **kwargs):
        # Save a copy of upstack callback to the side; this is the context we provide
        # for recursively instantiated instances of the Retry model
        self._callback = kwargs.pop('callback', None)
        super(RetryWithLogs, self).__init__(*args, **kwargs)

    def new(self, *args, **kwargs):
        # Newly created instances should have a history of callbacks made.
        kwargs['callback'] = self._callback
        return super(RetryWithLogs, self).new(*args, **kwargs)

    def increment(self, method, url, *args, **kwargs):
        pool = kwargs['_pool']
        endpoint = "%s://%s%s" % (pool.scheme, pool.host, url)
        try:
            response = kwargs['response']
            LOGGER.warning("Previous %s attempt on '%s' resulted in %s response.",
                           method, endpoint, response.status)
            LOGGER.info("Reattempting %s request for '%s'", method, endpoint)
        except KeyError:
            LOGGER.info("Reattempting %s request for '%s'", method, endpoint)
        if self._callback:
            try:
                self._callback(url)
            except Exception:
                # This is a general except block
                LOGGER.exception("Callback to '%s' raised an exception, ignoring.", url)
        return super(RetryWithLogs, self).increment(method, url, *args, **kwargs)
