#!/usr/bin/env sh

#
# Copyright 2020, Cray Inc.  All Rights Reserved.
#

wget http://car.dev.cray.com/artifactory/shasta-premium/SCMS/noos/noarch/release/shasta-1.3/cms-team/manifest.txt
aee_image_tag=$(cat manifest.txt | grep cray-aee | sed s/.*://g | tr -d '[:space:]')
sed -i s/@aee_image_tag@/${aee_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
rm manifest.txt