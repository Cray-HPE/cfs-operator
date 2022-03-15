#!/bin/bash
#
# MIT License
#
# (C) Copyright 2019, 2021-2022 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Extract coverage.xml to replace container file paths with local ones
cd ${WORKSPACE}/results
tar -xzvf buildResults.tar.gz
cd ${WORKSPACE}

# Mangle the path from the nox output to the source path in the coverage file so
# Sonarqube can find it
SOURCE="${WORKSPACE}/src"
sed -i "s|.nox/unittests-3-6/lib/python3.6/site-packages|$SOURCE|" ${WORKSPACE}/results/testing/coverage.xml

# Update the version for Sonarqube dynamically
CFS_OPERATOR_VERSION="`cat ${WORKSPACE}/.version`"
echo CFS_OPERATOR_VERSION=$CFS_OPERATOR_VERSION
sed -i "s|@CFS_OPERATOR_VERSION@|$CFS_OPERATOR_VERSION|" ${WORKSPACE}/sonar-project.properties
