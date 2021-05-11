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
""" Test the cray/cfs/operator/cfs package """
import requests
from mock import patch, Mock
from json.decoder import JSONDecodeError
from requests.exceptions import HTTPError, ConnectionError

from cray.cfs.operator.cfs.options import options
from cray.cfs.operator.cfs.configurations import get_configuration
from cray.cfs.operator.cfs.sessions import get_session, get_sessions, update_session_status, delete_sessions
from cray.cfs.operator.cfs import requests_retry_session


def test_successful_options():
    """
    Test reading and updating the sessionTTL option.
    """
    with patch('cray.cfs.operator.cfs.options.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '{}')
        fake_session.patch.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        options.update()
        assert (options.options == {'sessionTTL': '7d',
                                    'additionalInventoryUrl': ''})
        fake_session.get.assert_called_once()
        fake_session.patch.assert_called_once_with('http://cray-cfs-api/v2/options',
                                                   json={'sessionTTL': '7d',
                                                         'additionalInventoryUrl': ''})


def test_failed_options_read():
    """
    Test reading and updating the sessionTTL option.
    """
    with patch('cray.cfs.operator.cfs.options.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        options.update()
        assert (options.options == {'sessionTTL': '7d',
                                    'additionalInventoryUrl': ''})
        fake_session.get.assert_called_once()


def test_failed_options_read_json():
    """
    Test reading and updating the sessionTTL option.
    """
    with patch('cray.cfs.operator.cfs.options.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        options.update()
        assert (options.options == {'sessionTTL': '7d',
                                    'additionalInventoryUrl': ''})
        fake_session.get.assert_called_once()


def test_failed_options_write():
    """
    Test reading and updating the sessionTTL option.
    """
    with patch('cray.cfs.operator.cfs.options.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '{}')
        fake_session.patch.return_value = _fake_response(404, '')
        cfsrequests.return_value = fake_session
        options.update()
        assert (options.options == {'sessionTTL': '7d',
                                    'additionalInventoryUrl': ''})
        fake_session.get.assert_called_once()
        fake_session.patch.assert_called_once_with('http://cray-cfs-api/v2/options',
                                                   json={'sessionTTL': '7d',
                                                         'additionalInventoryUrl': ''})


def test_options_properties():
    """
    Test reading options properties.
    """
    options.options = {
        'sessionTTL'          : '7d',
        'defaultPlaybook'     : 'testplaybook',
        'defaultAnsibleConfig': 'testconfig'
    }
    options.session_ttl
    options.default_playbook
    options.default_ansible_config


def test_get_configuration():
    """
    Test reading configurations.
    """
    with patch('cray.cfs.operator.cfs.configurations.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '{}')
        cfsrequests.return_value = fake_session
        get_configuration('testconfig')
        fake_session.get.assert_called_once_with('http://cray-cfs-api/v2/configurations/testconfig')


def test_failed_get_configuration():
    """
    Test reading configurations failures.
    """
    with patch('cray.cfs.operator.cfs.configurations.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        try:
            get_configuration('testconfig')
        except HTTPError:
            pass
        fake_session.get.assert_called_once_with('http://cray-cfs-api/v2/configurations/testconfig')


def test_failed_get_configuration_json():
    """
    Test failures loading configuration json.
    """
    with patch('cray.cfs.operator.cfs.configurations.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        try:
            get_configuration('testconfig')
        except JSONDecodeError:
            pass
        fake_session.get.assert_called_once_with('http://cray-cfs-api/v2/configurations/testconfig')


def test_get_session():
    """
    Test reading sessions.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '{}')
        cfsrequests.return_value = fake_session
        get_session('testsession')
        fake_session.get.assert_called_once_with('http://cray-cfs-api/v2/sessions/testsession')


def test_failed_get_session_connection():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session',
               side_effect=ConnectionError()):
        exception = False
        try:
            get_session('testsession')
        except ConnectionError:
            exception = True
        assert(exception)


def test_failed_get_session_http():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            get_session('testsession')
        except HTTPError:
            exception = True
        assert(exception)


def test_failed_get_session_json():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            get_session('testsession')
        except JSONDecodeError:
            exception = True
        assert(exception)


def test_get_sessions():
    """
    Test reading sessions.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '{}')
        cfsrequests.return_value = fake_session
        get_sessions()
        fake_session.get.assert_called_once_with('http://cray-cfs-api/v2/sessions')


def test_failed_get_sessions_connection():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session',
               side_effect=ConnectionError()):
        exception = False
        try:
            get_sessions()
        except ConnectionError:
            exception = True
        assert(exception)


def test_failed_get_sessions_http():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            get_sessions()
        except HTTPError:
            exception = True
        assert(exception)


def test_failed_get_sessions_json():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.get.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            get_sessions()
        except JSONDecodeError:
            exception = True
        assert(exception)


def test_update_session():
    """
    Test reading configurations.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.patch.return_value = _fake_response(200, '{}')
        cfsrequests.return_value = fake_session
        update_session_status('testsession', {'status': 'complete'})
        fake_session.patch.assert_called_once_with(
            'http://cray-cfs-api/v2/sessions/testsession',
            json={'status': {'session': {'status': 'complete'}}})


def test_failed_update_session_connection():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session',
               side_effect=ConnectionError()):
        exception = False
        try:
            update_session_status('testsession', {'status': 'complete'})
        except ConnectionError:
            exception = True
        assert(exception)


def test_failed_update_session_http():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.patch.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            update_session_status('testsession', {'status': 'complete'})
        except HTTPError:
            exception = True
        assert(exception)


def test_failed_update_session_json():
    """
    Test reading sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.patch.return_value = _fake_response(200, '')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            update_session_status('testsession', {'status': 'complete'})
        except JSONDecodeError:
            exception = True
        assert(exception)


def test_delete_sessions():
    """
    Test reading configurations.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.delete.return_value = _fake_response(204, '{}')
        cfsrequests.return_value = fake_session
        delete_sessions()
        fake_session.delete.assert_called_once_with('http://cray-cfs-api/v2/sessions', params={})


def test_failed_delete_sessions_connection():
    """
    Test deleting sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.delete.side_effect = ConnectionError()
        cfsrequests.return_value = fake_session
        exception = False
        try:
            delete_sessions()
        except ConnectionError:
            exception = True
        assert(exception)


def test_failed_delete_sessions_http():
    """
    Test deleting sessions failures.
    """
    with patch('cray.cfs.operator.cfs.sessions.requests_retry_session') as cfsrequests:
        fake_session = Mock()
        fake_session.delete.return_value = _fake_response(404, '{}')
        cfsrequests.return_value = fake_session
        exception = False
        try:
            delete_sessions()
        except HTTPError:
            exception = True
        assert(exception)


def test_requests_retry_session():
    """
    Test reading and updating the sessionTTL option.
    """
    session = requests_retry_session()
    assert (session)


def _fake_response(status, content):
    r = requests.Response()
    r.status_code = status
    r._content = content.encode()
    return r
