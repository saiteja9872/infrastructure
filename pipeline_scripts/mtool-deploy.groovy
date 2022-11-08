//Global vars
backUpMtoolDir = "/var/tmp/modot_tools_backup/"
backUpMtoolVenv = "/var/tmp/modot_venv_backup/"
defaultMtoolDir = "/var/tmp"
defaultMtoolIntermidateDir = "modot_tools"
defaultMtoolVenvDir = "/var/tmp/modot_venv"
defaultMtoolDirFull = "${defaultMtoolDir}/${defaultMtoolIntermidateDir}"

node{
    currentBuild.displayName = "#${BUILD_NUMBER}: ${preprod_target}:${prod_target}"
    stage("Deploy to Preprod"){
        setBackUpsOnTarget(preprod_target, "preprod")
        def preProdSetUpRes = build job: 'jumpbox-setup', propagate: false, parameters: [
            string(name: 'target', value: "${preprod_target}"),
            string(name: 'mtool_branch', value: "${mtool_branch}")
        ]
        if ("${preProdSetUpRes.result}" != "SUCCESS") {
            def slackMsg = "Setting up mtool and configuring the Preprod JB jobs failed.\n" +
                           "Deployment has stopped. The Preprod JB has been reverted."
            notifyRevertError(preprod_target, "preprod", "danger", slackMsg, null, "jumpbox-setup job failed")
        }
        stage("Running Tests on Preprod"){
            def preProdTestRes = runMtoolTest(preprod_target, "preprod")
            if ("${preProdTestRes}" != "SUCCESS"){
                if ("${preProdTestRes}" == "UNSTABLE"){ 
                    // setup issues check flag if deployment should stop
                    if (fail_on_setup_issue.toString() == 'true'){
                        def slackMsg = "Mtool tests had setup issues. Deployment to Prod has stopped and Preprod has reverted."
                        notifyRevertError(preprod_target, "preprod", "danger", slackMsg, null, "Test setup issues in preprod")
                    }
                    else {
                        catchError(buildResult: "SUCCESS", stageResult: "UNSTABLE") {
                            def slackMsg = "Deployment to Preprod had test setup issues. Please check the status of the tests.\n " +
                                          "Deployment will continue to Prod"
                            notify(slackMsg, null, "warning")
                            sh "exit 2"
                        }
                    }
                }
                else {
                    // 'real' error
                    def slackMsg = "Mtool tests failed. Deployment to Prod has stopped and Preprod is reverted."
                    notifyRevertError(preprod_target, "preprod", "danger", slackMsg, null, "Mtool tests failed in preprod")
                }
            }
        }
        removeBackUpsOnTarget(preprod_target, "preprod")
    }
    stage("Deploy to Prod"){
        setBackUpsOnTarget(prod_target, "prod")
        def prodSetUpRes = build job: 'jumpbox-setup', propagate: false, parameters: [
            string(name: 'target', value: "${prod_target}")
        ]
        if ("${prodSetUpRes.result}" != "SUCCESS") {
            def slackMsg = "Setting up mtool and configuring the Prod JB jobs failed.\n" +
                           "Deployment has stopped. The Prod JB has been reverted."
            notifyRevertError(prod_target, "prod", "danger", slackMsg, null, "jumpbox-setup job failed")
        }
    }
    stage("Running Tests on Prod"){
        echo "TODO: Running Prod Tests"
        /*TODO: BBCTERMSW-22578
        This should look the same as preprod above but with prod instead*/
        removeBackUpsOnTarget(prod_target, "prod")
    }
    stage("Report Status"){
        println "${currentBuild.currentResult}"
        if ("${currentBuild.currentResult}" == "SUCCESS"){
            notify("Successfully deployed Mtool to Preprod and Prod", null, "good")
        }
        else
        {
            notify("@channel Failed to deploy Mtool to Preprod and Prod", null, "danger")
        }
    }
}


/**
 * setBackUpsOnTarget
 * Ssh into the target and backs up the modem tool dir and venv. If errors are found,
 * alert and error out (ending the pipeline)
 * @param target The jumpbox to ssh into
 * @param env The environment to use the correct service account for ssh
 * @return Nothing 
 */
