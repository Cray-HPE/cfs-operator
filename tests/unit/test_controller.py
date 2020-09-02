# Copyright 2019, Cray Inc. All Rights Reserved.
""" Test the cray/cfs/operators/controller.py module """
from unittest.mock import patch

# Class in controller module under test
from cray.cfs.operator.controller import BaseController


def test__init__():
    """ Test BaseController Constructor """
    env = {'foo': 'bar'}
    assert BaseController(env).env == env


def test_handle_event_error(error_event, aee_env):
    """ Test BaseController _handle_error """
    with patch.object(BaseController, '_handle_error') as mock_handler:
        conn = BaseController({})
        conn.handle_event(error_event)
        mock_handler.assert_called_with(error_event)

    conn = BaseController({})
    conn._handle_error(error_event)


def test_handle_event_added(added_event, event_obj_name, event_resource_version,
                            event_obj_type, event_obj):
    """ Test BaseController _handle_added """
    with patch.object(BaseController, '_handle_added') as mock_handler:
        conn = BaseController({})
        conn.handle_event(added_event)
        mock_handler.assert_called_with(
            event_obj, event_obj_name, event_obj_type, event_resource_version, added_event
        )

    conn = BaseController({})
    conn._handle_added(
        event_obj, event_obj_name, event_obj_type, event_resource_version, added_event
    )


def test_handle_event_modified(modified_event, event_obj_name,
                               event_resource_version, event_obj_type,
                               event_obj):
    """ Test BaseController _handle_modified """
    with patch.object(BaseController, '_handle_modified') as mock_handler:
        conn = BaseController({})
        conn.handle_event(modified_event)
        mock_handler.assert_called_with(
            event_obj, event_obj_name, event_obj_type, event_resource_version, modified_event
        )

    conn = BaseController({})
    conn._handle_modified(
        event_obj, event_obj_name, event_obj_type, event_resource_version, modified_event
    )


def test_handle_event_deleted(deleted_event, event_obj_name,
                              event_resource_version, event_obj_type, event_obj):
    """ Test BaseController _handle_deleted """
    with patch.object(BaseController, '_handle_deleted') as mock_handler:
        conn = BaseController({})
        conn.handle_event(deleted_event)
        mock_handler.assert_called_with(
            event_obj, event_obj_name, event_obj_type, event_resource_version, deleted_event
        )

    conn = BaseController({})
    conn._handle_deleted(
        event_obj, event_obj_name, event_obj_type, event_resource_version, deleted_event
    )
