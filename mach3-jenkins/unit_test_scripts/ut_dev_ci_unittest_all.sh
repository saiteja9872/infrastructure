#!/bin/bash

# Set variables
export P4PORT=${P4_PORT}
export P4CLIENT=${P4_CLIENT}
export P4USER=${P4_USER}
export P4PASSWD=${P4_TICKET}
export LM_LICENSE_FILE=/opt/license/
export VERSION_PATH=LeapFrog/Technical/Software/code/ut/dev
export VERSION_FILE=PRODUCT_VERSION.txt


# OpenWrt variables
export http_proxy="vcasquidp01.hq.corp.viasat.com:8080"
export https_proxy="vcasquidp01.hq.corp.viasat.com:8080"
export no_proxy="viasat.com"
export OPENWRT_EXT_HOST_DIR="/opt/openwrt-sdk-viaphy3-blackbird_gcc-8.4.0_glibc.Linux-x86_64/staging_dir/host"
# Same name as p4 label
export GIT_TAG_OPENWRT="JenkinsUtDev"


FILENAME=$VERSION_FILE
versionChanged=0

# Set up git password for pushing tag to openwrt.git repo
set_up_git_pass()
{
	echo -ne "echo $GIT_PASS" > git-askpass-helper.sh
	chmod 700 git-askpass-helper.sh
	export GIT_ASKPASS=./git-askpass-helper.sh
}

# Tag and push tag 
update_git_tag_openwrt()
{
	git tag -f $GIT_TAG_OPENWRT $1
	git push -f origin $GIT_TAG_OPENWRT

}

# Update feeds.conf to point to correct location
update_feeds_openwrt()
{
    P4_JENKINS_WORKSPACE=${WORKSPACE}/LeapFrog/Technical/Software/code
	sed -i -e 's/src-git ut_feed/#src-git ut_feed/' feeds.conf
	echo 'src-link ut_loc  '"$P4_JENKINS_WORKSPACE"'/ut/dev' >> feeds.conf
	echo 'src-link ut_cloc '"$P4_JENKINS_WORKSPACE"'/common' >> feeds.conf
	echo 'src-link ut_feed  '"${WORKSPACE}"'/ut_feed' >> feeds.conf
	cat feeds.conf
}

# Check if version number is valid
# param $1 - Old version number
# param $2 - New Version number
# return 1 - New version is valid
# return 2 - New Version is higher than max version
versionIsValid()
{
   if [ "$1" -ne "$2" ]
   then
      MAX_VERSION=65535

      if [ "$1" -gt "$MAX_VERSION" ]
      then
         versionChanged=2
      else
         versionChanged=1
      fi
   fi

   versionChanged=1
}

