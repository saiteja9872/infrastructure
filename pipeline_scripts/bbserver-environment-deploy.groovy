node("master"){
    currentBuild.displayName = "#${BUILD_NUMBER}: ${environment}"
    def envURL = "bbserver.ut-devops-${environment}.viasat.io"
    def numNodes = 2
    for (int i = 0; i < numNodes; i++) {
        def nodeNum = i + 1
        def thisHostName = "${environment}-bbserver-official-${nodeNum}.nae01.ut-devops-${environment}.viasat.io"
        stage("Deploy to node #${nodeNum}") {
            build job: 'bbserver-deploy', parameters: [
                string(name: 'target', value: thisHostName), 
                gitParameter(name: 'git_revision', value: 'origin/master'),
            ]
        }
        stage("Component test node #${nodeNum}"){
            build job: 'bbserver-component-tests', parameters: [
                string(name: 'target', value: thisHostName)
            ]
        }
        stage("Functional test node #${nodeNum}"){
            build job: 'bbserver-functional-tests', parameters: [
                string(name: 'TARGET', value: thisHostName)
            ]
        }
    }
    stage("Functional test for Load Balancer ${envURL}"){
        build job: 'bbserver-functional-tests', parameters: [
            string(name: 'TARGET', value: envURL)
        ]
    }
}
