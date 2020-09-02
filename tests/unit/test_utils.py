# Copyright 2019, Cray Inc. All Rights Reserved.
""" Test the cray/cfs/operators/utils.py module """
import secrets
import uuid

from cray.cfs.operator import utils


cfs_name = secrets.token_hex(8)
session_id = str(uuid.uuid4())
obj_name = 'cfs-'+session_id
mock_cfs = {
    'metadata': {
        'name': cfs_name,
        'labels': {
            'session-id': session_id
        }
    }
}
mock_obj = {
    'metadata': {
        'name': obj_name,
        'labels': {
            'cfsession': cfs_name,
            'session-id': session_id
        }
    }
}


def test_k8sObj2name():
    """ test the k8sObj2name function """
    assert utils.k8sObj2name(mock_obj) == obj_name


def test_object2cfsName():
    """ test the object2cfsName function """
    assert utils.object2cfsName(mock_obj) == cfs_name


def test_cfs2sessionId():
    """ test the cfs2sessionId function """
    assert utils.cfs2sessionId(mock_cfs) == session_id


def test_cfs2objectName():
    """ test the cfs2objectName function """
    assert utils.cfs2objectName(mock_cfs) == obj_name
