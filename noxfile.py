# Copyright 2019, Cray Inc. All Rights Reserved.
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
            '/app/lib/.version', '/app/sonar-project.properties',
            '/results'
        )
