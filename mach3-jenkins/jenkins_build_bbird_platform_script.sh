#!/usr/bin/env bash
set -x
set -e

export LM_LICENSE_FILE=/opt/license/
export ENG_REL="CICD"
export VERSION_PATH=LeapFrog/Technical/Software/code/ut/dev
export VERSION_FILE=PRODUCT_VERSION.txt
export VERSION_FILE_BBIRD=PRODUCT_VERSION_BBIRD.txt
export P4CLIENT=${P4CLIENT//[\/]/-}

FILENAME=$VERSION_FILE
# Avoid echo'ing all the commands in the bashrc file
set +x
echo "Sourcing ~/.bashrc"
source ~/.bashrc
set -x
echo "Building for subtarget: $OPENWRT_BUILD_SUBTARGET with following profiles: $OPENWRT_BUILD_PROFILES"

# Set up git pass for authentication with git since ssh was not allowed on vcalfutd05
set_up_git_pass()
{
    echo -ne "echo $GIT_PASS" > ${WORKSPACE}/git-askpass-helper.sh
    chmod 700 ${WORKSPACE}/git-askpass-helper.sh
    export GIT_ASKPASS=${WORKSPACE}/git-askpass-helper.sh
}

# Sets up feeds.conf
set_up_feeds()
{
    P4_JENKINS_WORKSPACE=${WORKSPACE}/LeapFrog/Technical/Software/code
    echo "" > feeds.conf
    echo "src-git ut_feed https://$GIT_USERNAME@git.viasat.com/BBC-Term/ut_feed.git^$UT_FEED_HASH" >> feeds.conf
    echo 'src-link ut_cloc '"$P4_JENKINS_WORKSPACE"'/common' >> feeds.conf
    echo 'src-link ut_loc  '"$P4_JENKINS_WORKSPACE"'/ut/dev' >> feeds.conf
    echo 'src-link vp3_loc '"$P4_JENKINS_WORKSPACE"'/ut/vp3_linux' >> feeds.conf
    echo 'src-link vp3_floc '"$P4_JENKINS_WORKSPACE"'/ut/vp3_firmware' >> feeds.conf
    cat feeds.conf.default >> feeds.conf
}

# Sets up P4 parts of the changelog
set_up_p4_changelist()
{
    p4_dir=$1
    prev_p4_cl_file=$2
    cur_p4_cl=$3
    changelog_file=$4
    p4_file_spec=$5

    if [ -f "$prev_p4_cl_file" ]; then
        echo "$prev_p4_cl_file exists."
    else
        echo "$prev_p4_cl_file does not exist."
        echo "No Peforce changes will be added until next build"
        echo $cur_p4_cl > $prev_p4_cl_file
    fi
    read prev_p4_cl < $prev_p4_cl_file
    echo "Old P4 CL is $prev_p4_cl"
    echo "Current P4 CL is $cur_p4_cl"

    let prev_p4_cl=$prev_p4_cl+1

    # Get p4 changes
    if [ "$p4_dir" != "dev" ]; then
        echo -e "#${p4_dir} Changes" >> $changelog_file
    fi
    p4 changes -l "$p4_file_spec"@$prev_p4_cl,$cur_p4_cl | sed '/^$/ d'| awk -v clist="Change $cur_p4_cl" -v awk_bld=${UT_VERSION} '{print $0}' >> $changelog_file

    # Remove Jenkins lines from file
    sed -i '/p4svc_ut_jenkins/d' $changelog_file
    sed -i '/Jenkins changed version to/d' $changelog_file

    # Update old perforce cl
    echo $cur_p4_cl > $prev_p4_cl_file
    echo "" >> $changelog_file
    cat $changelog_file
}

# Sets up git parts of the changelog
set_up_git_changelog()
{
    git_repo=$1
    prev_hash_file=$2
    cur_hash=$3
    changelog_file=$4

    if [ -f "$prev_hash_file" ]; then
        echo "$prev_hash_file exists."

    else
        echo "$prev_hash_file does not exist."
        echo "No Openwrt changes will be added until next build"
        echo $cur_hash > $prev_hash_file
    fi
    read prev_hash < $prev_hash_file
    echo "Old $git_repo hash is $prev_hash"
    echo "Current $git_repo hash is $cur_hash"
    
    echo $cur_hash > $prev_hash_file

    echo -e "#${git_repo} Changes" >> $changelog_file
    if [[ "$cur_hash" == "$prev_hash" ]]; then
        echo "No new ${git_repo} updates"
    else
        changes=$(git log --pretty=format:"Change %h on %ad by %an%n%x09%s" --date=short $prev_hash..$cur_hash)
        if [ -n "$changes" ]; then
            echo "$changes" >> $changelog_file
        fi
    fi
    echo "" >> $changelog_file

    #Update old hash
    cat $changelog_file
}

# Gets the current P4 CL for a spec
get_current_p4_cl()
{
    p4_spec=$1
    cl=$(p4 changes -m 1 -s submitted $p4_spec#have | awk '{print $2}')
    echo "$cl"
}

# Checks if a subtarget is a real hardware type
is_subtarget_real_hardware()
{
    subtarget=$1
    declare -a simulation_platforms=("protium1" "protium2" "protium3" "palladium1" "palladium2" "palladium3")
    for sim_target in "${simulation_platforms[@]}"
    do
        if [ "$sim_target" == "$subtarget" ]; then
            echo "1"
            return
        fi
    done
    echo "0"
}

# Configure a build with the profile and run make
configure_build_profile()
{
    local profile="$1"
    ./target/linux/viaphy3/prepare.sh $OPENWRT_BUILD_SUBTARGET $profile
    set +e

    pwd
    make -j5 V=w 2> error.log
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        cat error.log
        grep -m 1 -B 20 -n "^make.*\*\*\*" error.log
        echo "Profile: $profile failed to build!"
        exit 1
    fi
    set -e
}

pwd
ls ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/
DEV_P4_SPEC="//LeapFrog/Technical/Software/code/ut/dev/..."

# Sync dev to P4 label so we get the same workspace that ran during the unittests
cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev
echo $P4PASSWD | p4 -u $P4USER login
p4 sync //${P4CLIENT}/LeapFrog/Technical/Software/code/ut/dev...@JenkinsUtDev > /dev/null
CURR_P4_CL_DEV=$(p4 changes -m 1 -s submitted @JenkinsUtDev | awk '{print $2}')

echo "Current P4 CL for dev is $CURR_P4_CL_DEV"
echo "DEBUG: Version contents"
cat ${WORKSPACE}/$VERSION_PATH/$VERSION_FILE

# Sync version files
cd ${WORKSPACE}
p4 sync -f $VERSION_PATH/$VERSION_FILE
p4 sync -f $VERSION_PATH/$VERSION_FILE_BBIRD

# Sync any MACH3 code here

# Sync f5, sdp-fw changes together since they are under the same directory
p4 sync -f //${P4CLIENT}/LeapFrog/Technical/Software/code/ut/dev/core/f5/... > /dev/null
cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev/core/f5


# Get the latest P4 CL
SDP_FW_P4_SPEC="//Mach3/Technical/Software/ptria/blackbird/dsp/firmware/sdp/binaries/..."
CURR_P4_CL_SDPFW=$(get_current_p4_cl $SDP_FW_P4_SPEC )
echo "Current sdp fw CL is $CURR_P4_CL_SDPFW"

pwd
cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev
# Run make distclean since force sync'ing from perforce take 10-15 min
make distclean MODE=bbird

# Set version number values
COMPONENT=`awk '/Component/ { print $2 }' $FILENAME`
MAJOR=`awk '/Major/ { print $2 }' $FILENAME`
MINOR=`awk '/Minor/ { print $2 }' $FILENAME`
BUILD=`awk '/Build/ { print $2 }' $FILENAME`
MICRO=`awk '/Micro/ { print $2 }' $FILENAME`
NANO=`awk '/Nano/ { print $2 }' $FILENAME`

echo "Current UT version is $MAJOR.$MINOR.$MICRO.$NANO.$BUILD"
UT_VERSION=$MAJOR.$MINOR.$MICRO.$NANO.$BUILD

OPENWRT_HASH=`awk -F 'openwrt_hash=' '{print $2}' $VERSION_FILE_BBIRD | tr -d '\n'`
UT_FEED_HASH=`awk -F 'ut_feed_hash=' '{print $2}' $VERSION_FILE_BBIRD | tr -d '\n'`
echo "Current openwrt hash is $OPENWRT_HASH"
echo "Current ut_feed hash is $UT_FEED_HASH"

ls -ltr ${WORKSPACE}
cd ${WORKSPACE}
set_up_git_pass

# Check if openwrt dir exists, otherwise clone the repo
# Jenkins sets umask to 027 so we cannot use the git scm plugin since it will clone the repo with the wrong permissions
if [ ! -d "${WORKSPACE}/openwrt" ]; then
    echo "OpenWrt repo does not exist, cloning"
    git clone https://git.viasat.com/BBC-Term/openwrt.git openwrt
fi

# Fetch and checkout the git tag set by the unittests job
cd ${WORKSPACE}/openwrt

git fetch -f -t
git checkout -f JenkinsUtDev
# Debug log
git log -1

set_up_feeds
cat feeds.conf

./scripts/feeds update -a && ./scripts/feeds install -a

# Clean the artifacts from the old run but keep the toolchain
pwd
if [ -d "build_dir/" ]; then
    ls build_dir/
fi
# Set the correct target so openwrt cleans correctly
first_profile=$(echo $OPENWRT_BUILD_PROFILES | head -n1 | cut -d " " -f1)
./target/linux/viaphy3/prepare.sh $OPENWRT_BUILD_SUBTARGET $first_profile
make download V=w
make clean V=sc

if [ -d "build_dir/" ]; then
    ls build_dir/
fi
# Update build name to have UT version in name
JENKINS_BUILD_VERSION_FILE="${WORKSPACE}/openwrt/jenkins_build_version.txt"

# Create version file for Jenkins build
echo $UT_VERSION > $JENKINS_BUILD_VERSION_FILE

# Delete old artifacts
rm -rf "images/"

# Loop through each profile and build it
for profile in ${OPENWRT_BUILD_PROFILES}; do

    configure_build_profile "$profile"
    ls images/

    # Generate meta data information for non simulation platforms (real hardware) only
    is_real=$(is_subtarget_real_hardware "$OPENWRT_BUILD_SUBTARGET")
    if [ "$is_real" = "0" ]; then
        ./bin/targets/viaphy3/"$OPENWRT_BUILD_SUBTARGET"-glibc/openwrt-viaphy3-"$OPENWRT_BUILD_SUBTARGET"-Default-squashfs-image-metadata.sh
    fi

    ##### Create directory to store build artifacts #####
    cd images/
    ls
    build_folder_name=$(ls | sed 's/\$//' | grep "$OPENWRT_BUILD_SUBTARGET-$profile\_")

    CURRENT_CHANGELOG_FILE="${WORKSPACE}/openwrt/images/$build_folder_name/${build_folder_name}_changelist.txt"

    # Set up change log file
    # Each profile will have its own changelog file and files to track perforce and git changes
    echo "Setting up date"
    printf -v date '%(%Y/%m/%d)T' -1
    echo "$date- Jenkins build $UT_VERSION" > $CURRENT_CHANGELOG_FILE
    echo "#Perforce Changes" >> $CURRENT_CHANGELOG_FILE

    ## Create changelog for Perforce ##
    echo "Setting up P4 changes"
    cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev/
    PREV_P4_CL_FILE="${WORKSPACE}/.oldP4change_${profile}"
    set_up_p4_changelist "dev" "$PREV_P4_CL_FILE" "$CURR_P4_CL_DEV" "$CURRENT_CHANGELOG_FILE" "$DEV_P4_SPEC"

    ## Openwrt changes ##
    cd ${WORKSPACE}/openwrt
    echo "Setting up OpenWrt changes"
    PREV_OPENWRT_HASH_FILE="${WORKSPACE}/.oldOpenwrtChange_${profile}"
    set_up_git_changelog "OpenWrt" "$PREV_OPENWRT_HASH_FILE" "$OPENWRT_HASH" "$CURRENT_CHANGELOG_FILE"

    ## ut_feed changes ##
    cd ${WORKSPACE}/openwrt/feeds/ut_feed
    echo "Setting up ut_feed changes"
    PREV_UT_FEED_HASH_FILE="${WORKSPACE}/.oldUtFeedChange_${profile}"
    set_up_git_changelog "ut_feed" "$PREV_UT_FEED_HASH_FILE" "$UT_FEED_HASH" "$CURRENT_CHANGELOG_FILE"

    ## add any new changes here ##

    # sdp fw changes
    cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev/core/f5/sdp/binaries/
    PREV_P4_CL_SPDFW_FILE="${WORKSPACE}/.oldP4sdpfwchange_${profile}"
    set_up_p4_changelist "sdp-fw" "$PREV_P4_CL_SPDFW_FILE" "$CURR_P4_CL_SDPFW" "$CURRENT_CHANGELOG_FILE" "$SDP_FW_P4_SPEC"

    # Go back to the openwrt directory to build next profile
    cd ${WORKSPACE}/openwrt
done

cd ${WORKSPACE}