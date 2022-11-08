node {
   for (environment in ["prod", "preprod"]){
       stage("Run tests against ${environment}"){
           try {
                build job: 'bbserver-functional-tests', parameters: [
    	           string(name: 'TARGET', value: "bbserver.ut-devops-${environment}.viasat.io"), 
    	           gitParameter(name: 'git_revision', value: 'origin/master'),
    	           string(name: 'verbosity', value: ''),
    	           string(name: 'test_marker', value: '-m critical'),
               ]
            } catch (err) {
                echo "Tests against ${environment} environment failed."
            } 
       }
   }
}
