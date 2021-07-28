# Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
ARG BASE_CONTAINER=artifactory.algol60.net/docker.io/alpine:3.13.2
FROM ${BASE_CONTAINER} as base
ARG PIP_INDEX_URL=https://arti.dev.cray.com:443/artifactory/api/pypi/pypi-remote/simple
WORKDIR /app
RUN apk add --no-cache gcc musl-dev openssh libffi-dev openssl-dev python3-dev py3-pip make curl bash
ADD constraints.txt requirements.txt /app/
RUN PIP_INDEX_URL=${PIP_INDEX_URL} \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U wheel && \
    pip3 install --no-cache-dir -r requirements.txt
COPY src/ /app/lib
COPY .version /app/lib/
RUN cd /app/lib && pip3 install --no-cache-dir .

# Nox Environment
FROM base as nox
ARG PIP_INDEX_URL=https://arti.dev.cray.com:443/artifactory/api/pypi/pypi-remote/simple
COPY requirements-dev.txt noxfile.py /app/
RUN pip3 install --ignore-installed distlib --no-cache-dir -r /app/requirements-dev.txt

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
ENTRYPOINT [ "python3", "-m", "cray.cfs.operator" ]