def setBackUpsOnTarget(target, env){
    withCredentials([usernamePassword(credentialsId: "ut-devops-${env}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
        def status = sh (returnStatus:true,
        script:"""
            set +x; set -e; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
            sudo su
            cp -ar ${defaultMtoolDirFull} ${backUpMtoolDir} && cp -ar ${defaultMtoolVenvDir} ${backUpMtoolVenv}
            """
        )
        if ("${status}" != "0"){
            def slackMsg = "Failed to back up mtool directories on ${env}. Deployment will stop. Please see console log"
            notify(slackMsg, null, "danger")
            error("Unable to back up old Mtool directories")
        }
    }
}


/**
 * removeBackUpsOnTarget
 * Ssh into the target and remove the backup directories that were created earlier
 * @param target The jumpbox to ssh into
 * @param env The environment to use the correct service account for ssh
 * @return Nothing 
 */
def removeBackUpsOnTarget(target, env){
    withCredentials([usernamePassword(credentialsId: "ut-devops-${env}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
        testExitCode = sh (returnStatus:true,
        script:"""
            set +x; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
            sudo rm -rf ${backUpMtoolDir} ${backUpMtoolVenv}
            """
        )
    }
}


/**
 * revertToBackUpsOnTarget
 * Ssh into the target and remove the current mtool and venv directories and 
 * move the backups to be the default mtool and venv locations. If errors are found,
 * alert and error out (ending the pipeline)
 * @param target The jumpbox to ssh into
 * @param env The environment to use the correct service account for ssh
 * @return Nothing 
 */
def revertToBackUpsOnTarget(target, env){
    withCredentials([usernamePassword(credentialsId: "ut-devops-${env}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
        def status = sh (returnStatus:true,
        script:"""
            set +x; set -e; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
            sudo su
            rm -rf ${defaultMtoolDirFull} ${defaultMtoolVenvDir}
            mv ${backUpMtoolDir} ${defaultMtoolDirFull} && mv ${backUpMtoolVenv} ${defaultMtoolVenvDir}
            """
        )
        if ("${status}" != "0"){
            def slackMsg = "Failed to revert mtool directories on ${env}. Deployment will stop. Please see console log"
            notify(slackMsg, null, "danger")
            error("Unable to revert Mtool directories")
        }
    }
}


/**
 * notify
 * Sends out slack or email or both alerts  
 * @param slackMsg The message to send to slack
 * @param emailBody The body of the email to send
 * @param color The type of slack notification (either 'danger', 'good', 'warning')
 * @return Nothing 
 */
def notify(slackMsg, emailBody, color){
    def emailAddress = 'modotsupport@viasat.com'
    if (slackMsg != null) {
        slackMsg += "\nMore information <${env.BUILD_URL}|here>"
        slackSend(color: color, message: slackMsg)
    }
    if (emailBody != null) {
        emailext(body: emailBody,
            attachLog: true,
            subject: 'Failed Deployment for Mtools to Preprod and Prod',
            to: emailAddress,
            replyTo: emailAddress,
            from: emailAddress)
    }
}


/**
 * notifyRevertError
 * Wrapper that alerts, reverts the JB to the previous tools and errors out ending the pipeline
 * @param target The jumpbox to ssh into
 * @param env The environment to use the correct service account for ssh
 * @param color The type of slack notification (either 'danger', 'good', 'warning')
 * @param slackMsg The message to send to slack
 * @param emailBody The body of the email to send
 * @param errStr The message that will be printed with the error 
 * @return Nothing
 */
def notifyRevertError(target, env, color, slackMsg, emailBody, errStr){
    notify(slackMsg, emailBody, color)
    revertToBackUpsOnTarget(target, env)
    error(errStr)
}


/**
 * runMtoolTest
 * Sets up the correct macs and modem types for an environment and calls the `run-app-suite-functional-tests`
 * job to test mtool
 * @param target The jumpbox to ssh into
 * @param env The environment to use the correct service account for ssh
 * @return String the job result
 */
def runMtoolTest(target, env){
    def modemTypes = ""
    def macs = ""
    if ("${env}" == "preprod"){
        modemTypes = "${test_preprod_modem_types}"
        macs = "${test_preprod_macs}"
    }
    else {
        modemTypes = "${test_prod_modem_types}"
        macs = "${test_prod_macs}"
    }
    def jobRes = build job: 'run-app-suite-functional-tests', propagate: false, parameters: [
        string(name: 'target', value: "${target}"), 
        string(name: 'app', value: "mtool"),
        string(name: 'test', value: "${test_type}"),
        string(name: 'macs', value: "${macs}"),
        string(name: 'modem_types', value: "${modemTypes}"),
        string(name: 'venv_dir', value: "${defaultMtoolVenvDir}"),
        string(name: 'test_dir', value: "${defaultMtoolDir}"),
        string(name: 'checkout_dir', value: "${defaultMtoolIntermidateDir}")
    ]
    return "${jobRes.result}"
}
