cd ${WORKSPACE}/openwrt

# Loop through each profile and build it
for profile in ${OPENWRT_BUILD_PROFILES}; do
    ./target/linux/viaphy3/gen_bundle.sh . $OPENWRT_BUILD_SUBTARGET $profile
done

cd ${WORKSPACE}