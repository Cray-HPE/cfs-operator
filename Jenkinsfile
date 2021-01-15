
@Library('dst-shared@release/shasta-1.4') _

dockerBuildPipeline {
    repository = "cray"
    imagePrefix = "cray"
    app = "cfs-operator"
    name = "cray-cfs-operator"
    description = "Cray Management System - Configuration Framework Operator"
    product = "csm"
    enableSonar = true
    sendEvents = ["cfs-operator:master"]
    receiveEvent = ["ansible-execution-environment:master"]
}
