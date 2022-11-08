node
{
    stage("Get branch and set up testing environment on target"){
        build job: 'set-up-mtool-tests', parameters: [
            string(name: 'target', value: "${target}"),
            string(name: 'ref', value: "${sha1}"),
            string(name: 'subdir', value: "${checkout_dir}")
        ]
        failedTests = []
    }
    stage("Run black linter tests."){
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE')
        {
            (blackExitCode, blackResult) = runFormatter("b")
            if ("${blackExitCode}" > 0){
                println "${blackResult}\n"
                failedTests.push("black")
                sh "exit ${blackExitCode}"
            }
        }
    }
    stage("Run flake8 linter tests."){
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE')
        {
            (flakeExitCode, flakeResult) = runFormatter("f")
            if ("${flakeExitCode}" > 0){
                println "${flakeResult}\n"
                failedTests.push("flake8")
                sh "exit ${flakeExitCode}"
            }
        }
    }
    stage("Run pylint linter tests."){
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE')
        {
            (pylintExitCode, pylintResult) = runFormatter("p")
            if ("${pylintExitCode}" > 0){
                println "${pylintResult}\n"
                failedTests.push("pylint")
                sh "exit ${pylintExitCode}"
            }
        }
    }
    stage("Clean up test environment"){
        if (clean_up.toString() == 'true') {
            build job: 'tear-down-test', parameters: [
                string(name: 'target', value: "${target}"),
                string(name: 'test_dir', value: "${test_dir}"),
                string(name: 'venv_dir', value: "${venv_dir}")
            ]
        }
        else {
            println "Please make sure to clean up after yourself"
        }
    }
    stage("Analyze and report results"){
        if ("${blackExitCode}" > 0 || "${flakeExitCode}" > 0 || "${pylintExitCode}" > 0){
            currentBuild.result = 'FAILURE'
            // do not send out notifications
            // leaving for future use
            //notify('danger')
        }
    }
}


/**
 * runFormatter
 * Gets the modified file to run the format_python.sh script on.
 * Ssh into the target machine, become root, and run the format_python.sh script
 * and write the 0 or 1 to a file depending on success or failure. If there are no
 * modified files, this will return [0, "0"] since the format_python.sh will error if
 * no input files were passed in.
 * @param  program The type of program to run with the formatter
 * @return list contains the exit code and output of running the format_python.sh script
 */
def runFormatter(program){
    withCredentials([usernamePassword(credentialsId: "ut-devops-preprod_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
        files = sh (returnStdout:true, script: '''set +x; set +e; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} cat ${test_dir}/${checkout_dir}/modified_python_files.txt''').trim()
        filesNoNewlines = files.replace("\n", " ").replace("\r", " ")
        if (!filesNoNewlines.isEmpty()){
            echo "Format_python.sh will be run on the following modified files"
            echo "${files}"
            testResult = sh (returnStdout:true,
            script:"""
                set +x; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
                sudo su
                cd ${test_dir}/${checkout_dir}/
                source ${venv_dir}/bin/activate
                ./format_python.sh -s -p ${program} -a ${COV_KEY_FILE_PATH} -m read ${filesNoNewlines} && echo 0 > ${test_dir}/linter_test.txt || echo 1 > ${test_dir}/linter_test.txt
                chown ${SSH_USER} /var/tmp/test_dir/linter_test.txt
                exit # Exit sudo session
                exit # Exit SSH session
                EOF"""
            )
            testResult.trim()
            testsCode = sh (returnStdout:true, script: '''set +x;sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} cat ${test_dir}/linter_test.txt''') as Integer
            return [ testsCode, testResult]
        }else{
            echo "No modified files found. Will not test linting or analysis."
            return[0, "0"]
        }
    }
}


/**
 * notify
 * Sends email and slack message depending on send_alert parameter
 * @param  color The type of slack notification color
 */
def notify(color) {
    if (send_alert.toString() == 'true') {
        def emailAddress = 'modotsupport@viasat.com'
        def message = '$ghprbPullAuthorLogin\'s PR to $ghprbGhRepository has failed code quality checks. View the PR ${ghprbPullLink}. \n ' +
        'To re-run the code quality checks, please comment "$RERUN_TEST_TEXT" on the PR. See: $PROJECT_URL.\n' +
        "Failed tests: ${failedTests} \n" +
        'Build #$BUILD_NUMBER ($BUILD_STATUS) at ${BUILD_URL} console for more details.'
        slackMsg = "${env.ghprbPullAuthorLogin}'s PR to ${env.ghprbGhRepository} has failed code quality checks. View the PR ${env.ghprbPullLink}.\n" +
        "To re-run the code quality checks, please comment '${env.RERUN_TEST_TEXT}' on the PR.\n" +
        "Failed tests: ${failedTests}"
        slackSend(color: color, message: slackMsg)
        emailext(body: message,
            attachLog: true,
            subject: 'PR Failed Code Quality Checks on ${ghprbGhRepository}',
            to: emailAddress,
            replyTo: emailAddress,
            from: "modotsupport@viasat.com")
    }
}
