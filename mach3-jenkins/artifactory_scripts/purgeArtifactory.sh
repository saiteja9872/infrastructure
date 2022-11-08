#!/usr/bin/env bash

# Set variables
export MACH3_GENERIC_DEV=/mach3-generic-dev/terminal/viaphy3
export TERMINAL_GREEN=/terminals-viaphy3-green
export TERMINAL_YELLOW=/terminals-viaphy3-yellow
export DEV_G_LOC=/terminals-viaphy3-dev-g
export DEV_Y_LOC=/terminals-viaphy3-dev-y
export PREPROD_G_LOC=/terminals-viaphy3-preprod-g
export PREPROD_Y_LOC=/terminals-viaphy3-preprod-y
export PROD_G_LOC=/terminals-viaphy3-prod-g

mach3_genereic_dev_folder=(asic blackbird fcv protium1)
terminal_green_folder=(asic blackbird fcv protium1) # scpfw ssbl vcmpu)
terminal_yellow_folder=(asic blackbird fcv protium1) # ssbl vcmpu)

purge_folder()
{
    repo=("$@")
    echo "Number of days of build to keep: $maxAge"
    if $soloPurge; then
        echo "Solo folder, purge folder $artiFolder"
        if $dryRun; then
            echo "Dry run, just print"
            if $ignoreList; then
                ./artiPurgeTool.py /$artiPath/$artiFolder -a $maxAge -n -w $whiteList
            else
                ./artiPurgeTool.py /$artiPath/$artiFolder -a $maxAge -n
            fi
        else
            if $ignoreList; then
                ./artiPurgeTool.py /$artiPath/$artiFolder -a $maxAge -w $whiteList
            else
                ./artiPurgeTool.py /$artiPath/$artiFolder -a $maxAge
            fi
        fi
    else
        for folder in "${repo[@]}"; do
            echo "Purge the folder $folder"
            if $dryRun; then
                echo "Dry run, just print"
                if $ignoreList; then
                    ./artiPurgeTool.py $MACH3_GENERIC_DEV/$folder -a $maxAge -n -w ./whitelist.txt
                else
                    ./artiPurgeTool.py $MACH3_GENERIC_DEV/$folder -a $maxAge -n
                fi
            else
                if $ignoreList; then
                    ./artiPurgeTool.py $MACH3_GENERIC_DEV/$folder -a $maxAge -w ./whitelist.txt
                else
                    ./artiPurgeTool.py $MACH3_GENERIC_DEV/$folder -a $maxAge
                fi
            fi
        done
    fi
}

# execute script from git
ls -ltr
pwd
cd mach3-jenkins/artifactory_scripts
ls
purge_folder ${mach3_genereic_dev_folder[@]}

