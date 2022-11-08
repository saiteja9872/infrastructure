"""
This script is used by a Jenkins job to ssh onto the MoDOT jumpbox
and use mtool to find and fix modems in Brazil
that are missing the /mnt/jffs2/config/odu.conf file.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from packaging import version
from libs.acs_db import AcsDb
from libs.beam_drift_db import BeamDriftDb
from libs.common_utils import batches, get_expected_env_var
from libs.jumpbox import Jumpbox
from libs.mtool_utils import (
    check_if_cmd_had_expected_output,
    create_mac_list_file,
    format_mac_addr,
    run_mtool_command,
)

# Future
NEW_SW_EXPECTED_CONFIG_HEADER = "; odu.conf version Brazil.003 06-10-2022"
FILE_PATH_FOR_NEW_ODU = "python_scripts/jobs/straggler_automation/odu_Brazil_003.conf"
MIN_VERSION_FOR_NEW_ODU = "3.8.0.2.0"
OLD_SW_EXPECTED_CONFIG_HEADER = "; odu.conf version Brazil.002 06-10-2022"
FILE_PATH_FOR_OLD_ODU = "python_scripts/jobs/straggler_automation/odu_Brazil_002.conf"
FILE_DOES_NOT_EXIST = "head: /mnt/jffs2/config/odu.conf: No such file or directory"
SUBOPTIMAL_CONFIG_HEADER = "# odu.conf version Brazil.001 05-19-2022"
DEFAULT_BATCH_SIZE = 35
DATABASE_OF_KNOWN_GOOD = "brazil_odu_conf_file_true"
DATABASE_OF_KNOWN_OFFLINE = "brazil_odu_conf_offline"
MTOOL_FILE_NAME = "ut_macs_brazil_file_fixerizer.txt"


def execute_file_fixerizer():
    """
    A function to satisfy requirements of TERMSW-30757.
    All fixed residential modems in Brazil should have a /mnt/jffs2/config/odu.conf file.
    """
    offline_after_fix = []

    # Get two lists of residential modems in Brazil via the ACS database and sorted by sw version
    newer_software, older_software = get_full_list_of_brazil_modems()

    # Check Jenkins drop-down then diff the ACS database with the odu database accordingly
    newer_software, older_software = find_jenkins_scan_depth(newer_software, older_software)

    # Check list of modems for presence of odu.conf file. Sort and add to odu database if applicable
    file_exists, new_file_not_exists, old_file_not_exists, offline = check_for_file(newer_software, older_software)

    # Attempt to fix the list of modems missing the odu.conf file
    if len(new_file_not_exists) == 0 and len(old_file_not_exists) == 0:
        put_succeeded = []
        put_failed = []
    else:
        put_succeeded, put_failed, offline_after_fix = fix_modems_missing_file(new_file_not_exists, old_file_not_exists)

    file_not_exists = new_file_not_exists + old_file_not_exists
    # Print job statistics
    print_results(
        file_exists,
        file_not_exists,
        put_failed,
        put_succeeded,
        offline,
        offline_after_fix,
    )


def get_full_list_of_brazil_modems():
    """
    A function to retrieve all brazil modems from CM-T's ACS
    backend database based on realm.

    :return: a list of mac addresses running newer software
    :return: a list of mac addresses running older software
    """
    print("\n====================note=====================")
    print("Querying the ACS database")
    acs_db = AcsDb()
    if get_expected_env_var("scan_type") == "new_installs" or get_expected_env_var("scan_type") == "unknowns":
        acs_query_results = acs_db.get_online_brazil_modems()
    else:
        acs_query_results = acs_db.get_all_brazil_modems()
    acs_db.database.disconnect()

    # Format the list and separate by modem software version
    new_software, old_software = format_acs_db_list(acs_query_results)

    return new_software, old_software


def find_jenkins_scan_depth(newer_software, older_software):
    """
    A function to determine which scan type was selected in the Jenkins job.
    A full scan will clear the database and start from scratch.
    A fast scan will only check modems not already confirmed to be fixed.

    :param newer_software: a list of all residential Brazil modems from the ACS database with newer code
    :param older_software: a list of all residential Brazil modems from the ACS database with older code
    :return: a list of modems to check for new odu.conf
    :return: a list of modems to check for old odu.conf
    """
    print("\n====================note=====================")
    print("Querying the odu.conf database")

    # Clear the databases and start from scratch
    if get_expected_env_var("scan_type") == "everything":
        clear_database(DATABASE_OF_KNOWN_GOOD)
        clear_database(DATABASE_OF_KNOWN_OFFLINE)
    # Clear the offline database and check for new installs and newly online
    elif get_expected_env_var("scan_type") == "unknowns":
        clear_database(DATABASE_OF_KNOWN_OFFLINE)
        newer_software = diff_database_and_all_modems(newer_software)
        older_software = diff_database_and_all_modems(older_software)
    # Find new installs
    elif get_expected_env_var("scan_type") == "new_installs":
        newer_software = diff_database_and_all_modems(newer_software, True)
        older_software = diff_database_and_all_modems(older_software, True)

    # This should not happen unless the Jenkins config was improperly modified
    else:
        print(f"\n\nCheck your Jenkins scan-type input: {get_expected_env_var('scan_type')}\n\n")
        sys.exit(1)
    return newer_software, older_software


def check_for_file(newer_software, older_software):
    """
    A function to send a list of modems to mtool
    to check for existence of /mnt/jffs2/config/odu.conf file.

    :param newer_software: a list of modems to check for the newest odu.conf
    :param older_software: a list of modems to check for the older odu.conf
    :return: a list of mac addresses that already have the needed file
    :return: a list of mac addresses that need the newer odu.conf
    :return: a list of mac addresses that need the older odu.conf
    :return: a list of mac addresses where status could not be determined, presumably offline
    """
    file_exists = []
    new_file_not_exists = []
    old_file_not_exists = []
    offline = []

    jumpbox = Jumpbox()
    command_to_run = 'head -1 /mnt/jffs2/config/odu.conf'
    print("\n====================note=====================")
    print(f"Checking {len(newer_software) + len(older_software)} modem(s) for odu.conf file")

    new_groups = batches(newer_software, DEFAULT_BATCH_SIZE)
    old_groups = batches(older_software, DEFAULT_BATCH_SIZE)
    groups = new_groups + old_groups
    counter = 1

    if len(newer_software) > 0:
        for group in new_groups:
            create_mac_list_file(jumpbox, MTOOL_FILE_NAME, group)
            print(f"Checking for odu file - batch {counter} of {len(groups)}")
            new_file_version_output, _ = run_mtool_command(
                jumpbox, f"-a run_commands -m {MTOOL_FILE_NAME} -C '{command_to_run}'",
                verbose=False
            )
            for mac in group:
                if check_if_cmd_had_expected_output(new_file_version_output, mac, NEW_SW_EXPECTED_CONFIG_HEADER):
                    file_exists.append(mac)
                elif check_if_cmd_had_expected_output(new_file_version_output, mac, OLD_SW_EXPECTED_CONFIG_HEADER):
                    new_file_not_exists.append(mac)
                elif check_if_cmd_had_expected_output(new_file_version_output, mac, SUBOPTIMAL_CONFIG_HEADER):
                    new_file_not_exists.append(mac)
                elif check_if_cmd_had_expected_output(new_file_version_output, mac, "[SRC]"):
                    new_file_not_exists.append(mac)
                elif check_if_cmd_had_expected_output(new_file_version_output, mac, FILE_DOES_NOT_EXIST):
                    new_file_not_exists.append(mac)
                else:
                    offline.append(mac)
            counter += 1

    if len(older_software) > 0:
        for group in old_groups:
            create_mac_list_file(jumpbox, MTOOL_FILE_NAME, group)
            print(f"Checking for odu file - batch {counter} of {len(groups)}")
            old_file_version_output, _ = run_mtool_command(
                jumpbox, f'-a run_commands -m {MTOOL_FILE_NAME} -C "{command_to_run}"',
                verbose=False
            )
            for mac in group:
                if check_if_cmd_had_expected_output(old_file_version_output, mac, OLD_SW_EXPECTED_CONFIG_HEADER):
                    file_exists.append(mac)
                elif check_if_cmd_had_expected_output(old_file_version_output, mac, SUBOPTIMAL_CONFIG_HEADER):
                    old_file_not_exists.append(mac)
                elif check_if_cmd_had_expected_output(old_file_version_output, mac, "[SRC]"):
                    old_file_not_exists.append(mac)
                elif check_if_cmd_had_expected_output(old_file_version_output, mac, FILE_DOES_NOT_EXIST):
                    old_file_not_exists.append(mac)
                else:
                    offline.append(mac)
            counter += 1

    jumpbox.clear_any_previous_results(prefix="ut_macs_")
    jumpbox.disconnect()

    if len(file_exists) > 0:
        add_mac_to_database(file_exists, DATABASE_OF_KNOWN_GOOD)
        print(f"added {len(file_exists)} modem(s) to known fixed database")
    if len(offline) > 0:
        add_mac_to_database(offline, DATABASE_OF_KNOWN_OFFLINE)
        print(f"added {len(offline)} modem(s) to offline database")

    return file_exists, new_file_not_exists, old_file_not_exists, offline


def diff_database_and_all_modems(modems, do_not_check_offline=False):
    """
    A function to ignore modems that exist in the database and retain
    only the modems that need to be checked for presence of the odu.conf file.

    :param modems: a list of all modem mac addresses from the ACS db
    :param do_not_check_offline: T/F to exclude offline modems
    :return: a list of modems to check
    """
    modems_to_check = []
    current_offline_database = []

    ut_ops_automations_db = BeamDriftDb()
    current_fixed_database = ut_ops_automations_db.get_brazil_records(DATABASE_OF_KNOWN_GOOD)
    if do_not_check_offline:
        current_offline_database = ut_ops_automations_db.get_brazil_records(DATABASE_OF_KNOWN_OFFLINE)
    ut_ops_automations_db.database.disconnect()

    macs_in_database = current_fixed_database + current_offline_database
    macs_in_database = format_ut_db_list(macs_in_database)

    for modem in modems:
        if modem not in macs_in_database:
            modems_to_check.append(modem)

    return modems_to_check


def add_mac_to_database(modems, table):
    """
    A function to add modems with odu.conf file to the database.

    :param modems: a list of modems to add to the database
    :param table: name of table to add the list of modems
    """
    ut_ops_automations_db = BeamDriftDb()
    for modem in modems:
        ut_ops_automations_db.add_brazil_records(modem, table)
    ut_ops_automations_db.database.disconnect()


def clear_database(table):
    """
    A function to clear the existing database.

    :param table: name of the table to clear
    """

    ut_ops_automations_db = BeamDriftDb()
    ut_ops_automations_db.delete_brazil_records(table)
    ut_ops_automations_db.database.disconnect()


def fix_modems_missing_file(new_file_needed, old_file_needed):
    """
    A function to put a file on a modem using mtool and if successful, reboot.

    :param new_file_needed: a list of modems needing the newer odu.conf file
    :param old_file_needed: a list of modems needing an older odu.conf file
    :return: a list of modems that received the file and rebooted
    :return: a list of modems that did not receive the file
    :return: a list of modems offline after a fix was attempted
    """
    file_exists = []
    file_not_exists = []
    offline = []

    jumpbox = Jumpbox()

    print("\n====================note=====================")
    print("WARNING: THIS STEP TAKES A LONG TIME TO RUN")
    print(f"Attempting to fix {len(new_file_needed) + len(old_file_needed)} modem(s)")

    new_groups = batches(new_file_needed, DEFAULT_BATCH_SIZE)
    old_groups = batches(old_file_needed, DEFAULT_BATCH_SIZE)
    groups = new_groups + old_groups
    counter = 1

    if len(new_file_needed) > 0:
        jumpbox.upload_file(FILE_PATH_FOR_NEW_ODU, "odu.conf.new")
        for group in new_groups:
            command_to_run = '/mnt/jffs2/config/odu.conf'
            create_mac_list_file(jumpbox, MTOOL_FILE_NAME, group)
            print(f"Attempting to upload odu.conf - batch {counter} of {len(groups)}")
            output, _ = run_mtool_command(
                jumpbox, f"-a put_file -m {MTOOL_FILE_NAME} -l '/tmp/odu.conf.new' -r '{command_to_run}'",
                verbose=False
            )
            counter += 1
    if len(old_file_needed) > 0:
        jumpbox.upload_file(FILE_PATH_FOR_OLD_ODU, "odu.conf.old")
        for group in old_groups:
            command_to_run = '/mnt/jffs2/config/odu.conf'
            create_mac_list_file(jumpbox, MTOOL_FILE_NAME, group)
            print(f"Attempting to upload odu.conf - batch {counter} of {len(groups)}")
            output, _ = run_mtool_command(
                jumpbox, f"-a put_file -m {MTOOL_FILE_NAME} -l '/tmp/odu.conf.old' -r '{command_to_run}'",
                verbose=False
            )
            counter += 1
    modems = new_file_needed + old_file_needed
    groups = batches(modems, DEFAULT_BATCH_SIZE)
    counter = 1
    for group in groups:
        # Check the output
        command_to_run = 'test -f /mnt/jffs2/config/odu.conf ; echo $?'
        create_mac_list_file(jumpbox, MTOOL_FILE_NAME, group)
        print(f"Validating - batch {counter} of {len(groups)}")
        output, _ = run_mtool_command(
            jumpbox, f"-a run_commands -m {MTOOL_FILE_NAME} -C '{command_to_run}'",
            verbose=False
        )
        for mac in group:
            if check_if_cmd_had_expected_output(output, mac, "0"):
                file_exists.append(mac)
            elif check_if_cmd_had_expected_output(output, mac, "1"):
                file_not_exists.append(mac)
            else:
                offline.append(mac)
        counter += 1

    if len(file_exists) > 0:
        add_mac_to_database(file_exists, DATABASE_OF_KNOWN_GOOD)
        print(f"Added {len(file_exists)} modem(s) to the known fixed database")
    if len(offline) > 0:
        add_mac_to_database(offline, DATABASE_OF_KNOWN_OFFLINE)
        print(f"Added {len(offline)} modem(s) to offline database")

    jumpbox.clear_any_previous_results(prefix="ut_macs_")
    jumpbox.disconnect()
    return file_exists, file_not_exists, offline


def print_results(
        file_exists,
        file_not_exists,
        put_failed,
        put_succeeded,
        offline,
        offline_after_fix,
):
    """
    A function to print a report of the job statistics.

    :param file_exists: a list of mac addresses that did not need a fix
    :param file_not_exists: a list of mac addresses that needed a fix
    :param put_failed: a list of mac addresses that needed a fix but failed to receive the file
    :param put_succeeded: a list of mac addresses that needed a fix and received the file
    :param offline: a list of mac addresses that were offline
    :param offline_after_fix: a list of mac addresses that were offline after a fix was attempted
    """

    # Print list of modems that might need individual investigation
    if len(put_failed) > 0:
        print("\n==============modems of interest=============")
        print("\nThe following modem(s) did not have the file after a fix was attempted:")
        for mac in put_failed:
            print(f"{mac}")

    # Print summary statistics for the job
    print("\n===================summary===================\n")
    print(f"Of the {len(file_exists) + len(file_not_exists) + len(offline)} modem(s) checked:\n")
    """
    print(f"{len(offline) + len(offline_after_fix)} \tmodem(s) were offline")
    print(f"{len(file_exists)} \tmodem(s) already had the fix")
    print(f"{len(put_succeeded)} \tmodem(s) were fixed by this job")
    print(f"{len(put_failed)} \tmodem(s) remain broken")
    """
    print(f"OFFLINE: \t\t{len(offline) + len(offline_after_fix)}")
    print(f"NO ACTION: \t\t{len(file_exists)}")
    print(f"FIXED: \t\t\t{len(put_succeeded)}")
    print(f"FIX FAILED: \t\t{len(put_failed)}")


def format_acs_db_list(modems):
    """
    A function to change a list of dictionaries containing software and mac addresses into
    two lists of modem macs sorted by software version.

    :param modems: a list of dictionaries containing software versions and mac addresses
    :return: a unique list of mac addresses running code above or equal to VERSION_FOR_NEW_ODU
    :return: a unique list of mac addresses running code below VERSION_FOR_NEW_ODU
    """
    new_software = []
    old_software = []
    for modem in modems:
        # NOTE: Formatters call a syntax error in this line but it is necessary in this case
        if version.parse(modem["softwareVersion"].lstrip("UT2\_")) >= version.parse(MIN_VERSION_FOR_NEW_ODU):
            new_software.append(modem["cid"])
        else:
            old_software.append(modem["cid"])

    return new_software, old_software


def format_ut_db_list(modems):
    """
    A function to change a list of dictionaries containing mac addresses into
    a single formatted list of modems.

    :param modems: a list of dictionaries containing mac addresses
    :return: a unique list of mac addresses
    """
    return [modem["mac"] for modem in modems]


if __name__ == "__main__":
    print("\n====================begin====================")
    try:
        execute_file_fixerizer()
    except Exception as ex:
        print(f"\n{ex}")
        raise
    finally:
        print("\n=====================end=====================\n")
