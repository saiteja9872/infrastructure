node{
    currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    def environment = target.contains("preprod") ? "preprod": "prod"
    stage("Checkout code."){
        checkout scm
        checkout(
            [
                $class: 'GitSCM',
                branches: [[name: "${mtool_branch}"]],
                doGenerateSubmoduleConfigurations: false,
                extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'modot']],
                submoduleCfg: [],
                userRemoteConfigs:
                [[
                    credentialsId: '96d07716-66e9-48c1-9e88-ef1fcd2c9112',
                    url: 'https://git.viasat.com/BBC-Term/Modot-Tools.git'
                ]]
            ]
        )

    }
    stage("Run playbook."){
        withCredentials (
                [
                    usernamePassword (
                        credentialsId: '96d07716-66e9-48c1-9e88-ef1fcd2c9112',
                        usernameVariable: 'git_usr',
                        passwordVariable: 'git_pass'
                    ),
                    usernamePassword (
                        credentialsId: "ut-devops-preprod_cicd",
                        usernameVariable: 'vault_usr_preprod',
                        passwordVariable: 'vault_pass_preprod'
                    ),
                    usernamePassword (
                        credentialsId: "ut-devops-prod_cicd",
                        usernameVariable: 'vault_usr_prod',
                        passwordVariable: 'vault_pass_prod'
                    )
                ]
        ) {
            // Run actual playbook
            ansiblePlaybook (
                credentialsId: "ut-devops-${environment}_cicd",
                disableHostKeyChecking: true,
                inventory: target + ",",
                become: true,
                extras: "${verbosity} --extra-vars 'PPA_TO_USE=${ppa_to_use} PYTHON_VERSION=${python_version} GIT_USR=${git_usr} GIT_PASS=${git_pass} vault_usr_preprod=${vault_usr_preprod} vault_pass_preprod=${vault_pass_preprod} vault_usr_prod=${vault_usr_prod} vault_pass_prod=${vault_pass_prod} environ=${environment}'",
                playbook: 'infra/playbooks/jumpbox/packages.yml'
            )
        }
    }
}
