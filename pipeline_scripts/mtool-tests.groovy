node 
{
    def failedTests = []
    stage("Get branch and set up testing environment on target"){
        build job: 'set-up-mtool-tests', parameters: [
            string(name: 'target', value: "${target}"), 
            string(name: 'ref', value: "${sha1}"),
            string(name: 'subdir', value: "${checkout_dir}"),
            string(name: 'test_dir', value: "${test_dir}"),
            string(name: 'venv_dir', value: "${venv_dir}")
        ]
    }
    parallel( 
        "Functional Tests": {
            stage("Run Test Driver Wrapper on mtool application"){
                def mtoolPath = "${test_dir}" + "/" + "${checkout_dir}" + "/modem_tool/modem_tool.py"
                def jobRes = build job: 'run-app-suite-functional-tests', propagate: false, parameters: [
                    string(name: 'target', value: "${target}"), 
                    string(name: 'app', value: "mtool"),
                    string(name: 'test', value: "${test}"),
                    string(name: 'macs', value: "${macs}"),
                    string(name: 'modem_types', value: "${modem_types}"),
                    string(name: 'mtool_bin', value: "${mtoolPath}"),
                    string(name: 'test_dir', value: "${test_dir}"),
                    string(name: 'venv_dir', value: "${venv_dir}"),
                    string(name: 'checkout_dir', value: "${checkout_dir}")
                ]
                if ("${jobRes.result}" != "SUCCESS"){
                    failedTests.push("Functional-Tests")
                    def stageRes = "FAILURE"
                    if ("${jobRes.result}" == "UNSTABLE"){
                        stageRes = "UNSTABLE"
                    }
                    catchError(buildResult: "SUCCESS", stageResult: "${stageRes}") {
                        println "Test setup error."
                        sh "exit 2"
                    }
                }                
            }
        }, 
        "Unit Tests": {
            stage("Run unit tests on mtool application"){
                echo "Call job placeholder"
            }
        }
    )
    stage("Clean up test environment"){
        // Jenkins pipeline parameter
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
        if (failedTests.size() > 0){
            currentBuild.result = "FAILURE"
        }
    }
}
