
@Library('dst-shared@release/shasta-1.3') _

dockerBuildPipeline {
    repository = "cray"
    imagePrefix = "cray"
    app = "cfs-operator"
    name = "cray-cfs-operator"
    description = "Cray Management System - Configuration Framework Operator"
    product = "shasta-premium,shasta-standard"
    enableSonar = true
    sendEvents = ["cfs-operator:master"]
    receiveEvent = ["ansible-execution-environment:master"]
}
