node{
    currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    stage("Install packages and set up modem keys") {
        build job: 'jumpbox-packages', parameters: [
            string(name: 'target', value: target),
            string(name: 'verbosity', value: verbosity),
            string(name: 'mtool_branch', value: "${mtool_branch}")
        ]
    }
    stage("Set up VNC server") {
        build job: 'jumpbox-configure', parameters: [
            string(name: 'target', value: target),
            string(name: 'verbosity', value: verbosity)
        ]
    }
    stage("Deploy MoDOT tools") {
        build job: 'modot-tools-deploy', parameters: [
            string(name: 'target', value: target),
            gitParameter(name: 'branch_name', value: "${mtool_branch}"),
            string(name: 'verbosity', value: verbosity)
        ]
    }
}
