// this pipeline script is run from the build_ssbl Jenkins job at
// preprod01.naw03.jenkins.viasat.com/job/Mach3_Jenkins/job/Mach3_UT/job/UT_DEV/job/build_ssbl

node("vcalfutd05") {

    stage("sync perforce") {
        checkout (
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
                                    clobber: true,
                                    compress: false,
                                    line: 'LOCAL',
                                    locked: false,
                                    modtime: false,
                                    rmdir: false,
                                    type: 'WRITABLE',
                                    view: '''//Mach3/Technical/ASIC/ViaPHY3/firmware/SecureBootROM/... //jenkins-${NODE_NAME}-${JOB_NAME}/Mach3/Technical/ASIC/ViaPHY3/firmware/SecureBootROM/...
                                             //Mach3/Technical/ASIC/ViaPHY3/proc/script/act/... //jenkins-${NODE_NAME}-${JOB_NAME}/Mach3/Technical/ASIC/ViaPHY3/proc/script/act/...
                                             //Mach3/Technical/ASIC/ViaPHY3/src/act/... //jenkins-${NODE_NAME}-${JOB_NAME}/Mach3/Technical/ASIC/ViaPHY3/src/act/...'''
                                )
                        )
            )
        )
    }

    stage ("pull git repo") {
        dir('mach3-jenkins') {
            checkout (
                scm: [
                    $class: 'GitSCM',
                    branches: [[name: '*/master']],
                    extensions: [[
                        $class: 'SparseCheckoutPaths',
                        sparseCheckoutPaths: [[path: 'mach3-jenkins/vault_app_roles/sdp-prod-ut-vp3-jenkins']]
                    ]],
                    userRemoteConfigs: [[
                        credentialsId: 'svc-git-ut-jenkins-token',
                        url: 'https://git.viasat.com/BBC-Term/infrastructure.git'
                    ]]
                ]
            )
            sh "mv mach3-jenkins/* ."
            sh "rm -rf mach3-jenkins"
        }
    }

    stage("make ssbl variations") {
        withCredentials (
            [
                string(credentialsId: 'sdp-prod-ut-vp3-jenkins_secret-id', variable: 'VAULT_SECRET_ID'),
            ]
        )
            {
                sh '''echo "Workspace is ${WORKSPACE}"

                    # ViaPHY3 stuff
                    export ASIC_DIR=${WORKSPACE}/Mach3/Technical/ASIC/ViaPHY3
                    export ROM_DIR=${ASIC_DIR}/firmware/SecureBootROM

                    # Properties for downstream build
                    echo -n "${ROM_DIR}/packages/SecondStage" > ssbl_path_param.txt

                    # ARM development Studio Env Variables
                    export ADS_BASE_DIR=/opt/eda/arm/developmentstudio-2020.0
                    export ARMCLANG_VER=ARMCompiler6.14
                    export ARM_PATH=${ADS_BASE_DIR}/sw/${ARMCLANG_VER}/bin/
                    export PATH="$ARM_PATH:${ADS_BASE_DIR}/bin:$PATH"
                    export ARMLMD_LICENSE_FILE=27020@vcalic04
                    export ARM_TOOL_VARIANT=gold
                    export ARM_PRODUCT_PATH=${ADS_BASE_DIR}/sw/mappings/
                    export LM_LICENSE_FILE=5282@vcalic04:1709@vcalic02:27000@vcalic14:2100@vcalic14:1700@vcalic17:27000@vohcaemlyn01:27010@vcalic04:1709@lm-synopsys

                    export VAULT_ROLE_ID=`cat mach3-jenkins/vault_app_roles/sdp-prod-ut-vp3-jenkins | tr -d \'\\n\'`
                    export VAULT_ADDR="https://vault.security.viasat.io:8200"
                    export VAULT_CACERT=${VAULT_INTERMEDIATE_PEM}
                    export VAULT_TOKEN=`vault write auth/approle/login role_id=${VAULT_ROLE_ID} secret_id=${VAULT_SECRET_ID} | grep \'token \' | awk \'{print $2}\'`

                    # Use to differentiate SSBL builds with the same version
                    export JENKINS_BUILD_NUMBER="_${BUILD_NUMBER}"

                    cd ${ROM_DIR}

                    make ssbl_variations BLD_REL=cicd BLD_NO=1'''
            }
    }

    stage("update build name") {
        def buildVersion = readFile (
                file: 'Mach3/Technical/ASIC/ViaPHY3/firmware/SecureBootROM/packages/SecondStage/ssbl_version.txt'
            )
        currentBuild.displayName = "#${BUILD_NUMBER}_" + buildVersion
    }

    stage('kick off build_scpfw job') {
        sh "pwd"
        sh "ls -la"
        def ssbl_path_param = readFile (file: 'ssbl_path_param.txt')
        build (
            job: 'build_scpfw',
            parameters: [string (name: 'SSBL_PATH_PARAM', value: ssbl_path_param)]
        )
    }
}
