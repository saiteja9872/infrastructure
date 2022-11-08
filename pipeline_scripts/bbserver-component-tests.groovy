node('master'){
    currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    def environment = target.contains("preprod") ? "preprod": "prod"

    def testsCode = "1"
    try {
        stage("Run tests"){
            withCredentials([usernamePassword(credentialsId: "ut-devops-${environment}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
                sh '''set +x; sshpass -e ssh -q ${SSH_USER}@${target} <<-EOF
                    sudo su
                    source /home/${SSH_USER}/bbserverproject/bbserverprojenv/bin/activate
                    cd /home/${SSH_USER}/bbserver/modotserver
                    (coverage run --source='.' ./manage.py test bbmanager/tests && echo 0 > /var/tmp/tests.exit_code) || echo 1 > /var/tmp/tests.exit_code
                    coverage report -m
                    coverage xml -o /var/tmp/coverage.report
                    chown ${SSH_USER} /var/tmp/coverage.report
                    chown ${SSH_USER} /var/tmp/tests.exit_code
                    exit # Exit sudo
                    exit # Exit SSH session
                    EOF'''
                sh '''set +x;sshpass -e scp -q ${SSH_USER}@${target}:/var/tmp/coverage.report .'''
                testsCode = sh returnStdout:true, script: '''set +x;sshpass -e ssh -q ${SSH_USER}@${target} cat /var/tmp/tests.exit_code'''
                testsCode = testsCode.trim()
            }
        }
        stage("Publish findings"){
            cobertura autoUpdateHealth: false, autoUpdateStability: false, coberturaReportFile: 'coverage.report', conditionalCoverageTargets: '70, 0, 0', failUnhealthy: false, failUnstable: false, lineCoverageTargets: '80, 0, 0', maxNumberOfBuilds: 0, methodCoverageTargets: '80, 0, 0', onlyStable: false, sourceEncoding: 'ASCII', zoomCoverageChart: false
            sh "set +x; echo ${testsCode}"

            if ("${testsCode}" != "0"){
                error("Not all tests passed - see console for failed test cases.")
            }
        }

    } catch (Exception e) {
        currentBuild.result = 'FAILURE'

    } finally {
        if (currentBuild?.result == 'FAILURE'){
            notify('danger', 'not all bbserver component tests passed', true)
        }
        else if (currentBuild?.getPreviousBuild()?.result == 'FAILURE')
        {
            notify('good', 'all bbserver component tests passed', true)
        }
        else {
            notify('good', 'all bbserver component tests passed', false)
        }
    }
}

def notify(color, message, alert) {
    def fullMessage = "${message} on ${target} (<${env.BUILD_URL}|Open>)"

    if (alert) {
        def emailAddress = 'modotsupport@viasat.com'
        emailext(body: message + ' on ${target}\n\nSee: $PROJECT_NAME, Build #$BUILD_NUMBER ($BUILD_STATUS) at ${BUILD_URL}console for more details.',
            subject: 'BB Server component tests $BUILD_STATUS',
            to: emailAddress,
            replyTo: emailAddress,
            from: emailAddress)

        fullMessage = '@channel ' + fullMessage
    }

    slackSend(color: color, message: fullMessage)
}
