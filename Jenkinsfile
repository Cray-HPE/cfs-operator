
@Library('dst-shared@master') _

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

    githubPushRepo = "Cray-HPE/cfs-operator"
    /*
        By default all branches are pushed to GitHub

        Optionally, to limit which branches are pushed, add a githubPushBranches regex variable
        Examples:
        githubPushBranches =  /master/ # Only push the master branch
        
        In this case, we push bugfix, feature, hot fix, master, and release branches
    */
    githubPushBranches =  /(bugfix\/.*|feature\/.*|hotfix\/.*|master|release\/.*)/ 
}
