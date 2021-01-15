#!/usr/bin/env sh

#
# Copyright 2020, Cray Inc.  All Rights Reserved.
#

wget http://car.dev.cray.com/artifactory/csm/SCMS/noos/noarch/dev/master/cms-team/manifest.txt
aee_image_tag=$(cat manifest.txt | grep cray-aee | sed s/.*://g | tr -d '[:space:]')
sed -i s/@aee_image_tag@/${aee_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
rm manifest.txt
