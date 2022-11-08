// Script copied from
// https://jenkins-pp.viasat.com/job/Surfbeam_2_Jenkins/job/ut/job/ut_dev_ci_build_all_targets_pipeline/
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

pipeline {
    agent any

    // Parameters for the pipeline go here
    parameters {
        string(defaultValue: "", description: 'Sw version from make all job', name: 'UT_VERSION')
        string (
            defaultValue: "eng-g eng-y field-y factory-g",
            description: 'The profiles to build for each subtarget',
            name: 'PROFILES_TO_BUILD'
        )
    }

    // Test Execution
    stages {
        stage('Setup') {
            steps {
                sh 'echo "UT_VERSION = $UT_VERSION"'
                // initialize the pipeline fail flag
                script {
                    env.fail_flag = "False"
                }
            }
        }
        stage("Build All Platforms")
        {
            parallel {
                stage("Build ASIC") {
                    steps {
                        buildJob (
                            'build_asic',
                            "ASIC",
                            [string(name: 'PROFILES', value: "${params.PROFILES_TO_BUILD}"), string(name: 'git_branch', value: "${params.branchName}")],
                            false
                        )
                    }
                }
                stage("Build Blackbird XCVR") {
                    steps {
                        buildJob (
                            'build_blackbird_xcvr',
                            "Blackbird",
                            [string(name: 'PROFILES', value: "${params.PROFILES_TO_BUILD}"), string(name: 'git_branch', value: "${params.branchName}")],
                            false
                        )
                    }
                }
            }
        }
        stage("Build FSBL") {
            steps {
                buildJob('build_fsbl', "FSBL", [string(name: 'git_branch', value: "${params.branchName}")], false)
            }
        }
        stage("Validation") { // check the pipeline flag and fail/pass the pipeline accordingly
            steps {
                script {
                    println("Pipeline Fail Flag:" + env.fail_flag)
                    if (env.fail_flag.contains("True")) {
                        currentBuild.result = 'FAILURE' // of FAILURE
                        error("Pipeline failed")
                        echo "Pipeline failed"
                        sh "exit 1"
                    }
                    else {
                        echo "Pass"
                        // PIPELINE passed, publish all builds
                        buildJob (
                            'publish_blackbird_to_artifactory',
                            'Publish FSBL to artifactory',
                            [   string(name: 'branchName', value: "${params.branchName}"),
                                string(name: 'SUBTARGET', value: "fsbl"),
                                string(name: 'BUILD_DIR', value: "/home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_fsbl/Mach3/Technical/ASIC/ViaPHY3/firmware/SecureBootROM/fsbl/archive"),
                                string(name: 'PATTERNS', value: ".")
                            ],
                            false
                        )
                        buildJob (
                            'publish_blackbird_to_artifactory',
                            'Publish SSBl to artifactory',
                            [   string(name: 'branchName', value: "${params.branchName}"),
                                string(name: 'SUBTARGET', value: "ssbl"),
                                string(name: 'BUILD_DIR', value: "/home/jenkins-ldap-svc/workspace/Mach3_Jenkins/Mach3_UT/UT_DEV/build_ssbl/Mach3/Technical/ASIC/ViaPHY3/firmware/SecureBootROM/packages/SecondStage/archive"),
                                string(name: 'PATTERNS', value: ".")
                            ],
                            false
                        )
                    }
                }
            }
        }
    }

    // Wrap-up actions, currently just emails, add in post to archives
    post {
        success {
            script {
                if (
                    currentBuild.previousBuild != null
                    && currentBuild.previousBuild.result != 'SUCCESS'
                ) {
                    // Disable slack notification and do email only for now
                    emailext (
                        subject: "Pipeline Stable '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
                        mimeType: 'text/html',
                        body: """Build is back to normal (SUCCESS): ${env.BUILD_URL}""",
                        to: "bbird-sw@viasat.com"
                    )
                }
            }
            sh 'echo "$UT_VERSION" > $WORKSPACE/latest.properties'
            archive (includes: 'latest.properties')
            echo "Pipeline PASS"
        }
        failure {
            echo "Pipeline FAIL"
            emailext (
                subject: "FAILURE: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
                mimeType: 'text/html',
                recipientProviders: [[$class: 'CulpritsRecipientProvider']],
                body: """<p>FAILURE: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]':</p>
                    <p>Check console output at "<a href="${env.BUILD_URL}">${env.JOB_NAME} [${env.BUILD_NUMBER}]</a></p>
                    ${buildResultsMap.each{ k, v -> println "<p>${k} ---> ${v}<br></p>" }}""",
                to: "bbird-sw@viasat.com"
            )
        }
        always {
            script {
                println ("Build All Pipeline Result Summary")
                buildResultsMap.each{ k, v -> println "${k} ----> ${v}" }
                currentBuild.displayName = "#${env.BUILD_NUMBER}_$UT_VERSION"
            }
        }
    }
}
