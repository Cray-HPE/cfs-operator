#
# MIT License
#
# (C) Copyright 2019-2022, 2024-2025 Hewlett Packard Enterprise Development LP
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
ARG BASE_CONTAINER=artifactory.algol60.net/docker.io/alpine:3.18
FROM ${BASE_CONTAINER} as base
WORKDIR /app
# Upgrade apk-tools and busybox to avoid Snyk-detected security issues
RUN apk add --upgrade --no-cache apk-tools busybox && \
	apk update && \
    apk add --no-cache gcc musl-dev openssh-client libffi-dev openssl-dev python3-dev py3-pip make curl bash git && \
    apk -U upgrade --no-cache
ADD constraints.txt requirements.txt /app/
RUN --mount=type=secret,id=netrc,target=/root/.netrc pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U wheel && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 list --format freeze
COPY src/ /app/lib
COPY .version /app/lib/
RUN cd /app/lib && pip3 install --no-cache-dir . && pip3 list --format freeze
RUN chmod 755 $(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")/cray/cfs/clone/askpass.py

# Nox Environment
FROM base as nox
COPY requirements-dev.txt noxfile.py /app/
RUN pip3 install --ignore-installed distlib --no-cache-dir -r /app/requirements-dev.txt && pip3 list --format freeze

# Unit testing
FROM nox as testing
COPY requirements-test.txt .coveragerc /app/
COPY tests/unit/ /app/tests/unit/
ENV BUILDENV=pipeline
CMD ["nox", "--nocolor", "-s", "unittests"]

# Linting
FROM testing as lint
COPY requirements-lint.txt .flake8 sonar-project.properties /app/
ENV BUILDENV=pipeline
CMD ["nox", "--nocolor", "-s", "lint"]

# Main application - CFS Kubernetes Operator
FROM base as application
RUN mkdir -p /inventory
USER nobody:nobody
ENTRYPOINT [ "python3", "-m", "cray.cfs.operator" ]
