"""
Contains functionality for attempting to update "stragglers" for various applications or settings.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import traceback
from libs.acs_db import AcsDb  # for running SQL commands on the ACS database
from libs.jumpbox import Jumpbox
from libs.mtool_utils import (
    create_mac_list_file,
    run_mtool_command,
    check_if_cmd_had_expected_output,
)
from libs.common_utils import (
    batches,
    get_expected_env_var,
    print_heading,
)
import update_stragglers_versions as import_list

DEFAULT_BATCH_SIZE = 35
MAC_LIST_FILE_NAME = "ut_macs_app_stragglers.txt"


def update_stragglers():
    """
    Gets data from Jenkins, determines what to send to SQL db, formats the list, then fixes them
    """
    app_to_query_and_fix = get_expected_env_var("app_to_query")
    dict_of_macs_and_cids, profile = find_db_inputs_by_selection(app_to_query_and_fix)
    list_of_macs = format_straggler_list(dict_of_macs_and_cids)
    fix_stragglers_via_mtool(list_of_macs, profile)


def find_db_inputs_by_selection(application):
    """
    A function to determine the values to send to the ACS database to be queried
    :param application: The name of the application supplied by user input in Jenkins
    :return: a list of dictionaries containing mac addresses and the profile name needed for mtool
    """
    db_query_results = []
    profile = ""
    print(f"\n===================={application}=====================")
    try:
        if application == "modoc":
            app_versions = import_list.MODOC_VERSIONS
            db_query_results = get_modoc_stragglers(app_versions)
            profile = "modot_install_modoc"
        elif application == "vstat":
            app_versions = import_list.VSTAT_VERSIONS
            db_query_results = get_vstat_stragglers(app_versions)
            profile = "modot_install_vstat_<hw type>"
        elif application == "esp":
            app_versions = import_list.ESP_VERSIONS
            db_query_results = get_esp_stragglers(app_versions)
            profile = "modot_install_esp"
        elif application == "statpush":
            db_query_results = get_statpush_stragglers()
            profile = "modot_statpush_config_<hw type>"
        elif application == "bb_url":
            db_query_results = get_bburl_stragglers()
            profile = "modot_bb_url"
        elif application == "fw_dw_mode":
            db_query_results = get_fw_dw_mode_stragglers()
            profile = "modot_firmware_download_mode"
        elif application == "allowlist":
            app_versions = import_list.ALLOWLIST_UNACCEPTABLE_VERSIONS
            db_query_results = get_allowlist_stragglers(app_versions)
            profile = "modot_app_allowlist"
        elif application == "blueout":
            db_query_results = get_blueout_stragglers()
            profile = "modot_enable_blueout"
        elif application == "fl_unlock":
            db_query_results = get_fl_unlock_stragglers()
            profile = "modot_set_flutimer"
        elif application == "ota_modems":
            # This is a special case for OTA automation team's modems
            # No SQL query is needed; therefore no specialized function
            db_query_results = import_list.OTA_MAC_LIST
            profile = "modot_no_filters_modoc"
        elif application == "shield_localhost_fix":
            # This is a special case for shield bug termsw-32980
            db_query_results = get_shield_with_localhost()
            # The prior function is exited and we do not return here
        elif application == "vstat_4.2_fix":
            # This is a special case for vstat bug termsw-33245
            db_query_results = get_42x_and_vstat()
            # The prior function is exited and we do not return here
        elif application == "vwa":
            get_vwa_stragglers()
            db_query_results = get_vwa_stragglers()
            profile = "<term type>_default"
        else:
            print(f"Invalid drop-down option received from Jenkins: {application}")
    except Exception as error_msg:
        print(f"SOMETHING WENT WRONG: error was {error_msg}")
        sys.exit()

    return db_query_results, profile


def get_modoc_stragglers(versions):
    """
    A function to get modoc stragglers
    :param versions: List of versions acceptable for the modoc application
    :return: a list of dictionaries containing mac addresses
    """
    app = "modoc"
    modoc_mac_list = []
    list_of_versions = []
    acceptable_hardware = import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    for version in versions:
        list_of_versions += [f"{app}-{version}"]
    modoc_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)

    # A query for out-of-date modoc rules versions
    app = "modoc_rules"
    versions = import_list.MODOC_RULES_UNACCEPTABLE_VERSIONS
    acs_db = AcsDb()
    for version in versions:
        modoc_mac_list += acs_db.get_app_stragglers(
            app,
            acceptable_hardware,
            [f"%%with Version=2.4 and RulesVersion={version}"],
        )
    acs_db.database.disconnect()

    return modoc_mac_list


def get_vstat_stragglers(versions):
    """
    A function to get vstat stragglers
    :param versions: List of versions acceptable for the vstat application
    :return: a list of dictionaries containing mac addresses
    """
    app = "vstats"
    vstat_mac_list = []
    list_of_versions = []
    acceptable_hardware = import_list.UT2_HW + import_list.SPOCK_HW
    for version in versions:
        list_of_versions += [f"{app}-{version}"]
    vstat_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)
    return vstat_mac_list


def get_esp_stragglers(versions):
    """
    A function to get esp stragglers
    :param versions: List of versions acceptable for the esp application
    :return: a list of dictionaries containing mac addresses
    """
    app = "esp"
    esp_mac_list = []
    list_of_versions = []
    acceptable_hardware = (
        import_list.UT_HW + import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    )
    for version in versions:
        list_of_versions += [f"{app}-{version}"]
    esp_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)
    return esp_mac_list


def get_statpush_stragglers():
    """
    A function to get statpush stragglers
                First check is for applicable modems without statpush entirely
                Subsequent checks are for the statpush version which varies by hardware type
    :return: a list of dictionaries containing mac addresses
    """
    app = "statpush"
    statpush_mac_list = []
    acceptable_hardware = (
        import_list.UT_HW + import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    )
    statpush_mac_list += run_sql_queries(app, acceptable_hardware)

    app = "statpush_by_hw"

    # UT by acceptable version
    list_of_versions = []
    acceptable_hardware = import_list.UT_HW
    list_of_versions += [f"{x}" for x in import_list.STATPUSH_UT_VERSIONS]
    statpush_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)

    # UT2 by acceptable version
    list_of_versions = []
    acceptable_hardware = import_list.UT2_HW
    list_of_versions += [f"{x}" for x in import_list.STATPUSH_UT2_VERSIONS]
    statpush_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)

    # DATA by acceptable version
    list_of_versions = []
    acceptable_hardware = import_list.DATA_HW
    list_of_versions += [f"{x}" for x in import_list.STATPUSH_DATA_VERSIONS]
    statpush_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)

    # SPOCK by acceptable version
    list_of_versions = []
    acceptable_hardware = import_list.SPOCK_HW
    list_of_versions += [f"{x}" for x in import_list.STATPUSH_SPOCK_VERSIONS]
    statpush_mac_list += run_sql_queries(app, acceptable_hardware, list_of_versions)

    return statpush_mac_list


def get_bburl_stragglers():
    """
    A function to get blackbox url stragglers
    :return: a list of dictionaries containing mac addresses
    """
    app = "bb_url"
    bburl_mac_list = []
    acceptable_hardware = (
        import_list.UT_HW + import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    )
    bburl_mac_list += run_sql_queries(
        app,
        acceptable_hardware,
        ['%%"BBServerPath": "https://bbserver.ut-devops-prod.viasat.io/bbmanager/blackboxes"%%'],
    )
    return bburl_mac_list


def get_fw_dw_mode_stragglers():
    """
    A function to get firmware download mode 2 stragglers
    :return: a list of dictionaries containing mac addresses
    """
    app = "fw_dwld"
    fwmd_mac_list = []
    acceptable_hardware = import_list.DATA_HW
    fwmd_mac_list += run_sql_queries(
        app,
        acceptable_hardware,
    )
    return fwmd_mac_list


def get_allowlist_stragglers(versions):
    """
    A function to get allowlist (aka whitelist) stragglers
    :param versions: List of versions unacceptable for the allowlist entry
    :return: a list of dictionaries containing mac addresses
    """
    app = "allowlist"
    allowlist_mac_list = []
    acceptable_hardware = (
        import_list.UT_HW + import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    )
    acs_db = AcsDb()
    for version in versions:
        allowlist_mac_list += acs_db.get_app_stragglers(
            app,
            acceptable_hardware,
            [f"%%AppWhitelist_{version}%%"],
        )
    acs_db.database.disconnect()
    return allowlist_mac_list


def get_blueout_stragglers():
    """
    A function to get blueout mode stragglers
    :return: a list of dictionaries containing mac addresses
    """
    app = "blueout"
    blueout_mac_list = []
    acceptable_hardware = (
        import_list.SPOCK_HW
    )  # TODO: add DATA after XCI is rolled out BBCTERMSW-29491
    blueout_mac_list += run_sql_queries(
        app,
        acceptable_hardware,
        ['%%"ODUBlueOutEnable": true%%'],
    )
    return blueout_mac_list


def get_fl_unlock_stragglers():
    """
    A function to get fl unlock timer stragglers
                Check is for applicable modems without fl unlock set to 14400
    :return: a list of dictionaries containing mac addresses
    """
    app = "fl_unlock"
    unlock_mac_list = []
    acceptable_hardware = import_list.SPOCK_HW + import_list.DATA_HW
    unlock_mac_list += run_sql_queries(
        app,
        acceptable_hardware,
    )
    return unlock_mac_list


def get_shield_with_localhost():
    """
    A function to find shield modems with a localhost entry
    then reboot to resolve the issue
    See TERMSW-32980 for details
    """
    shield_list = []
    local_host_present = []
    modems_to_investigate = []
    modems_not_broken = []
    offline = []

    # Get a list of the shield modems from ACS database
    app = "shield_localhost"
    shield_list += run_sql_queries(app, import_list.SPOCK_HW,)
    formatted_shield_list = format_straggler_list(shield_list)

    jumpbox = Jumpbox()
    # jumpbox.run_command("sshca-client -v")

    # Check for localhost output in the ufwd file
    command_to_run = 'grep -c 127.0.0.1 /tmp/ufwdctrlsrv.conf'
    groups = batches(formatted_shield_list, DEFAULT_BATCH_SIZE)
    counter = 1

    print("\n\n====================note=====================")
    print(f"Checking {len(formatted_shield_list)} modem(s) for localhost in ufwdctrlsrv.conf.....")
    for group in groups:
        print(f"Checking batch {counter} of {len(groups)}")
        create_mac_list_file(jumpbox, MAC_LIST_FILE_NAME, group)
        output, _ = run_mtool_command(
            jumpbox, f"-a run_commands -m {MAC_LIST_FILE_NAME} -C '{command_to_run}'",
            verbose=False,
        )
        # Check the output
        for mac in group:
            if check_if_cmd_had_expected_output(output, mac, '0'):
                modems_not_broken.append(mac)
            elif check_if_cmd_had_expected_output(output, mac, '1'):
                local_host_present.append(mac)
            else:
                offline.append(mac)
        counter += 1

    # If modem failed the previous step, check again to exclude modems with shield disabled (bridge mode)
    if len(local_host_present) > 0:
        counter = 1
        command_to_run = 'utstat -Y | grep shield | grep enabled'
        output_if_present = 'shield admin state:  enabled'
        groups = batches(local_host_present, DEFAULT_BATCH_SIZE)

        print("\n\n====================note=====================")
        print(f"Checking {len(local_host_present)} modem(s) for shield state.....")
        for group in groups:
            print(f"Checking batch {counter} of {len(groups)}")
            create_mac_list_file(jumpbox, MAC_LIST_FILE_NAME, group)
            output, _ = run_mtool_command(
                jumpbox, f"-a run_commands -m {MAC_LIST_FILE_NAME} -C '{command_to_run}'",
                verbose=False,
            )
            # Check the output
            for mac in group:
                if check_if_cmd_had_expected_output(output, mac, output_if_present):
                    modems_to_investigate.append(mac)
                else:
                    modems_not_broken.append(mac)
            counter += 1

    # Fix the broken modems by rebooting
    if len(modems_to_investigate) > 0:
        counter = 1
        command_to_run = 'reboot'
        groups = batches(modems_to_investigate, DEFAULT_BATCH_SIZE)

        print("\n\n====================note=====================")
        print(f"Fixing {len(modems_to_investigate)} modem(s).....")
        for group in groups:
            print(f"Fixing batch {counter} of {len(groups)}")
            create_mac_list_file(jumpbox, MAC_LIST_FILE_NAME, group)
            output, _ = run_mtool_command(
                jumpbox, f"-a run_commands -m {MAC_LIST_FILE_NAME} -C '{command_to_run}'",
                verbose=False,
            )
            counter += 1

    jumpbox.clear_any_previous_results(prefix="ut_macs_")
    jumpbox.disconnect()

    print("\n\n====================summary=====================")
    print(f"Healthy: \t{len(modems_not_broken)}")
    print(f"Offline: \t{len(offline)}")
    print(f"Fixed: \t\t{len(modems_to_investigate)}")

    sys.exit(0)


def get_42x_and_vstat():
    """
    A function to find 4.2.x modems running an older
    version of the vstat application
    Fix requires root access which is not possible
    via automation at this time
    See TERMSW-33245 for details
    """
    # Get a list of the 4.2 modems with vstat != 2.1.4 from ACS database
    app = "vstat_42x_fix"
    old_vstat_list = []
    modems_to_investigate = []
    modems_not_broken = []
    offline = []
    old_vstat_list += run_sql_queries(app, import_list.SPOCK_HW, ['SPOCK_4.2.%%'])
    formatted_old_vstat_list = format_straggler_list(old_vstat_list)

    # Log onto the modem to check uForwarder status
    jumpbox = Jumpbox()
    # jumpbox.run_command("sshca-client -v")

    command_to_run = 'utstat -Y | grep "ufwd admin state"'
    groups = batches(formatted_old_vstat_list, DEFAULT_BATCH_SIZE)
    counter = 1

    print("\n\n====================note=====================")
    print(f"Checking {len(formatted_old_vstat_list)} modem(s) for uForwarder status....")
    for group in groups:
        print(f"Checking batch {counter} of {len(groups)}")
        create_mac_list_file(jumpbox, MAC_LIST_FILE_NAME, group)
        output, _ = run_mtool_command(
            jumpbox, f"-a run_commands -m {MAC_LIST_FILE_NAME} -C '{command_to_run}'",
            verbose=False,
        )
        # Check the output
        for mac in group:
            if check_if_cmd_had_expected_output(output, mac, 'ufwd admin state:    enabled'):
                modems_to_investigate.append(mac)
            elif check_if_cmd_had_expected_output(output, mac, 'ufwd admin state:    disabled'):
                modems_not_broken.append(mac)
            else:
                offline.append(mac)
        counter += 1

    if len(modems_to_investigate) > 0:
        print("\n\n====================action_needed=====================")
        for mac in modems_to_investigate:
            print(f"{mac}")

        print("\n\nAs root, perform the following:")
        print("\nmnt_vstat_dir=/mnt/jffs2/vstats"
              "\nvstats_tarball=`ls -c /ufwdfs/usr/bin/vstats*.tar.gz 2> /dev/null|head -1`"
              "\nif [ ! -z '$vstats_tarball' ]; then"
              "\n    cd $mnt_vstat_dir && "
              "\n        rm -f *.tar.gz && "
              "\n        tar zxf $vstats_tarball && "
              "\n        cp vstat /usr/bin/vstat && "
              "\n        cp vstats_setup /usr/bin/vstats_setup && "
              "\n        cp compatible_platform /usr/bin/compatible_platform && "
              "\n        vstats_setup INSTALL $(vstat -v) 2> /dev/null && "
              "\n        killall vstat && vstats_setup START "
              "\n    rm -f /ufwdfs/usr/bin/vstats*.tar.gz "
              "\nfi")

    print("\n\n====================summary=====================")
    print(f"Healthy: \t{len(modems_not_broken)}")
    print(f"Offline: \t{len(offline)}")
    print(f"Broken: \t{len(modems_to_investigate)}")
    print("--------------------------")
    print(f"Total: \t\t{len(formatted_old_vstat_list)}")

    sys.exit(0)


def get_vwa_stragglers():
    """
    A function to get vwa stragglers based on a mismatch of image id and current id
    :return: a list of dictionaries containing mac addresses
    """
    app = "vwa"
    vwa_mac_list = []
    acceptable_hardware = (
        import_list.UT_HW + import_list.UT2_HW + import_list.DATA_HW + import_list.SPOCK_HW
    )
    vwa_mac_list += run_sql_queries(app, acceptable_hardware,)

    return vwa_mac_list


def run_sql_queries(application, hardware, helper_string=None):
    """
    A function to query the ACS SQL database
    :param application: a string identifying the app to query
    :param hardware: a string of the hardware types applicable to the query
    :param helper_string: an SQL fragment string of versions or other needed search strings
    :return: a list of dictionaries containing mac addresses
    """
    acs_db = AcsDb()
    db_query_results = acs_db.get_app_stragglers(application, hardware, helper_string)
    acs_db.database.disconnect()
    return db_query_results


def fix_stragglers_via_mtool(modems, profile):
    """
    A function to run mtool on modem stragglers and apply a profile to repair the modem
    :param modems: a list of mac addresses
    :param profile: a string with the profile to apply
    """
    jumpbox = Jumpbox()
    # Refresh the ssh-ca certs
    # jumpbox.run_command("sshca-client -v")
    mac_list_file_name = "ut_macs_app_stragglers.txt"

    print(f"\n====================note=====================")
    print(f"Attempting to fix {len(modems)} modem(s)")
    groups = batches(modems, DEFAULT_BATCH_SIZE)
    counter = 1

    for group in groups:
        print(f"Working on batch {counter} of {len(groups)}")
        create_mac_list_file(jumpbox, mac_list_file_name, group)
        run_mtool_command(
            jumpbox, f"-a push_profile -m 'ut_macs_app_stragglers.txt' -P '{profile}' -i -t 10",
            verbose=False
        )
        counter += 1
    jumpbox.clear_any_previous_results(prefix="ut_macs_")
    jumpbox.disconnect()


def format_straggler_list(modems):
    """
    A function to change a list of dictionaries containing mac addresses into
                            a single formatted list of modems
    :param modems: a list of dictionaries containing mac addresses
    :return: a unique list of mac addresses considered to be stragglers
    """
    return list({modem["cid"] for modem in modems})


# The main function
if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        update_stragglers()
    except Exception as ex:
        print_heading(f"SOMETHING WENT WRONG: {ex}")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
