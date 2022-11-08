node('master'){
    currentBuild.displayName = "#${BUILD_NUMBER}: ${target}"
    def environment = "preprod"
    stage("Run Coverity Analysis and Commit Findings"){
        withCredentials([usernamePassword(credentialsId: "ut-devops-${environment}_cicd", passwordVariable: 'SSHPASS', usernameVariable: 'SSH_USER')]) {
            sh (
            script:"""
                set +x; sshpass -e ssh -o StrictHostKeyChecking=no -q ${SSH_USER}@${target} <<-EOF
                sudo su
                cd ${varTmpDir}
                rm -rf ${varTmpDir}/coverity-results
                ${covBinPath}/cov-build --dir ${varTmpDir}/coverity-results --fs-capture-search ${mtoolDir} --no-command
                ${covBinPath}/cov-analyze --dir ${varTmpDir}/coverity-results --strip-path ${mtoolDir} --aggressiveness-level high --all --enable-callgraph-metrics 
                ${covBinPath}/cov-commit-defects --host ${covHost} --dataport ${covPort} --stream ${covStream} --on-new-cert trust -ssl --dir ${varTmpDir}/coverity-results --auth-key-file ${covKey}
                exit # Exit sudo
                exit # Exit SSH session
                EOF"""
            )
        }
    }
}
