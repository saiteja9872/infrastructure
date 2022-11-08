node {
    currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    def environment = target.contains("preprod") ? "preprod" : "prod"
    echo "Detected environment '${environment}'."

    stage("Checkout playbook from GitHub.") {
        checkout changelog: false, poll: false, scm: [
            $class: 'GitSCM',
            branches: [[name: 'refs/heads/master']],
            doGenerateSubmoduleConfigurations: false,
            extensions: [[
                $class: 'SparseCheckoutPaths',
                sparseCheckoutPaths: [[path: 'playbooks/bbserver']]
            ]],
            submoduleCfg: [],
            userRemoteConfigs: [[credentialsId: '96d07716-66e9-48c1-9e88-ef1fcd2c9112', url: 'https://git.viasat.com/BBC-Term/infrastructure.git']]
        ]
    }
    stage("Run playbook with credentials."){
        def thisCredentialsId = "ut-devops-${environment}_cicd"
        def thisVaultCredentialsId = "preprod-ansible-vault-credentials"

        echo "Using credentials ID ${thisCredentialsId} and vault password ID ${thisVaultCredentialsId}..."
        ansiblePlaybook extras: "${verbosity} --extra-vars 'THIS_ENVIRONMENT=${environment}'",
            playbook: 'playbooks/bbserver/deploy-base.yml',
            credentialsId: thisCredentialsId,
            vaultCredentialsId: thisVaultCredentialsId,
            inventory: '${target},'
    }
}