# Function that reads/edits version file
editProductVersion()
{
   if [ $# -ne 6 ]
   then
      echo "Invalid editProductVersion call" >&2
      exit 4
   fi
    sed -i 's/^Major *.*/Major       '"$1"'/' $6
    sed -i 's/^Minor *.*/Minor       '"$2"'/' $6
    sed -i 's/^Micro *.*/Micro       '"$3"'/' $6
    sed -i 's/^Nano *.*/Nano        '"$4"'/' $6
    sed -i 's/^Build *.*/Build       '"$5"'/' $6
}

get_openwrt_repo()
{
   cd ${WORKSPACE}
   if [ ! -d ${WORKSPACE}/openwrt ]; then
     echo "openwrt repo does not exist, cloning"
     git clone -b vp3-v20.XX https://svc_git_ut_jenkins:baf17cb7b385d81933e2433a5db3bfde5a150b80@git.viasat.com/BBC-Term/openwrt.git openwrt
   fi
}

get_ut_feed_repo()
{
   cd ${WORKSPACE}
   if [ ! -d ${WORKSPACE}/ut_feed ]; then
     echo "ut_feed repo does not exist, cloning"
     git clone https://svc_git_ut_jenkins:baf17cb7b385d81933e2433a5db3bfde5a150b80@git.viasat.com/BBC-Term/ut_feed.git ut_feed
   fi
}




pwd
cd LeapFrog/Technical/Software/code/ut/dev/automation
export PATH=$PATH:/usr/local/bin
./run_unit_tests_jenkins.sh
perforce_tests_exit_code=$?
if [ $perforce_tests_exit_code -ne 0 ]; then
    echo "ut/dev Unittests Failed!"
    exit 1
fi
#Calculate line coverage
    #Grab number of lines covered by unit tests
        coveredLines=0
        for x in `ls $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/unittest/results/coverage_report/*coverage.html`; do 
             fileCount=`cat $x | awk '/Lines:/ {getline; print}' | sed -n 's/.*>\([0-9][0-9]*\)<.*/\1/p'`
            coveredLines=`expr $coveredLines + $fileCount`
        done
        echo "Total number of lines unit tested: $coveredLines"
    #Find source files
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/ut_mac/ -name "*.c" > ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/ut_mac/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/klms/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/klms/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/root_fs/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/root_fs/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/secure_swdl/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/secure_swdl/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/ab/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/ab/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/afe/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/afe/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/blackbox_agent/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/blackbox_agent/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/hw/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/hw/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/macsim/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/macsim/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/ptria/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/ptria/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/specAn/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/specAn/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/statPush/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/statPush/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/TxBurst/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/TxBurst/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/umr/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/umr/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/utstat/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/utstat/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/viaphy/ -name "*.cpp" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/viaphy/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/macsim/ -name "*.c" >> ~/list_c
        find $WORKSPACE/LeapFrog/Technical/Software/code/ut/dev/platform/apps/macsim/ -name "*.cpp" >> ~/list_c
    #Prune unit test dirs/files
        cat ~/list_c | sed '/unittest/ d'> ~/newlist_c
    #Remove blank lines and comments, then count lines:
        total=0;for x in `cat ~/newlist_c`; do echo $x;t=`cat $x | sed '/^$/ d' | sed '/^\s*$/ d' |~/remccom3.sed|wc -l`; total=`expr $total + $t`;echo $total; done;
        echo "Total number of lines: $total"
        echo "Overall UT unit test line coverage: $coveredLines / $total = `echo $coveredLines/$total | bc -l`" | tee $WORKSPACE/unit_test_line_coverage.txt
        
        
# Run Unittests from OpenWrt for BBIRD
# Set up env and record hash for use later
get_openwrt_repo
openwrt_repo=$?
if ! get_openwrt_repo; then
   echo "OPENWRT REPO FAILED"
   exit 1
fi
cd ${WORKSPACE}/openwrt/
export openwrt_hash=$(git log --pretty=format:'%H' -n 1)

update_feeds_openwrt 
./scripts/feeds update -a ; ./scripts/feeds install -a
# Copy over tools so Jenkins doesn't have to build them
cp -R $OPENWRT_EXT_HOST_DIR/* staging_dir/host/

./target/linux/viaphy3/prepare.sh -e blackbird eng-g
# Compile linux kernel to get the headers needed by the components
make target/linux/compile -j8
# Run unittests from openwrt
make unittest V=sc
test_exit_code=$?
if [ $test_exit_code -ne 0 ]; then
    echo "Blackbird Unittests Failed!"
    exit 1
fi

# Record ut_feed hash used for unittests
get_ut_feed_repo
ut_feed_repo=$?
if [ $ut_feed_repo -ne 0 ]; then
   echo "UT_FEED REPO FAILED"
   exit 1
fi
cd ${WORKSPACE}/ut_feed
export ut_feed_hash=$(git log --pretty=format:'%H' -n 1)
echo $ut_feed_hash


# Get UT and BBIRD version files
cd ${WORKSPACE}/LeapFrog/Technical/Software/code/ut/dev/
pwd
FILENAME=PRODUCT_VERSION.txt
BBIRD_FILENAME=PRODUCT_VERSION_BBIRD.txt
# Sync version file and revert if still open
#/usr/local/bin/p4 -P $P4TICKET sync $FILENAME
#/usr/local/bin/p4 -P $P4TICKET revert $FILENAME
/usr/local/bin/p4 sync $FILENAME $BBIRD_FILENAME
/usr/local/bin/p4 revert $FILENAME $BBIRD_FILENAME

# Set version number values
UT_COMPONENT=`awk '/Component/ { print $2 }' $FILENAME`
UT_MAJOR=`awk '/Major/ { print $2 }' $FILENAME`
UT_MINOR=`awk '/Minor/ { print $2 }' $FILENAME`
UT_BUILD=`awk '/Build/ { print $2 }' $FILENAME`
UT_MICRO=`awk '/Micro/ { print $2 }' $FILENAME`
UT_NANO=`awk '/Nano/ { print $2 }' $FILENAME`
UT_NEW_BUILD=`expr $UT_BUILD + 1`
echo "Current UT version is $UT_MAJOR.$UT_MINOR.$UT_MICRO.$UT_NANO.$UT_NEW_BUILD"
UT_VERSION=$UT_MAJOR.$UT_MINOR.$UT_MICRO.$UT_NANO.$UT_NEW_BUILD
echo "UT_VERSION==$UT_VERSION" > version.out
UT_NEW_BUILD_NUMBER=`expr $BUILD_NUMBER + 8000`
echo "UT_VERSION_LABEL=$UT_NEW_BUILD_NUMBER" >> version.out

# Set BBIRD version number values
BBIRD_COMPONENT=`awk '/Component/ { print $2 }' $BBIRD_FILENAME`
BBIRD_MAJOR=`awk '/Major/ { print $2 }' $BBIRD_FILENAME`
BBIRD_MINOR=`awk '/Minor/ { print $2 }' $BBIRD_FILENAME`
BBIRD_BUILD=`awk '/Build/ { print $2 }' $BBIRD_FILENAME`
BBIRD_MICRO=`awk '/Micro/ { print $2 }' $BBIRD_FILENAME`
BBIRD_NANO=`awk '/Nano/ { print $2 }' $BBIRD_FILENAME`
BBIRD_NEW_BUILD=`expr $BBIRD_BUILD + 1`
echo "Current Blackbird version is $BBIRD_MAJOR.$BBIRD_MINOR.$BBIRD_MICRO.$BBIRD_NANO.$BBIRD_NEW_BUILD"
BBIRD_VERSION=$BBIRD_MAJOR.$BBIRD_MINOR.$BBIRD_MICRO.$BBIRD_NANO.$BBIRD_NEW_BUILD
echo "BBIRD_VERSION=$BBIRD_VERSION" >> version.out
BBIRD_NEW_BUILD_NUMBER=`expr $BUILD_NUMBER + 8000`
echo "BBIRD_VERSION_LABEL=$BBIRD_NEW_BUILD_NUMBER" >> version.out

# Check if new build version is valid
let newBuild=$UT_BUILD+1;
versionIsValid $newBuild $UT_BUILD 
if [ $versionChanged -eq 1 ]
then
	UT_BUILD=$newBuild
else
	echo "Build version out of bounds."
	exit 2
fi
UT_BUILD=$newBuild

# Open file and edit
#/usr/local/bin/p4 -P $P4TICKET edit $FILENAME || exit 3
/usr/local/bin/p4 edit $FILENAME $BBIRD_FILENAME || exit 3
editProductVersion $UT_MAJOR $UT_MINOR $UT_MICRO $UT_NANO $UT_BUILD $FILENAME


# Check if new build version is valid
let newBuild=$BBIRD_BUILD+1;
versionIsValid $newBuild $BBIRD_BUILD
if [ $versionChanged -eq 1 ]
then
	BBIRD_BUILD=$newBuild
else
	echo "Build version out of bounds."
	exit 2
fi
BBIRD_BUILD=$newBuild

# Update BBIRD version file
editProductVersion $BBIRD_MAJOR $BBIRD_MINOR $BBIRD_MICRO $BBIRD_NANO $BBIRD_BUILD $BBIRD_FILENAME
sed -i 's/^openwrt_hash=.*$/openwrt_hash='"$openwrt_hash"'/' $BBIRD_FILENAME
sed -i 's/^ut_feed_hash=.*$/ut_feed_hash='"$ut_feed_hash"'/' $BBIRD_FILENAME

DESCRIPTION="Jenkins changed version to UT.$UT_MAJOR.$UT_MINOR.$UT_MICRO.$UT_NANO.$UT_BUILD	See $BUILD_URL for details"
UT_VERSION=$UT_MAJOR.$UT_MINOR.$UT_MICRO.$UT_NANO.$UT_BUILD

## Build changelist
let PREVBUILD=$BUILD_NUMBER-1
echo $PREVBUILD
echo $UT_VERSION > /tftpboot/Release/CICD/.utversion
echo $DESCRIPTION > /tftpboot/Release/CICD/.description

ls -al
#cd LeapFrog/Technical/Software/code/ut/dev
#/usr/local/bin/p4 -P $P4TICKET tag -l JenkinsUtDev-$BUILD_NUMBER ...@$P4_CHANGELIST
/usr/local/bin/p4 tag -l JenkinsUtDev ...@$P4_CHANGELIST

read OLDCL < //tftpboot/Release/CICD/.oldP4change
echo $P4_CHANGELIST > /tftpboot/Release/CICD/.oldP4change

NEWCL=$P4_CHANGELIST

echo $OLDCL
echo $NEWCL

let PREVCL=$OLDCL+1

#/usr/local/bin/p4 -P $P4TICKET changes -l ...@$PREVCL,$NEWCL | sed '/^$/ d'| awk -v clist="Change $NEWCL" -v awk_bld=${UT_VERSION} '{if ($0 ~ clist) print $4 "- Jenkins build " awk_bld "\n" $0; else print}' >> /tftpboot/Release/CICD/changelist.txt
/usr/local/bin/p4 changes -l ...@$PREVCL,$NEWCL | sed '/^$/ d'| awk -v clist="Change $NEWCL" -v awk_bld=${UT_VERSION} '{if ($0 ~ clist) print $4 "- Jenkins build " awk_bld "\n" $0; else print}' >> /tftpboot/Release/CICD/changelist.txt
echo "" >> /tftpboot/Release/CICD/changelist.txt

# Remove Jenkins lines from file
sed -i '/p4svc_ut_jenkins/d' /tftpboot/Release/CICD/changelist.txt
sed -i '/Jenkins changed version to/d' /tftpboot/Release/CICD/changelist.txt

# submit the version files
#/usr/local/bin/p4 -P $P4TICKET submit -d "$DESCRIPTION" $VERSION_FILE
#/usr/local/bin/p4 submit -d "$DESCRIPTION" $VERSION_FILE $BBIRD_FILENAME
/usr/local/bin/p4 submit -d "$DESCRIPTION"

echo $OLDCL > /tftpboot/Release/CICD/.oldrange
echo $NEWCL > /tftpboot/Release/CICD/.newrange

# Update git tag 
cd ${WORKSPACE}/openwrt/
set_up_git_pass
update_git_tag_openwrt $openwrt_hash
