node{
	currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    def environment = target.contains("preprod") ? "preprod": "prod"
	stage("Checkout code."){
		checkout scm
	}
	stage("Run playbook."){
		// Run actual playbook
		ansiblePlaybook credentialsId: "ut-devops-${environment}_cicd",
			disableHostKeyChecking: true,
			inventory: target + ",",
            		extras: verbosity,
			playbook: 'playbooks/jumpbox/configure-settings.yml'
	}
}
