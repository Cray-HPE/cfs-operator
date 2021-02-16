#!/usr/bin/env sh

#
# Copyright 2020 Hewlett Packard Enterprise Development LP
#

wget http://car.dev.cray.com/artifactory/csm/SCMS/noos/noarch/release/shasta-1.4/cms-team/manifest.txt
aee_image_tag=$(cat manifest.txt | grep cray-aee | sed s/.*://g | tr -d '[:space:]')
sed -i s/@aee_image_tag@/${aee_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
cfs_operator_image_tag=$(cat .version)
sed -i s/@cfs_operator_image_tag@/${cfs_operator_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
rm manifest.txt
