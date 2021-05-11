#!/bin/bash
# Copyright 2021 Hewlett Packard Enterprise Development LP
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

# This script will edit all the values.yaml files under the kubernetes
# directory, and replace instances of IMAGE_XXX_TAG with a value that is
# generated dynamically from the manifest.txt file.  e.g. IMAGE_CRAY_BOA_TAG.
#
# The "update_tags.conf" file has configuration information.
#
# Lines that start with "tags:" contain one or more tag variable names
# that are expected to be generated from the manifest.txt files.  If
# they don't exist it will cause this script to fail.
#
# Lines that start with "teams:" can contain one or more <team> elements
#
# Example:
#   tags: IMAGE_CRAY_BOA_TAG
#   teams: csm"

set -o pipefail

trap "rm -f manifest.txt" 0

#
# Extract tag variable names from update_tags.conf.
#
verify_reqs() {
    local ret var tag

    # The get_teams() function will return the error
    # if this file doesn't exist.
    [ -f update_tags.conf ] || { return 0; }

    ret=0
    while read vars; do
        for var in ${vars}; do
            tag=$(eval echo \${${var}})
            if [ -z "${tag}" ]; then
                echo "Missing ${var} from manifest file"
                ret=1
            fi
        done
    done <<-EOF
	$(grep '^tags:' update_tags.conf | sed -e 's/^tags://')
	EOF

    return ${ret}
}

TEAM_LIST=""

#
# Extract team names from update_tags.conf.
#
get_teams() {
    local teams

    if ! [ -f update_tags.conf ]; then
        echo "ERROR: missing file: update_tags.conf"
        return 1
    fi

    while read teams; do
        for item in ${teams}; do
            team=${item}
            if [ -z "${team}" ]; then
                echo "Invalid team: ${item}"
                return 1
            fi
            TEAM_LIST="${TEAM_LIST} ${item}"
        done
    done <<-EOF
	$(grep '^teams:' update_tags.conf | sed -e 's/^teams://')
	EOF

    # Strip off leading space
    echo "TEAM_LIST=${TEAM_LIST}"
    TEAM_LIST=${TEAM_LIST# }
    echo "TEAM_LIST=${TEAM_LIST}"

    return 0
}

#
# Fetch the manifest.txt file, and generate IMAGE_XXX_TAG variables
# from its contents.  Along with that, IMAGES_NAMES is constructed
# with a list of the names of all the variables that have been created.
#
get_container_versions_on_branch() {
    local branch=$1 image var tag junk

    get_teams || { return 1; }

    if [ -z "${TEAM_LIST}" ]; then
        echo "ERROR: missing team list in get_tags.conf"
        return 1
    fi

    # There can be multiple manifest.txt files that need to be pulled in
    for item in ${TEAM_LIST}; do
        team=${item}

        url="https://arti.dev.cray.com/artifactory/${team}-misc-${branch}-local/manifest/manifest.txt"
        if ! wget -nv "${url}"; then
            echo "ERROR: Could not wget ${url}"
            return 1
        fi

        echo "Contents of ${url}"
        echo "===="
        cat manifest.txt
        echo "===="

        # Generate environment variables. An entry like:
        #        cray-boa: 0.1.7-20200602224745_1c267cb
        # will generate:
        #        IMAGE_CRAY_BOA_TAG=0.1.7-20200602224745_1c267cb
        IMAGE_NAMES=""
        while read image tag junk; do
            var=$(echo IMAGE_${image%:}_TAG | tr '[a-z]-' '[A-Z]_')
            IMAGE_NAMES="${IMAGE_NAMES} ${var}"
            eval export ${var}=${tag}
        done < manifest.txt
            rm -f manifest.txt
    done

    verify_reqs || { return 1; }

    return 0
}

get_container_versions() {
    if [[ "${GIT_BRANCH}" =~ release\/.* ]]; then
        echo "Release Branch: ${GIT_BRANCH}"
        get_container_versions_on_branch "stable"
    elif [[ "${PARENT_BRANCH}" =~ release\/.* ]]; then
        echo "Parent Release Branch: ${PARENT_BRANCH}"
        get_container_versions_on_branch "stable"
    else
        echo "non-Release Branch"
        get_container_versions_on_branch "master"
    fi
}

pin_dependent_containers() {

    get_container_versions || { return 1; }

    # Build up the "sed" command
    SED_CMD="sed -i"
    for var in ${IMAGE_NAMES}; do
        tag=$(eval echo \${${var}})
        SED_CMD="${SED_CMD} -e s/${var}/${tag}/g"
    done

    for yaml_file in $(find kubernetes -name values.yaml); do
        if ! ${SED_CMD} ${yaml_file}; then
            echo "ERROR: failed: ${SED_CMD} ${yaml_file}"
            return 1
        fi
        echo "Changes to ${yaml_file}"
        git diff ${yaml_file}
    done

    return 0
}

if ! pin_dependent_containers; then
    echo "ERROR: Failed to pin dependent container versions."
    exit 1
fi

exit 0
