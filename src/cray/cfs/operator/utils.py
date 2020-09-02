# Copyright 2019, Cray Inc. All rights reserved.
""" Utility functions for the CFS Operator """
import uuid


def k8sObj2name(obj):
    return obj['metadata']['name']


def generateSessionId(cfs_obj):
    resource_id = None
    if 'metadata' in cfs_obj:
        if 'labels' in cfs_obj['metadata']:
            if 'session-id' in cfs_obj['metadata']['labels']:
                resource_id = cfs_obj['metadata']['labels']['session-id']
    if not resource_id:
        resource_id = str(uuid.uuid4())
    return resource_id


def cfs2redisServiceName(cfs_obj):
    return 'cray-cfs-dbsvc-' + k8sObj2name(cfs_obj)


def cfs2redisDeploymentName(cfs_obj):
    return 'cray-cfs-db-' + k8sObj2name(cfs_obj)


def cfs2redisNetworkPolicyName(cfs_obj):
    return 'cray-cfs-dbnp-' + k8sObj2name(cfs_obj)


def object2cfsName(obj):
    return obj['metadata']['labels']['cfsession']


def cfs2sessionId(cfs_obj):
    return cfs_obj['metadata']['labels']['session-id']


def cfs2objectName(cfs_obj):
    return 'cfs-' + cfs2sessionId(cfs_obj)
