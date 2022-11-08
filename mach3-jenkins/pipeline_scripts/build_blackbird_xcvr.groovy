// this pipeline script is run from the build_blackbird_xcvr Jenkins job at
// preprod01.naw03.jenkins.viasat.com/job/Mach3_Jenkins/job/Mach3_UT/job/UT_DEV/job/build_blackbird_xcvr

import groovy.transform.Field
@Field Map buildResultsMap = [:]

// Runs a job and stores the result with the url for the job logs
def buildJob(jobName, stageName, param, propogate_param) {
    // create a stage for each job
    // assign a param to store all the build job properties
    slavejob = build job: jobName, parameters: param, propagate: propogate_param
    job_result = slavejob.absoluteUrl + " --- " + slavejob.result
    if(slavejob.result == 'FAILURE') {
        echo "$jobName job failed"
        env.fail_flag = "True" // set the pipeline fail flag
    }
    // update the dict with the result
    script {
        println(stageName + " ---> " + job_result)
        buildResultsMap.put(stageName, job_result)
    }
}


node("vcalfutd05") {

    stage("sync perforce") {
        checkout (
            perforce (
                credential: 'fb8f511e-c90f-40f2-9075-2e7dbe8ca2f9',
                populate: syncOnly(
                    force: true,
                    have: true,
                    modtime: false,
                    parallel: [enable: false, minbytes: '1024', minfiles: '1', threads: '4'],
                    pin: '',
                    quiet: true,
                    revert: false
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
                                    clobber: true,
                                    compress: false,
                                    line: 'LOCAL',
                                    locked: false,
                                    modtime: false,
                                    rmdir: true,
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
        sh "ls -la "
        sh "ls -la /home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_blackbird_xcvr/LeapFrog/Technical/Software/code/ut/dev/core/f5/sdp/binaries/"
    }

    stage("pull git repo") {
        dir('jenkins') {
            git (
                branch: '${git_branch}',
                credentialsId: 'svc-git-ut-jenkins-token',
                url: 'https://git.viasat.com/BBC-Term/infrastructure.git'
            )
        }
    }

    stage("run bash script to build blackbird platform") {
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
        )
        {
            sh '''export OPENWRT_BUILD_SUBTARGET="blackbird"
                export OPENWRT_BUILD_PROFILES="${PROFILES}"
                export P4CLIENT="jenkins-${NODE_NAME}-${JOB_NAME}"
                export P4PORT="ssl:perforcesb.viasat.com:1666"
                pwd
                ls -la
                bash -ex ./jenkins/mach3-jenkins/jenkins_build_bbird_platform_script.sh'''
        }
    }

    stage("publish images to artifactory") {
        script {
            buildJob (
                'publish_blackbird_to_artifactory',
                'Publish Images to Artifactory',
                [   string(name: 'branchName', value: "${params.git_branch}"),
                    string(name: 'SUBTARGET', value: "blackbird"),
                    string(name: 'BUILD_DIR', value: "${WORKSPACE}/openwrt/images"),
                    string(name: 'PATTERNS', value: "\\(eng\\|factory\\|field\\)-\\(g\\|y\\)_")
                ],
                false
            )
        }
    }

    stage("build bundle files within the same workspace"){
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
        )
        {
            sh '''export OPENWRT_BUILD_SUBTARGET="blackbird"
                export OPENWRT_BUILD_PROFILES="${PROFILES}"
                export P4CLIENT="jenkins-${NODE_NAME}-${JOB_NAME}"
                export P4PORT="ssl:perforcesb.viasat.com:1666"
                pwd
                ls -la
                bash -ex ./jenkins/mach3-jenkins/build_bbird_bundle_script.sh'''
        }
    }

    stage("publish bundles to artifactory") {
        script {
            buildJob (
                'publish_blackbird_to_artifactory',
                'Publish Bundles to Artifactory',
                [   string(name: 'branchName', value: "${params.git_branch}"),
                    string(name: 'SUBTARGET', value: "blackbird"),
                    string(name: 'BUILD_DIR', value: "${WORKSPACE}/openwrt/images"),
                    string(name: 'PATTERNS', value: "\\-bundle_")
                ],
                false
            )
        }
    }

    stage("update build name") {
        script {
            def buildVersion = readFile(file: 'openwrt/jenkins_build_version.txt')
            currentBuild.displayName = "#${BUILD_NUMBER}_" + buildVersion
        }
    }
}
