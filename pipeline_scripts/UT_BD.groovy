import java.util.regex.* 
import groovy.transform.Field

@NonCPS
def get_vers(file){
    def lines = readFile(file)
    return lines
}

pipeline {
    agent {

            label "vcalfutd04"

    }

    environment {
        APPTOKEN = credentials('ut_bd_token')
        BD_URL = "https://blackduck.infosec.viasat.io"
        BD_JAR = "synopsys-detect-7.9.0.jar"
        APP_DIR = "${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev/"
        // added for override
        DETECT_JAR = "/tmp/${BD_JAR}"

    }

    stages {

        stage('clean up and P4 Sync') {
            steps {
                deleteDir()
                echo "p4 sync..."
                checkout poll: false, scm: perforce(credential: 'p4svc_ut_jenkins_ssl_2', 
                    populate: forceClean(have: true, parallel: [enable: false, minbytes: '1024', minfiles: '1', threads: '4'], 
                    pin: 'now', quiet: true), 
                    workspace: manualSpec(charset: 'none', name: 'p4svc_ut_jenkins_${JOB_NAME}', 
                    pinHost: true, spec: clientSpec(allwrite: false, backup: false, clobber: true, compress: false, line: 'LOCAL', 
                    locked: false, modtime: false, rmdir: true, serverID: '', streamName: '', type: 'WRITABLE', 
                    view: '''//LeapFrog/Technical/Software/code/common/instrumentation/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/instrumentation/...
//LeapFrog/Technical/Software/code/common/lifeline/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/lifeline/... 
//LeapFrog/Technical/Software/code/common/secure_swdl/dev/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/secure_swdl/dev/...
//LeapFrog/Technical/Software/code/common/cem/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/cem/...
//LeapFrog/Technical/Software/code/common/blackbox/v1.0/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/blackbox/v1.0/... 
//LeapFrog/Technical/Software/code/common/prod.mk //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/prod.mk
//LeapFrog/Technical/Software/code/common/rules.mk //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/rules.mk
//Afterburner/Technical/Software/code/common/patdist_client/v2.0/...  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/patdist_client/v2.0/... 
//Afterburner/Technical/Software/code/common/AbTypes.h  //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/common/AbTypes.h
//LeapFrog/Technical/Software/code/ut/dev/... //p4svc_ut_jenkins_${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/...
''')))

                script {
                    UT_version = "None"
                    Version = get_vers("LeapFrog/Technical/Software/code/ut/dev/PRODUCT_VERSION.txt")
                    if (Debug) { println(Version) }
                    // UT_version = params.UT_VERSION
                    println(UT_version)
                    def pattern = ~/(?m)Major\s+(\d+)\nMinor\s+(\d+)\nMicro\s+(\d+)\nNano\s+(\d+)\nBuild\s+(\d+)$/
                    def matcher = pattern.matcher(Version)   // if (matcher.matches()) {
                    if (matcher.find()) {
                       UT_version=  matcher.group(1) +'.'+  matcher.group(2) +'.'+  matcher.group(3) +'.'+  matcher.group(4) +'.'+ matcher.group(5)
                    } else {
                       UT_version = "NOT_FOUND"
                       println("Failed to get UT SW VERSION")
                       sh "exit 1"
                    }
                }
                echo "${UT_version}"
            }
        }       

        stage ('Black Duck Scan on Build'){

            steps { 

                sh '''
                    echo "extract build files"
                    
                '''

                synopsys_detect detectProperties: 
                    '''
                        --blackduck.url=${BD_URL}
                        --blackduck.trust.cert=true 
                        --logging.level.detect=DEBUG 
                        --detect.diagnostic=true
                        --detect.project.name=LeapFrog-ut-dev
                        --detect.project.version.name=v1
                        --detect.detector.search.depth=15
                        --detect.source.path=${APP_DIR}
                        --detect.blackduck.signature.scanner.snippet.matching="FULL_SNIPPET_MATCHING"
                        --logging.level.com.synopsys.integration=TRACE
                        --detect.blackduck.signature.scanner.copyright.search=true
                        --detect.blackduck.signature.scanner.license.search=true 
                        --blackduck.api.token="${APPTOKEN}"
                    ''', 
                    downloadStrategyOverride: [$class: 'ScriptOrJarDownloadStrategy'],
                    returnStatus: true

                }
            }           
    }     
