# Copyright 2019, 2021 Hewlett Packard Enterprise Development LP
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
import nox


@nox.session(python='3')
def unittests(session):
    """ cray.cfs.operator unit tests """
    session.install('-r', 'requirements-test.txt')
    session.install('-r', 'requirements.txt')
    runtime = session.env.get('BUILDENV', 'local')

    # Local runs get HTML coverage reports, Pipeline runs get XML
    xml_unittests = None
    xml_coverage = None
    html_coverage = None
    if runtime == 'local':
        install_source = "./src/"
        html_coverage = "htmlcov"
    elif runtime == 'pipeline':
        install_source = '/app/lib/'
        xml_unittests = '--junitxml=/results/unittests.xml'
        xml_coverage = '--cov-xml'
    session.install(install_source)  # cray.cfs.operator package

    cmd = [
        'py.test',
        '--cov-config=.coveragerc',
        '--cov=cray.cfs.operator',
    ]
    if html_coverage:
        cmd.extend(['--cov-report', 'html:htmlcov'])
    if xml_coverage:
        cmd.extend(['--cov-report', 'xml:/results/coverage.xml'])
    if xml_unittests:
        cmd.append(xml_unittests)

    session.run(*cmd, 'tests')

    # Copy the coveragerc file into the build results for later use by Sonarqube
    if runtime == 'pipeline':
        session.run('/bin/cp', '/app/.coveragerc', '/results')


@nox.session(python='3')
def lint(session):
    session.install('-r', 'requirements-lint.txt')
    session.install('-r', 'requirements.txt')
    runtime = session.env.get('BUILDENV', 'local')
    cmd = ['flake8', '--tee']
    if runtime == 'local':
        install_source = "./src/"
        target = './src/cray'
        cmd.append(target)
    elif runtime == 'pipeline':
        install_source = '/app/lib/'
        target = '/app/lib/cray'
        cmd.extend(['--output-file=/results/pylint.txt', target])

    session.install(install_source)  # cray.cfs.operator package
    session.run(*cmd)

    # Copy files into the build results for later use by Sonarqube
    if runtime == 'pipeline':
        session.run(
            '/bin/cp',
            '/app/.version', '/app/sonar-project.properties',
            '/results'
        )
