#!/bin/bash
# Copyright 2019, Cray Inc. All Rights Reserved.

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
