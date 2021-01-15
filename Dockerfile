# Copyright 2019-2020 Hewlett Packard Enterprise Development LP
FROM dtr.dev.cray.com/baseos/alpine:3.12.0 as base
WORKDIR /app
RUN apk add --no-cache gcc musl-dev openssh libffi-dev openssl-dev python3-dev py3-pip make curl bash
ADD constraints.txt requirements.txt /app/
RUN PIP_INDEX_URL=https://arti.dev.cray.com:443/artifactory/api/pypi/pypi-remote/simple \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U wheel && \
    pip3 install --no-cache-dir -r requirements.txt
COPY src/ /app/lib
COPY .version /app/
RUN cd /app/lib && pip3 install --no-cache-dir .

# Nox Environment
FROM base as nox
COPY requirements-dev.txt noxfile.py /app/
RUN PIP_INDEX_URL=https://arti.dev.cray.com:443/artifactory/api/pypi/pypi-remote/simple \
    pip3 install --ignore-installed distlib --no-cache-dir -r /app/requirements-dev.txt

# Unit testing
FROM nox as testing
COPY requirements-test.txt .coveragerc /app/
COPY tests/unit/ /app/tests/unit/
ENV BUILDENV=pipeline
CMD ["nox", "--nocolor", "-s", "unittests"]

# Linting
FROM nox as lint
COPY requirements-lint.txt .flake8 sonar-project.properties /app/
ENV BUILDENV=pipeline
CMD ["nox", "--nocolor", "-s", "lint"]

# Main application - CFS Kubernetes Operator
FROM base as application
RUN mkdir -p /inventory
ENTRYPOINT [ "python3", "-m", "cray.cfs.operator" ]
