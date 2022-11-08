node('master'){
    def environment = target.contains("preprod") ? "preprod": "prod"
    def mtoolLogLoc = "/root/.mtool/logs/mtool_run.log"
    def testLogLoc = "${test_dir}/${checkout_dir}/Tests/logs/test_results.log"
    def tokenDir = "/root/etc/"
    def buildRes = "FAILURE"
    def stageRes = "FAILURE"
    def configFile = "config.txt"
    def configLoc = "/var/tmp/${configFile}"
    stage("Run and analyze tests"){
        withCredentials([usernamePassword(credentialsId: "ut-devops-${environment}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
            writeFile file: "${configFile}", text: "[CREDENTIALS]\npassword = ${SSHPASS}"
            scpExitCode = sh (returnStatus: true,
            script:"""
                chmod 600 ${configFile}
                set +x; sshpass -e scp -o StrictHostKeyChecking=no -q ${configFile} ${SSH_USER}@${target}:${configLoc}
                sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
                sudo chmod 600 ${configLoc} && sudo chown root:root ${configLoc}
                """
            )
            if ("${scpExitCode}" != 0){
                println "config failed to be scp'd over. File may already exist. Continuing"
            }
            testExitCode = sh (returnStatus:true,
            script:"""
                sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
                sudo su
                cd ${test_dir}/${checkout_dir}/Tests
                # remove log files so we get don't mess up results
                rm -f ${mtoolLogLoc}
                rm -f ${testLogLoc}
                LOGNAME=${SSH_USER} # for getpass.getuser()
                source ${venv_dir}/bin/activate
                python test_driver.py -m ${macs} -y ${modem_types} -e ${envs} -b ${mtool_bin} -i ${ips} -a ${app} -t ${test} -c ${configLoc} ${verbose} 2>&1
                """
            )

            if ("${testExitCode}" != "0"){
                println "Non zero exit code. Printing debug logs"
                mtoolLogs = getFileContents(mtoolLogLoc, environment)
                testLogs = getFileContents(testLogLoc, environment)
                println "Test logs:\n${testLogs}"
                println "Mtool logs:\n${mtoolLogs}"
                // Setup issues, mark as unstable since its not a 'true' failure
                if ("${testExitCode}" != "1"){
                        buildRes = "UNSTABLE"
                }
                stageRes = "${buildRes}"
                catchError(buildResult: "${buildRes}", stageResult: "${stageRes}") {
                    sh "exit ${testExitCode}"
                }
            }
            sh (script: """set +x;sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} sudo rm -rf ${tokenDir} ${configLoc} ${mtoolLogLoc} ${testLogLoc}""")
        }
    }
}


/**
 * getFileContents
 * Ssh into the target and returns the contents of the file. Uses global 'target' variable 
 * @param fileLoc The location of the remote file
 * @param env The environment to use the correct service account for ssh
 * @return string the file contents 
 */
def getFileContents(fileLoc, env) {
    withCredentials([usernamePassword(credentialsId: "ut-devops-${env}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
        fileContents = sh (returnStdout:true, script: """set +x;sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} sudo cat ${fileLoc}""")
        fileContents.trim()
        return fileContents
    }
}