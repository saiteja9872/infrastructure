#!/usr/bin/env bash
set -e
set +x

export ARTIFACTORY_ROOT_LOC=https://artifactory.viasat.com/artifactory
export OLD_LOC=mach3-generic-dev/terminal/viaphy3
export ARTIFACTORY_DEV_G_LOC=terminals-viaphy3-dev-g
export ARTIFACTORY_DEV_Y_LOC=terminals-viaphy3-dev-y
export ARTIFACTORY_PREPROD_G_LOC=terminals-viaphy3-preprod-g
export ARTIFACTORY_PREPROD_Y_LOC=terminals-viaphy3-preprod-y
export ARTIFACTORY_PROD_G_LOC=terminals-viaphy3-prod-g

export WORKSPACE_DIR=${PWD}

# Push file and checksums to artifactory
push_file_to_artifactory()
{
    file=$1
    dest_path=$2
    # Calculate file checksums
    sha256=$(openssl dgst -sha256 $file | sed 's/^SHA256.*= //')
    sha1=$(openssl dgst -sha1   $file | sed 's/^SHA1.*= //')
    md5=$(openssl dgst -md5    $file | sed 's/^MD5.*= //')
    echo "Uploading $file to $dest_path/"
    # Upload this file to Artifactory: JSON output is suppressed, and only
    # the simple progress bar shown (which doesn't display the filename)
    output=$(/usr/local/bin/curl -w "\n%{http_code}" \
    --user $GIT_USER:$GIT_PASS \
    --header "X-Checksum-Md5:${md5}" \
    --header "X-Checksum-Sha1:${sha1}" \
    --header "X-Checksum-Sha256:${sha256}" \
    --config "/home/jenkins-ldap-svc/.curl_artifactory" \
    --retry 3 \
    --retry-all-errors \
    --retry-delay 30 \
    --max-time 120 \
    --upload-file $file \
    "$dest_path/")
    res=$?

    if [[ "$res" != "0" ]]; then
        echo -e "$output"
        exit $res
    fi

    if [[ $output =~ [^0-9]([0-9]+)$ ]]; then
        httpCode=${BASH_REMATCH[1]}
        body=${output:0:-${#httpCode}}
        #echo -e "$body"
        if (($httpCode < 200 || $httpCode >= 300)); then
            # Remove this is you want to have pure output even in case of failure:
            echo "Failure HTTP response code: ${httpCode}"
            exit 1
        fi
    else
        echo -e "$output"
        echo "Cannot get the HTTP return code"
        exit 1
    fi
}

# Push contents of directory to artifactory
push_dir_to_artifactory()
{
    dest_path=$1
    for file in *; do
        push_file_to_artifactory $file $dest_path
    done
    echo "Done pushing files into $dest_path"
}

# Set the folder name based on the current directory
set_dir_name()
{
    folder_name=${PWD##*/} 
    echo $folder_name
}

# Loops through all possible profiles and builds in those profiles 
# and publishes them to artifactory
push_profile_image()
{
    pwd
    ls
    subtarget=$1
    patterns=$2
    echo "Patterns are ${patterns}"
    builds=$(ls | grep -e $patterns)
    echo "builds are $builds"
    for build in $builds; do
        if [ -d "$build" ]; then
            echo "$1 $build directory found. Working in $build/"
            cd "$build"
            purge_loc=""
            if [[ $build == *"eng-g_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/latest-build"
            elif [[ $build == *"eng-g-bundle_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/latest-bundle/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/bundle/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/$subtarget/eng-g/latest-bundle"
            elif [[ $build == *"factory-g_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/latest-build"
            elif [[ $build == *"factory-g-bundle_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/latest-bundle/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/bundle/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/$subtarget/factory-g/latest-bundle"
            elif [[ $build == *"eng-y_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/latest-build"
            elif [[ $build == *"eng-y-bundle_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/latest-bundle/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/bundle/$build"
                purge_loc="/$ARTIFACTORY_DEV_Y_LOC/$subtarget/eng-y/latest-bundle"
            elif [[ $build == *"field-y_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/latest-build"
            elif [[ $build == *"field-y-bundle_"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/latest-bundle/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/bundle/$build"
                purge_loc="/$ARTIFACTORY_DEV_Y_LOC/$subtarget/field-y/latest-bundle"
            elif [[ $build == *"ssbl"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/vp3-ssbl/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/vp3-ssbl/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/vp3-ssbl/latest-build"
            elif [[ $build == *"fsbl"* ]] && [[ $build == *"cicd"* ]]; then
                dest_path="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/vp3-fsbl/latest-build/$build"
                dest_path_nightly="$ARTIFACTORY_ROOT_LOC/$ARTIFACTORY_DEV_G_LOC/vp3-fsbl/build/$build"
                purge_loc="/$ARTIFACTORY_DEV_G_LOC/vp3-fsbl/latest-build"
            else                     
                echo "Correct build not specified. Skipping $build"
                continue
            fi  
            echo "============================="
            pwd
            echo "Pushing $build to $dest_path and $dest_path_nightly"
            echo "============================="
            if !([[ -z $purge_loc ]]); then
                echo "purging files in $purge_loc"
                ${WORKSPACE}/mach3-jenkins/artifactory_scripts/artiPurgeTool.py $purge_loc -c 0
                echo "Finished purging"
            fi
                
            push_dir_to_artifactory $dest_path
            push_dir_to_artifactory $dest_path_nightly

            cd ..
            pwd
        fi
    done  
}

#### Copy non secure builds ####
if [ -d ${BUILD_DIR} ]; then
    echo "${SUBTARGET} builds. Working in ${BUILD_DIR}"
    ( cd ${BUILD_DIR} ; push_profile_image $SUBTARGET $PATTERNS)
fi
