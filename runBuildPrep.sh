#!/usr/bin/env sh

#
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
#

wget http://car.dev.cray.com/artifactory/csm/SCMS/noos/noarch/release/shasta-1.4/cms-team/manifest.txt
aee_image_tag=$(cat manifest.txt | grep cray-aee | sed s/.*://g | tr -d '[:space:]')
sed -i s/@aee_image_tag@/${aee_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
cfs_operator_image_tag=$(cat .version)
sed -i s/@cfs_operator_image_tag@/${cfs_operator_image_tag}/g kubernetes/cray-cfs-operator/values.yaml
rm manifest.txt
./update_versions.sh
exit $?
