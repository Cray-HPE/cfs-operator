#!/usr/bin/env sh

#
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
#

# The URL to the manifest.txt file must be updated to point to the stable manifest when cutting a release branch.
wget https://arti.dev.cray.com/artifactory/csm-misc-master-local/manifest/manifest.txt
aee_image_tag=$(cat manifest.txt | grep cray-aee | sed s/.*://g | tr -d '[:space:]')
sed -i s/@aee_image_tag@/${aee_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
rm manifest.txt
