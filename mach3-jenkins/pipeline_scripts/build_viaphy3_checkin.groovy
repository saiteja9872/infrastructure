// this pipeline script is run from the build_viaphy3_checkin Jenkins job viasat at
// preprod01.naw03.jenkins.viasat.com/job/Mach3_Jenkins/job/Mach3_UT/job/UT_DEV/job/build_viaphy3_checkin

node("vcalfutd05") {
    
    dir ("/home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_viaphy3_checkin"){
        stage("sync perforce for checkin job") {

            checkout (
                changelog: false,
                scm:
                    perforce (
                        credential: 'fb8f511e-c90f-40f2-9075-2e7dbe8ca2f9',
                        populate:
                            forceClean (
                                have: false,
                                parallel: [enable: true, minbytes: '1024', minfiles: '1', threads: '4'],
                                quiet: true
                            ),
                            workspace:
                                manualSpec (
                                    charset: 'none',
                                    cleanup: false,
                                    name: 'jenkins-${NODE_NAME}-${JOB_NAME}',
                                    pinHost: false,
                                    spec:
                                        clientSpec (
                                            allwrite: false,
                                            backup: true,
                                            changeView: '',
                                            clobber: true,
                                            compress: false,
                                            line: 'LOCAL',
                                            locked: false,
                                            modtime: false,
                                            rmdir: true,
                                            serverID: '',
                                            streamName: '',
                                            type: 'WRITABLE',
                                            view: '''//LeapFrog/Technical/Software/code/ut/dev/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/...
                                                    //LeapFrog/Technical/Software/code/common/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/common/...
                                                    //LeapFrog/Technical/Software/code/common/VOS/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/common/VOS/...
                                                    //LeapFrog/Technical/Software/code/common/vOS/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/common/vOS/...
                                                    //Afterburner/Technical/Software/code/common/patdist_client/v2.0/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/common/patdist_client/v2.0/...
                                                    //Afterburner/Technical/Software/code/common/AbTypes.h //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/common/AbTypes.h
                                                    //LeapFrog/Technical/Software/code/ut/dev/platform/apps/f5/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/platform/apps/f5_stub/...
                                                    //Mach3/Technical/Software/ut/dev/platform/apps/f5/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/platform/apps/f5/...
                                                    //LeapFrog/Technical/Software/code/ut/dev/core/f5/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/core/f5_stub/...
                                                    //Mach3/Technical/Software/ut/dev/core/f5/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/core/f5/...
                                                    //Mach3/Technical/Software/ut/vp3_linux/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/vp3_linux/...
                                                    //Mach3/Technical/Software/ptria/blackbird/dsp/firmware/sdp/binaries/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/dev/core/f5/sdp/binaries/...
                                                    //Mach3/Technical/ASIC/ViaPHY3/firmware/... //jenkins-${NODE_NAME}-${JOB_NAME}/LeapFrog/Technical/Software/code/ut/vp3_firmware/...'''
                                        )
                                )
                    )
            )
            sh "ls -la"
            sh "ls -la /home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_viaphy3_checkin/LeapFrog/Technical/Software/code/ut/dev/core/f5/sdp/binaries/"
        }

        stage("pull git repo for checkin job") {

            dir('jenkins') {
                git (
                    branch: '${git_branch}',
                    credentialsId: 'svc-git-ut-jenkins-token',
                    url: 'https://git.viasat.com/BBC-Term/infrastructure.git'
                )
            }
        }

        stage("run bash script to build blackbird platform for checkin job") {

            withCredentials (
                [
                    usernamePassword (
                        credentialsId: 'fb8f511e-c90f-40f2-9075-2e7dbe8ca2f9',
                        passwordVariable: 'P4PASSWD',
                        usernameVariable: 'P4USER'
                    ),
                    usernamePassword (
                        credentialsId: 'svc-git-ut-jenkins-token',
                        passwordVariable: 'GIT_PASS',
                        usernameVariable: 'GIT_USERNAME'
                    )
                ]
            ) {
                withEnv(['WORKSPACE=/home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_viaphy3_checkin']) {
                    sh '''export OPENWRT_BUILD_SUBTARGET="blackbird"
                        export OPENWRT_BUILD_PROFILES="${PROFILES}"
                        export P4CLIENT="jenkins-${NODE_NAME}-${JOB_NAME}"
                        export P4PORT="ssl:perforcesb.viasat.com:1666"
                        pwd
                        ls -la
                        bash -ex ./jenkins/mach3-jenkins/jenkins_build_bbird_platform_script.sh'''
                }
            }
        }

        stage("update build name for checkin job") {

            script {
                def buildVersion = readFile(file: 'openwrt/jenkins_build_version.txt')
                currentBuild.displayName = "#${BUILD_NUMBER}_" + buildVersion
            }
        }
    }
}