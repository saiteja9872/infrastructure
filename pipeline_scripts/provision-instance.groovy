node {
	currentBuild.displayName = "#${BUILD_NUMBER}: ${host_short_name}"
	def environment = subnet_name.contains("preprod") ? "preprod" : "prod"
	echo "Detected environment '${environment}'."

    stage("Checkout playbook from GitHub.") {
    	checkout changelog: false,
        poll: false,
        scm: [$class: 'GitSCM',
            branches: [[name: 'refs/heads/master']],
            doGenerateSubmoduleConfigurations: false,
            extensions: [[$class: 'SparseCheckoutPaths',
                sparseCheckoutPaths: [[path: 'playbooks/provision-instance.yml']]]],
            submoduleCfg: [],
            userRemoteConfigs: [[credentialsId: '96d07716-66e9-48c1-9e88-ef1fcd2c9112',
            url: 'https://git.viasat.com/BBC-Term/infrastructure.git']]]
  	}
  	stage("Run playbook with credentials."){
  		withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
                          accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                          credentialsId: "${AWS_CREDENTIALS}",
                          secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
			   ansiblePlaybook extras: '${verbosity}',
               playbook: 'playbooks/provision-instance.yml',
               become: true
		}
		archiveArtifacts artifacts: 'ec2.ip', onlyIfSuccessful: true
  	}
  	def newIpAddress = sh (
	    script: 'cat ec2.ip',
	    returnStdout: true
	).trim()
  	stage("Set DNS entries."){
  		build job: 'dns-setter', parameters: [
	  		string(name: 'host_short_name', value: host_short_name),
	  		string(name: 'ip_address', value: newIpAddress),
	  		string(name: 'region', value: "${region}"),
	  		string(name: 'stripe', value: "ut-devops-${environment}")
  		]
  	}
  	stage("Run GI playbooks for initial configurations."){
  	    sleep 30
  	    def env = (environment == "preprod") ? "pre" : "prod"
        def region_code = ("${region}" == "eu-west-1") ? "euw01": "nae01"
  		build job: 'server-infra-baseline', quietPeriod: 10, parameters: [
	  		string(name: 'target', value: newIpAddress),
            string(name: 'region_code', value: region_code),
	  		string(name: 'environment', value: environment),
	  		string(name: 'allowed_groups', value: "[\"ut-devops-${environment}_vs2_jumpbox_admins\", \"modot-jb-${env}\"]"),
	  		string(name: 'sudo_groups', value: "[\"ut-devops-${environment}_vs2_jumpbox_admins\"]"),
	  		string(name: 'verbosity', value: verbosity)
  		]
  	}
}
