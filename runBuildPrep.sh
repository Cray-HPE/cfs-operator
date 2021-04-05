#!/usr/bin/env sh

#
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
#

./update_tags.sh

VERSION=`cat .version`
sed -i s/@VERSION@/${VERSION}/g kubernetes/cray-cfs-operator/Chart.yaml

