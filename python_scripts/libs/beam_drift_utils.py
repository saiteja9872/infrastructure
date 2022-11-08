"""
Contains functionality for attempting to correct modems that have drifted onto the wrong beam.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from time import sleep, time
from random import shuffle
import urllib3
from libs import common_utils, mtool_utils, cmt_utils
from libs.acs_db import AcsDb

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_WAIT_FOR_ONLINE_SECS = 600  # ten minutes in seconds
SECONDS_IN_A_MINUTE = 60  # one minute in seconds
LKG_FILE_PATH_ON_MODEM = "/mnt/jffs2/config/lkg-fwd.conf"

# the max number of attempts we're willing to make to pull
# a good LKG file from an online modem on a given beam
MAX_LKG_PULL_ATTEMPTS_PER_BEAM = 10

# how many seconds to sleep between each check when waiting for a modem to come online
ONLINE_CHECK_INTERVAL_SECS = 15

# how many seconds to wait after a modem comes online to try to interact with it
WAIT_FOR_NEWLY_ONLINE_MODEM_TO_STABILIZE_SECS = 20

# mtool struggles when we give it too many modems at once
MTOOL_BATCH_SIZE_DEFAULT = 35


def get_modems_on_wrong_beam(
    beam_drift_db, modems
):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """
    Step #1 - Check whether input modems are on the wrong beam and create dictionaries for each
              modem we're working on to keep track of its current beam and goal beam.

    :param beam_drift_db: an instance of the BeamDriftDb class
    :return: a list of dictionaries representing the modems that are already on their goal beams,
             a list of dictionaries representing the modems that have drifted from their goal
             beams, and a list of dictionaries representing the modems whose beam pinnings we were
             unable to check in ACS
    """

    # We need to confirm whether each modem is has drifted from its goal beam.
    print(" \nlooking up each modem's current and goal beam via CM-T")
    mismatched = []
    matched = []
    ambitionless = []
    goal_on_different_satellite = []
    failed_to_check = []
    for modem in modems:
        mac = modem[0]
        goal_sat = modem[1]  # will be None if job parameter didn't provide an override
        goal_beam = modem[2]  # will be None if job parameter didn't provide an override
        goal_pol = modem[3]  # will be None if job parameter didn't provide an override

        # Get information about each modem's current satellite and beam.
        enrichment_response = cmt_utils.get_enrichment_data(mac)
        orig_sat = cmt_utils.parse_orig_sat_from_enrichment_data(enrichment_response)
        orig_beam = cmt_utils.parse_orig_beam_from_enrichment_data(enrichment_response)
        orig_pol = cmt_utils.parse_orig_pol_from_enrichment_data(enrichment_response)
        vno = cmt_utils.parse_vno_from_enrichment_data(enrichment_response)
        if enrichment_response.status_code != 200 or not orig_beam or not orig_sat:
            failed_to_check.append(
                {
                    "mac": mac,
                    "orig sat": "?",
                    "orig beam": "?",
                    "goal sat": goal_sat or "?",
                    "goal beam": goal_beam or "?",
                    "goal pol": goal_pol or "?",
                    "sat pin": "?",
                    "beam pin": "?",
                    "pol pin": "?",
                    "sw version": "<did not check SW version>",
                    "vno": vno,
                }
            )
            common_utils.print_http_response(enrichment_response)
            continue
        if common_utils.is_job_verbose():
            common_utils.print_http_response(enrichment_response)

        # Determine each what satellite and beam each modem is
        # pinned to in the ACS by looking at its CPE config.
        config_response = cmt_utils.get_cpe_config(mac)
        if config_response.status_code != 200:
            failed_to_check.append(
                {
                    "mac": mac,
                    "orig sat": orig_sat,
                    "orig beam": orig_beam,
                    "orig pol": orig_pol,
                    "goal sat": goal_sat or "?",
                    "goal beam": goal_beam or "?",
                    "goal pol": goal_pol or "?",
                    "sat pin": "?",
                    "beam pin": "?",
                    "pol pin": "?",
                    "sw version": "<did not check SW version>",
                    "vno": vno,
                }
            )
            common_utils.print_http_response(config_response)
            continue
        if common_utils.is_job_verbose():
            common_utils.print_http_response(config_response)

        # Parse the current satellite and beam ACS pinning from the CM-T response.
        sat_pin = cmt_utils.parse_goal_sat_id_from_cpe_config(config_response)
        beam_pin = cmt_utils.parse_goal_beam_from_cpe_config(config_response)
        pol_pin = cmt_utils.parse_goal_pol_from_cpe_config(config_response)
        sw_version = cmt_utils.parse_sw_version_from_cpe_config(config_response)

        # If we didn't provide a manual override of the goal satellite and beam,
        # we'll need to determine what they should be.
        if not (goal_sat and goal_beam and goal_pol):

            # If the beam pin is currently zero, then we must have cleared the pinning in a
            # previous run of the job. We attempt to look up its former goal in our local
            # goal database, where we save goal data before we clear it.
            if beam_pin == 0:
                saved_goal = beam_drift_db.look_up_goal(mac, verbose=common_utils.is_job_verbose())
                if saved_goal and "goal_sat" in saved_goal and "goal_beam" in saved_goal:
                    goal_sat = saved_goal["goal_sat"]
                    goal_beam = saved_goal["goal_beam"]
                    goal_pol = saved_goal["goal_pol"]

            # If we didn't determine the goal by some other means by now, then we default to the
            # current pinning in ACS as the goal. If a modem has no goal satellite ID specified,
            # we can assume it's trying to move to a beam within the same satellite ID that it's
            # currently on.
            goal_sat = goal_sat or sat_pin or orig_sat
            goal_beam = goal_beam or beam_pin
            goal_pol = goal_pol or pol_pin

        # If a modem doesn't have a beam pinning and we didn't provide an override in the job
        # parameter, we can't proceed further with that modem because we don't know where to
        # tell it to move.
        if not (
            goal_beam
            and goal_pol
            and common_utils.is_valid_beam_pol(goal_pol)
            and goal_pol != "NOT_SET"
        ):
            ambitionless.append(
                {
                    "mac": mac,
                    "orig sat": orig_sat,
                    "orig beam": orig_beam,
                    "orig pol": orig_pol,
                    "goal sat": goal_sat,
                    "goal beam": goal_beam if (goal_beam is not None) else "_",
                    "goal pol": goal_pol if (goal_pol is not None) else "_",
                    "sat pin": sat_pin if (sat_pin is not None) else "_",
                    "beam pin": beam_pin if (beam_pin is not None) else "_",
                    "pol pin": pol_pin if (pol_pin is not None) else "_",
                    "sw version": sw_version,
                    "vno": vno,
                }
            )
            common_utils.print_http_response(config_response)
            continue

        # If a modem is trying to move to a beam on a different satellite,
        # its problem is outside the scope of this job, so we leave it alone.
        if goal_sat != orig_sat:
            goal_on_different_satellite.append(
                {
                    "mac": mac,
                    "orig sat": orig_sat,
                    "orig beam": orig_beam,
                    "orig pol": orig_pol,
                    "goal sat": goal_sat,
                    "goal beam": goal_beam if (goal_beam is not None) else "_",
                    "goal pol": goal_pol if (goal_pol is not None) else "_",
                    "sat pin": sat_pin if (sat_pin is not None) else "_",
                    "beam pin": beam_pin if (beam_pin is not None) else "_",
                    "pol pin": pol_pin if (pol_pin is not None) else "_",
                    "sw version": sw_version,
                    "vno": vno,
                }
            )
            continue

        # Compare actual and goal values to determine whether each
        # modem is already on the beam it's supposed to be on.
        (matched if goal_sat == orig_sat and goal_beam == orig_beam else mismatched).append(
            {
                "mac": mac,
                "goal sat": goal_sat,
                "goal beam": goal_beam,
                "goal pol": goal_pol,
                "orig sat": orig_sat,
                "orig beam": orig_beam,
                "orig pol": orig_pol,
                "sat pin": sat_pin if (sat_pin is not None) else "_",
                "beam pin": beam_pin if (beam_pin is not None) else "_",
                "pol pin": pol_pin if (pol_pin is not None) else "_",
                "sw version": sw_version,
                "vno": vno,
            }
        )

    # Print and return the results.
    print_modems_verbose(
        mismatched + matched + ambitionless + goal_on_different_satellite + failed_to_check
    )
    if mismatched:
        print(f" \n{list_macs(mismatched)} not on goal beam")
    if matched:
        print(f" \n{list_macs(matched)} already on goal beam")
    if ambitionless:
        print(f" \nno goal beam could be determined for {list_macs(ambitionless)}")
    if goal_on_different_satellite:
        print(
            f" \nskipping {list_macs(goal_on_different_satellite)} because helping modems"
            " move to beams on a different satellite is outside the scope of this job"
        )
    if failed_to_check:
        print(f" \nfailed to check actual and goal beam for {list_macs(failed_to_check)}")
    return mismatched, matched, ambitionless, goal_on_different_satellite, failed_to_check


def clear_beam_pinnings(beam_drift_db, drifted_modems):
    """
    Step #2 - Temporarily clear the goal beams of drifted modems in ACS so they can stop
              trying to move to a beam that they're unable to get online on. We need them
              to get into a stable state on their current (bad) beam in order to fix their
              LKG files so they can move to the good beam.

    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :param beam_drift_db: an instance of the BeamDriftDb class
    :return: a list of dictionaries representing the modems whose beam
             pinnings were cleared successfully and a list of dictionaries
             representing the modems whose beam pinnings were not
    """
    cleared = []
    already_cleared = []
    failed = []
    for modem in drifted_modems:

        # Before clearing the beam pinnings, record the original goal sat and beam for
        # future reference, since this information will be removed from the ACS database.
        beam_drift_db.update_goal(
            modem["mac"],
            modem["goal sat"],
            modem["goal beam"],
            modem["goal pol"],
            verbose=common_utils.is_job_verbose(),
        )

        # Attempt to clear the pinnings if they aren't already.
        if modem["beam pin"] or modem["goal pol"] != "NOT_SET":
            if cmt_utils.clear_beam_pinning(modem["mac"]):
                cleared.append(modem)
            else:
                failed.append(modem)
        else:
            already_cleared.append(modem)

    # Print and return the results.
    if cleared:
        print(f" \ncleared beam pinning for {list_macs(cleared)}")
    if already_cleared:
        print(f" \n{list_macs(already_cleared)} already cleared prior to this run of job")
    if failed:
        print(f" \nfailed to clear beam pinning for {list_macs(failed)}")
    return cleared + already_cleared, failed


def pin_to_goal_beams(modems_on_goal_beams):
    """
    Step #3 - Ensure that modems already on their goal beams are pinned to them in ACS.

    :param modems_on_goal_beams: a list of dictionaries that represent
                                 modems that are on their intended beams
    :return: a list of dictionaries representing the modems whose beam pinnings were updated
             successfully, a list of dictionaries representing the modems whose beam pinnings
             already matched their goal beams, and a list of dictionaries representing modems
             whose beam pinnings we failed to update to their goal beams
    """
    pinned = []
    already_matched = []
    failed = []
    for modem in modems_on_goal_beams:
        mac = modem["mac"]
        goal_beam = modem["goal beam"]
        goal_pol = modem["goal pol"]

        # Determine whether or not modems are already pinned to their goal sat and beam.
        beam_pinned_to_goal = modem["beam pin"] == goal_beam

        # Attempt to pin modems to their goal sat and beam if they aren't already.
        if beam_pinned_to_goal:
            already_matched.append(modem)
        elif cmt_utils.pin_beam(mac, goal_beam, goal_pol):
            pinned.append(modem)
        else:
            failed.append(modem)

    # Print and return the results.
    if pinned:
        print(f" \npinned {list_macs(pinned)} to goal beam in ACS")
    if already_matched:
        print(f" \n{list_macs(already_matched)} already pinned to goal beam")
    if failed:
        print(f" \nfailed to pin {list_macs(failed)} to goal beam")
    return pinned, already_matched, failed


def wait_till_modems_are_online(drifted_modems, max_wait_secs):
    """
    Step #4, Step #6, and Step #13 - Wait for modems to come online.

    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :param max_wait_secs: a number representing the maximum number of
                          seconds to wait for modems to come online
    :return: a list of dictionaries representing the modems that came online before the waiting
             period was up and a list of dictionaries representing the modems that didn't
    """

    # Until we've checked, assume all modems might be offline.
    online_modems = []
    offline_modems = drifted_modems

    # Wait until there are no more offline modems or until we've hit our time limit.
    start_time = int(time())
    current_time = start_time
    end_time = current_time + max_wait_secs
    while current_time < end_time and offline_modems:
        sleep(ONLINE_CHECK_INTERVAL_SECS)
        current_time = int(time())
        print(
            f" \n{current_time - start_time}/{max_wait_secs} seconds elapsed with"
            f" {len(online_modems)}/{len(drifted_modems)} modems online"
        )

        # Check if any new modems have come online between sleep intervals.
        just_came_online = []
        for modem in offline_modems:
            if cmt_utils.ping_modem(modem["mac"]):
                just_came_online.append(modem)
        if just_came_online:
            print(f" \n{list_macs(just_came_online)} came online")

        # Check if any previously online modems have fallen offline between sleep intervals.
        fell_back_offline = []
        for modem in online_modems:
            if not cmt_utils.ping_modem(modem["mac"]):
                fell_back_offline.append(modem)
        if fell_back_offline:
            print(f" \n{list_macs(fell_back_offline)} fell back offline")

        # Update the lists of modems that are currently online and offline.
        for modem in just_came_online:
            online_modems.append(modem)
        for modem in fell_back_offline:
            online_modems.remove(modem)
        offline_modems = [modem for modem in drifted_modems if modem not in online_modems]

    # Print and return the results.
    if offline_modems:
        print(f" \n{list_macs(offline_modems)} did not come online after {max_wait_secs} seconds")
    if online_modems:
        print(
            f" \nsleeping for {WAIT_FOR_NEWLY_ONLINE_MODEM_TO_STABILIZE_SECS}"
            f" more seconds to give newly online modems a chance to stabilize"
        )
        sleep(WAIT_FOR_NEWLY_ONLINE_MODEM_TO_STABILIZE_SECS)
    return online_modems, offline_modems


def restart_cwmp(jumpbox, drifted_modems):
    """
    Step #5 - Restart CWMP on drifted modems.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a list of dictionaries representing the modems on which CWMP was restarted
             successfully and a list of dictionaries representing the modems on which it wasn't
    """
    macs = [modem["mac"] for modem in drifted_modems]
    succeeded_macs, failed_macs = restart_cwmp_on_macs(jumpbox, macs)
    succeeded = [modem for modem in drifted_modems if modem["mac"] in succeeded_macs]
    failed = [modem for modem in drifted_modems if modem["mac"] in failed_macs]
    if succeeded:
        print(" \nwaiting 3 minutes to give CWMP a chance to fix modems")
        sleep(180)
    return succeeded, failed


def restart_cwmp_on_macs(jumpbox, macs):
    """
    Step #5 - Restart CWMP on drifted modems.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param macs: a list of strings representing mac addresses

    :return: a list of strings representing the mac address of modems on which CWMP was
             restarted successfully and a list of strings representing the mac addresses
             of the modems on which it wasn't
    """
    failed = []
    succeeded = []

    # Use mtool to restart CWMP on these modems.
    if macs:
        mac_list_file_name = "ut_macs_restart_cwmp"
        batches = common_utils.batches(macs, get_mtool_batch_size())
        for batch in batches:
            mtool_utils.create_mac_list_file(jumpbox, mac_list_file_name, batch)
            output, _ = mtool_utils.run_mtool_command(
                jumpbox,
                f"-a run_commands -m {mac_list_file_name}"
                " -C 'killall vstat; cwmpclient_setup RESTART'",
            )

            # Examine the output of the mtool command to see which modems we succeeded on.
            for mac in batch:
                (
                    succeeded
                    if mtool_utils.check_if_cmd_no_output_succeeded(output, mac)
                    else failed
                ).append(mac)

    # Print and return the results.
    if failed:
        print(f" \ncould not restart CWMP on {common_utils.readable_list(failed)}")
    if succeeded:
        print(f" \nrestarted CWMP on {common_utils.readable_list(succeeded)}")

    return succeeded, failed


def check_if_goal_beam_in_lkg(
    jumpbox, beam_drift_db, drifted_modems
):  # pylint: disable=too-many-locals
    """
    Step #8 - Check whether goal beam info is missing from LKG files.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param beam_drift_db: an instance of the BeamDriftDb class
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a list of dictionaries representing modems that don't have their goal beam in their
             LKG file, a list of dictionaries representing modems that do have their goal beam in
             their LKG file and whose goal beam has an opposite polarization to that of their
             current beam, a list of dictionaries representing modems that do have their goal beam
             in their LKG file and whose goal beam has the same polarization as that of their
             current beam, and a list of dictionaries representing modems whose LKG files we were
             unable to examine
    """
    goal_beam_not_in_lkg = []
    goal_beam_in_lkg_same_pol = []
    goal_beam_in_lkg_opp_pol = []
    failed_to_check = []

    # Get the subset of modems that are trying to move to each goal beam. We'll run mtool
    # on batches of all the modems with the same goal beam since they'll share an LKG file.
    goal_beams = {(modem["goal sat"], modem["goal beam"]) for modem in drifted_modems}
    for sat, beam in goal_beams:
        modems = [
            modem
            for modem in drifted_modems
            if modem["goal sat"] == sat and modem["goal beam"] == beam
        ]

        # Use mtool to grep for these modems' goal beam in their LKG file.
        mac_list_file_name = f"ut_macs_sat_{sat}_beam_{beam}"
        mtool_utils.create_mac_list_file(
            jumpbox, mac_list_file_name, [modem["mac"] for modem in modems]
        )
        output, _ = mtool_utils.run_mtool_command(
            jumpbox,
            f"-a run_commands -m {mac_list_file_name} -C "
            f"\"egrep 'Neighbor_Beam_Id = {beam}|Beam_Id  = {beam}' {LKG_FILE_PATH_ON_MODEM}\"",
        )

        # Examine the output of the mtool command to see which modems have their goal
        # beam info in their LKG file already.
        for modem in modems:
            if is_goal_beam_in_mtool_output(output, modem["mac"], beam):
                opp_pol = str(modem["orig beam"])[1] != str(beam)[1]
                if opp_pol:
                    goal_beam_in_lkg_opp_pol.append(modem)
                else:
                    goal_beam_in_lkg_same_pol.append(modem)
                beam_drift_db.flag_unhelpable_modem(
                    modem["mac"], modem["goal sat"], opp_pol, verbose=common_utils.is_job_verbose()
                )
            else:
                goal_beam_not_in_lkg.append(modem)

    # Print and return the results.
    if goal_beam_not_in_lkg:
        print(f" \n{list_macs(goal_beam_not_in_lkg)} did not have goal beam in LKG file")
    if goal_beam_in_lkg_same_pol:
        print(
            f" \n{list_macs(goal_beam_in_lkg_same_pol)}"
            f" had goal beam of same polarization in LKG file"
        )
    if goal_beam_in_lkg_opp_pol:
        print(
            f" \n{list_macs(goal_beam_in_lkg_opp_pol)}"
            f" had goal beam of opposite polarization in LKG file"
        )
    if failed_to_check:
        print(f" \nfailed to check whether {list_macs(failed_to_check)} had goal beam in LKG file")

    return (
        goal_beam_not_in_lkg,
        goal_beam_in_lkg_same_pol,
        goal_beam_in_lkg_opp_pol,
        failed_to_check,
    )


def get_good_lkg_files(jumpbox, drifted_modems):  # pylint: disable=too-many-locals
    """
    Step #9 - For each beam to which any modem in this batch is trying to move,
              obtain an LKG file from a modem currently online on that beam.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    """

    # Clear any previous results
    jumpbox.clear_any_previous_results(prefix="sat_", suffix=".conf")

    # Get the set of beams for which we need to find modems with good LKG files.
    desired_beams = {(modem["goal sat"], modem["goal beam"]) for modem in drifted_modems}

    # Attempt to find a good LKG file on each beam.
    found_beams = []
    failed_beams = []
    for sat, beam in desired_beams:
        print(f" \ntrying to download a good LKG for sat {sat} beam {beam}")
        local_file_name = f"sat_{sat}_beam_{beam}.conf"

        # Ask CM-T for a group of online modems on the desired beam. We only need one LKG file, but
        # we ask for multiple modems so that we can try to reach them one at a time and stop once
        # we've succeeded at downloading an LKG from one of them.
        macs = cmt_utils.get_modems(
            sat_id=sat,
            beam=beam,
            limit=MAX_LKG_PULL_ATTEMPTS_PER_BEAM,
            verbose=common_utils.is_job_verbose(),
        )
        shuffle(macs)
        found = False
        for mac in macs:
            mtool_utils.run_mtool_command(
                jumpbox,
                f"-a get_file -M {mac} -r {LKG_FILE_PATH_ON_MODEM} -l {local_file_name}",
                verbose=common_utils.is_job_verbose(),
            )

            # Once we've obtained a valid LKG file for this beam, we move on to the next beam.
            output, _ = jumpbox.run_command(f"grep 'Beam_Id  = {beam}' {mac}_{local_file_name}")
            if any(f"Beam_Id  = {beam}" in line for line in output):
                _, errors = jumpbox.run_command(f"mv {mac}_{local_file_name} {local_file_name}")
                if not errors:
                    found = True
                    print(f" \n\t-> grabbed one from {mac}")
                    break

        # Keep track of which beams we were and weren't able to find good LKG files on.
        if not found:
            print(" \n\t-> failed")
        (found_beams if found else failed_beams).append((sat, beam))

    # Determine which modems had LKG files found for them.
    succeeded = [
        modem for modem in drifted_modems if (modem["goal sat"], modem["goal beam"]) in found_beams
    ]
    failed = [
        modem for modem in drifted_modems if (modem["goal sat"], modem["goal beam"]) in failed_beams
    ]

    # Print and return the results.
    if found_beams:
        print(
            " \nsuccessfully retrieved good LKG file on"
            f" {list_beams(found_beams)} for {list_macs(succeeded)}"
        )
    if failed_beams:
        print(
            " \nfailed to retrieve good LKG file on"
            f" {list_beams(failed_beams)} for {list_macs(failed)}"
        )
    return succeeded, failed


def back_up_lkg_files(jumpbox, drifted_modems):
    """
    Step #10 - Back up the modems' existing LKG files just in case something goes
              wrong when we're trying to replace them with new LKG files in Step #11.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a list of dictionaries representing the modems whose LKG files we successfully backed
             up and a list of dictionaries representing the modems whose LKG files we didn't
    """
    failed = []
    succeeded = []

    # Use mtool to back up the LKG files on these modems.
    if drifted_modems:
        mac_list_file_name = "ut_macs_back_up_lkg"
        batches = common_utils.batches(drifted_modems, get_mtool_batch_size())
        for batch in batches:
            mtool_utils.create_mac_list_file(
                jumpbox, mac_list_file_name, [modem["mac"] for modem in batch]
            )
            output, _ = mtool_utils.run_mtool_command(
                jumpbox,
                f"-a run_commands -m {mac_list_file_name}"
                f" -C 'cp {LKG_FILE_PATH_ON_MODEM} {LKG_FILE_PATH_ON_MODEM}.bk'",
            )

            # Examine the output of the mtool command to see which modems we succeeded on.
            for modem in batch:
                (
                    succeeded
                    if mtool_utils.check_if_cmd_no_output_succeeded(output, modem["mac"])
                    else failed
                ).append(modem)

    # Print and return the results.
    if succeeded:
        print(f" \nbacked up LKG file on {list_macs(succeeded)}")
    if failed:
        print(f" \ncould not back up LKG file on {list_macs(failed)}")
    return succeeded, failed


def push_good_lkg_files(jumpbox, drifted_modems):
    """
    Step #11 - Push the good LKG files that we obtained in Step #9 onto the drifted modems. A good
              LKG file is one that comes from a modem that's online on the beam to which the
              drifted modem needs to move. This should give the modem the information it needs to
              successfully get online on the beam to which it's trying to move.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a list of dictionaries representing the modems to which we successfully pushed new
             LKG files and a list of dictionaries representing the modems to which we didn't
    """
    error_pushing_lkg = []
    succeeded = []

    # Get the subset of modems that are trying to move to each goal beam. We'll run mtool
    # on batches of all the modems with the same goal beam since they'll share an LKG file.
    goal_beams = {(modem["goal sat"], modem["goal beam"]) for modem in drifted_modems}
    for sat, beam in goal_beams:
        modems = [
            modem
            for modem in drifted_modems
            if modem["goal sat"] == sat and modem["goal beam"] == beam
        ]

        # Use mtool to push the good LKG file to this batch of modems.
        mac_list_file_name = f"ut_macs_sat_{sat}_beam_{beam}"
        mtool_utils.create_mac_list_file(
            jumpbox, mac_list_file_name, [modem["mac"] for modem in modems]
        )
        output, _ = mtool_utils.run_mtool_command(
            jumpbox,
            f"-a put_file -m {mac_list_file_name} -l sat_{sat}_beam_{beam}.conf"
            f" -r {LKG_FILE_PATH_ON_MODEM}",
        )

        # Examine the output of the mtool command to see which modems received the file.
        for modem in modems:
            (
                succeeded
                if f"Put file succeeded to {mtool_utils.format_mac_addr(modem['mac'])}." in output
                else error_pushing_lkg
            ).append(modem)

    # Print and return the results.
    if succeeded:
        print(f" \npushed good LKG file to {list_macs(succeeded)}")
    if error_pushing_lkg:
        print(f" \nerror pushing good LKG file to {list_macs(error_pushing_lkg)}")
    return succeeded, error_pushing_lkg


def reboot_modems(jumpbox, drifted_modems):
    """
    Step #12 - Reboot modems. Now that the modems have good LKG files on them,
              they'll hopefully come back on the correct beam after we reboot them.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    """
    succeeded = []
    failed = []

    # Use mtool to reboot the modems.
    if drifted_modems:
        mac_list_file_name = "ut_macs_reboot"
        batches = common_utils.batches(drifted_modems, get_mtool_batch_size())
        for batch in batches:
            mtool_utils.create_mac_list_file(
                jumpbox, mac_list_file_name, [modem["mac"] for modem in batch]
            )
            output, _ = mtool_utils.run_mtool_command(
                jumpbox, f"-a run_commands -m {mac_list_file_name} -C reboot"
            )

            # Examine the output of the mtool command to
            # see which modems were rebooted successfully.
            for modem in batch:
                (
                    succeeded
                    if mtool_utils.check_if_cmd_had_expected_output(
                        output, modem["mac"], "called at"
                    )
                    else failed
                ).append(modem)

        # Sleep to give modems a chance to begin rebooting.
        sleep(30)

    # Print the results.
    if succeeded:
        print(f" \ndefinitely rebooted {list_macs(succeeded)}")
    if failed:
        print(f" \nmay have rebooted {list_macs(failed)}")


def re_pin_beams(drifted_modems):
    """
    Step #14 - Restore the modems' correct beam pinnings in ACS, undoing what we did in Step #2.

    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a list of dictionaries representing the modems whose beam
             pinnings were restored successfully and a list of dictionaries
             representing the modems whose beam pinnings were not
    """
    repinned = []
    failed = []
    for modem in drifted_modems:
        if cmt_utils.pin_beam(modem["mac"], modem["goal beam"], modem["goal pol"]):
            repinned.append(modem)
        else:
            failed.append(modem)

    # Print and return the results.
    if repinned:
        print(f" \nre-pinned {list_macs(repinned)} to goal beam in ACS")
    if failed:
        print(f" \nfailed to re-pin {list_macs(failed)} to goal beam")
    return repinned, failed


def check_beams_match_on_modem(  # pylint: disable=too-many-branches,too-many-locals
    jumpbox, beam_drift_db, drifted_modems, flag_pol_swap_issue_on_failure
):
    """
    Step #7 & Step #15 - Use utstat -L to check whether the modems that we rebooted in Step #12
                         came back online on the correct beam. If they didn't, check whether the
                         beam that they did come online on has a polarization opposite to that of
                         the beam to which they failed to move. If it does, this could indicate a
                         broken polarity switch on an AB modem.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param beam_drift_db: an instance of the BeamDriftDb class
    :param drifted_modems: a list of dictionaries that represent modems
                           that have drifted from their intended beams
    :param flag_pol_swap_issue_on_failure: True to flag a possible polarization switcher issue on
                                           failure, False otherwise
    :return: a list of dictionaries representing modems on their goal beam, a list of dictionaries
             representing modems on the wrong beam of an opposite polarization to that of their
             goal beam, a list of dictionaries representing modems that are on the wrong beam of
             the same polarization as that of their goal beam, and a list of modems whose beam
             we were unable to check using utstat -L
    """
    on_goal_beam = []
    on_wrong_beam_opp_pol = []
    on_wrong_beam_same_pol = []
    failed_to_check_beam = []

    # Use mtool to check the modems' beam IDs.
    if drifted_modems:  # pylint: disable=too-many-nested-blocks
        mac_list_file_name = "ut_macs_check_mismatch"
        batches = common_utils.batches(drifted_modems, get_mtool_batch_size())
        for batch in batches:
            mtool_utils.create_mac_list_file(
                jumpbox, mac_list_file_name, [modem["mac"] for modem in batch]
            )
            output, _ = mtool_utils.run_mtool_command(
                jumpbox, f"-a run_commands -m {mac_list_file_name} -C 'utstat -L | grep beamId'"
            )

            # Examine the output of the mtool command to see whether each modem came up on its goal
            # beam. If it didn't, compare the polarizations of the actual and goal beams to provide
            # evidence as to whether this modem is likely to have a broken polarity switch.
            for modem in batch:
                beam = get_beam_from_mtool_output(output, modem["mac"])
                if not beam:
                    failed_to_check_beam.append(modem)
                elif beam == modem["goal beam"]:
                    on_goal_beam.append(modem)
                else:
                    try:
                        goal_pol = str(modem["goal beam"])[1]
                        actual_pol = str(beam)[1]
                        opp_pol = actual_pol != goal_pol

                        if opp_pol:
                            on_wrong_beam_opp_pol.append(modem)
                        else:
                            on_wrong_beam_same_pol.append(modem)
                        beam_drift_db.flag_unhelpable_modem(
                            modem["mac"],
                            modem["goal sat"],
                            opp_pol,
                            verbose=common_utils.is_job_verbose(),
                        )

                    except IndexError:
                        failed_to_check_beam.append(modem)

    # Print and return the results.
    if on_goal_beam:
        print(f" \n{list_macs(on_goal_beam)} on goal beam")
    if flag_pol_swap_issue_on_failure:
        if on_wrong_beam_opp_pol:
            print(
                f" \n{list_macs(on_wrong_beam_opp_pol)}"
                f" failed to move to beam of opposite polarization"
            )
        if on_wrong_beam_same_pol:
            print(
                f" \n{list_macs(on_wrong_beam_same_pol)}"
                f" failed to move to beam of same polarization"
            )
    elif on_wrong_beam_opp_pol or on_wrong_beam_same_pol:
        print(f" \n{list_macs(on_wrong_beam_opp_pol + on_wrong_beam_same_pol)} on wrong beam")
    if failed_to_check_beam:
        print(f" \nfailed to check whether {list_macs(failed_to_check_beam)} on goal beam")
    return on_goal_beam, on_wrong_beam_opp_pol, on_wrong_beam_same_pol, failed_to_check_beam


def checks_beams_pinned_to_goals(drifted_modems):
    """
    Step #16 - Check whether the beam re-pinnings in Step #14 went through in ACS.

    :param drifted_modems: a list of dictionaries that represent modems
                           that have drifted from their intended beams
    :return: a list of dictionaries representing modems pinned to their goal beam, a list of
             dictionaries representing modems not pinned to their goal beam, and a list of
             dictionaries representing modems whose beam pinnings we were unable to check
    """
    pinned_to_goal = []
    not_pinned_to_goal = []
    failed_to_check = []
    for modem in drifted_modems:

        # Retrieve the modem's CPE config from CM-T.
        config_response = cmt_utils.get_cpe_config(modem["mac"])
        if config_response.status_code != 200:
            failed_to_check.append(modem)
            common_utils.print_http_response(config_response)
            continue

        # Parse the modem's current satellite and beam pinnings in ACS from it's CPE config.
        pinned_sat = cmt_utils.parse_goal_sat_id_from_cpe_config(config_response)
        pinned_beam = cmt_utils.parse_goal_beam_from_cpe_config(config_response)

        # Compare the modem's current pinnings in ACS to the goal
        # pinnings we determined for it at the beginning of this job.
        goal_sat = modem["goal sat"]
        goal_beam = modem["goal beam"]
        if ((not pinned_beam) or (pinned_beam != goal_beam)) or (
            pinned_sat and (pinned_sat != goal_sat)
        ):
            print(f" \nexpected {modem['mac']} to be pinned to {goal_sat} {goal_beam}")
            common_utils.print_http_response(config_response)
            not_pinned_to_goal.append(modem)
        else:
            pinned_to_goal.append(modem)

    # Print and return the results.
    if pinned_to_goal:
        print(f" \n{list_macs(pinned_to_goal)} pinned to goal beam")
    if not_pinned_to_goal:
        print(f" \n{list_macs(not_pinned_to_goal)} not pinned to goal beam")
    if failed_to_check:
        print(f" \nfailed to check if {list_macs(failed_to_check)} pinned to goal beam")
    return pinned_to_goal, not_pinned_to_goal, failed_to_check


def print_modems_verbose(drifted_modems):
    """
    Print a list of drifted modems in a format that aids further processing.

    :param drifted_modems: :param drifted_modems: a list of dictionaries that represent modems
                           that have drifted from their intended beams
    """
    print(" \n[mac (original -> goal) (initial pinning) software vno]")
    print(
        " \n".join(
            [
                f"{modem['mac']} ({modem['orig sat']} {modem['orig beam']} {modem['orig pol']}"
                f" -> {modem['goal sat']} {modem['goal beam']} {modem['goal pol']})"
                f" (pinned to {modem['sat pin']} {modem['beam pin']} {modem['pol pin']})"
                f" {modem['sw version']} {modem['vno']}"
                for modem in drifted_modems
            ]
        )
    )
    print(" \n[mac, goal sat, goal beam, goal pol]")
    print(
        " \n".join(
            [
                f"{modem['mac']}, {modem['goal sat']}, {modem['goal beam']}, {modem['goal pol']}"
                for modem in drifted_modems
            ]
        )
    )
    print(" \n[macs only] ")
    print(" \n".join([modem["mac"] for modem in drifted_modems]))


def get_list_of_drifted_modems():
    """
    Get the input list of modems on which to run the job from the ACS database,
    the job input, or both (depending on the chosen job parameters) minus those
    in the blocklist.

    This is a helper function to get_modems_on_wrong_beam().
    Do not call this function directly; call get_modems_on_wrong_beam() instead.

    :return: a list of tuples whose first element is a string representing the MAC address of
             a modem that we want to help move to its correct beam and whose second and third
             elements contain numbers representing the goal sat ID and goal beam or None, None
    """

    # Get the input list of modems (and, if provided, their
    # goal sat IDs and beams) from the Jenkins job parameter.
    modems = get_user_provided_modems()

    # If a nonzero parameter for the number of mismatched modems
    # to retrieve from the ACS DB was supplied, retrieve that many.
    if should_get_drifted_modems_from_acs_db():
        drifted_modems_from_db = get_drifted_modems_from_acs_db()

        # Combine the user provided modems with the ACS DB provided modems. User
        # provided modems take precedence since they're considered an override.
        user_provided_macs = [modem[0] for modem in modems]
        modems += [modem for modem in drifted_modems_from_db if modem[0] not in user_provided_macs]

    # Filter out modems in the blocklist.
    return [modem for modem in modems if modem[0] not in get_blocklist()]


def get_user_provided_modems():
    """
    Get the list of modems from the Jenkins job parameter.

    This is a helper function to get_modems_on_wrong_beam (Step #1).

    :return: a list of tuples whose first element is a string representing the MAC address of
             a modem that we want to help move to its correct beam and whose second and third
             elements contain numbers representing the goal sat ID and goal beam or None, None
    """
    modems = []

    # Each line in the text field parameter represents a different modem.
    input_modems = os.getenv("macs")
    if input_modems:
        lines = input_modems.strip().split("\n")
        for line in lines:

            # If a line has a goal override specified, it'll look like: mac, goal_sat, goal_beam
            values = [x.strip() for x in line.split(",")]

            # The MAC address is neither case nor colon sensitive
            mac = values[0].replace(":", "").upper()

            # If there's an empty line, just skip it.
            if not mac:
                continue

            # Make sure that each line either contains a single
            # MAC or a MAC plus numerical sat and beam IDs
            if len(values) == 1:
                modems.append((mac, None, None, None))
            else:
                try:
                    modems.append((mac, int(values[1]), int(values[2]), values[3].upper()))
                except (IndexError, ValueError):
                    print(
                        " \nError: Each line should contain a single mac"
                        f" or 'mac, goal_sat, goal_beam, goal_pol'. Ignoring '{line}'"
                    )

        # Ensure there are no duplicate MACs, because that could cause chaotic job behavior.
        if len({modem[0] for modem in modems}) < len(modems):
            raise RuntimeError("ERROR: job parameter contains duplicate MAC addresses")

    return modems


def get_drifted_modems_from_acs_db():
    """
    Retrieve a list of modems that are on the wrong beam from the ACS database.

    :return: a list of tuples containing a string and two numbers
             (mac, goal satellite ID, goal beam, goal pol)
    """

    # Verify that we're running the job in prod.
    environment = common_utils.get_expected_env_var("environment")
    if environment != "prod":
        print(
            " \nwe can only pull drifted modems from the ACS database if we're"
            f" running the job in prod (we're currently in {environment})"
        )
        return []

    # Attempt to connect to the ACS database.
    acs_db = AcsDb()
    if not acs_db.database.is_connected():
        return []

    # Get beam mismatched modems from the ACS (up to the specified maximum quantity).
    drifted_modems = acs_db.get_drifted_modems(
        limit=common_utils.get_expected_env_var("max_modems_from_acs_db")
    )
    acs_db.database.disconnect()
    results = []
    for modem in drifted_modems:
        try:
            mac = modem["cid"]
            goal_sat = modem["PrimarySatelliteID"]
            goal_beam = modem["PrimaryBeamIDPending"] or modem["PrimaryBeamID"]
            goal_pol = modem["PrimaryBeamPolarizationPending"] or modem["PrimaryBeamPolarization"]
            goal_sat_id = int(goal_sat) if ((goal_sat is not None) and goal_sat.isdigit()) else None
            goal_beam_id = (
                int(goal_beam) if ((goal_beam is not None) and goal_beam.isdigit()) else None
            )
            results.append((mac, goal_sat_id, goal_beam_id, goal_pol))
        except KeyError as ex:
            print(f" \nERROR: failed to pull beam mismatched modems from ACS database\n{ex}")
            break
    return results


def get_blocklist():
    """
    Get the list of modems to exclude from the job from the Jenkins job parameter.

    :return: a list of strings representing the MAC addresses
             of modems to exclude from this run of the job
    """

    # Each line in the text field parameter contains a MAC address.
    blocklist_input = os.getenv("blocklist")
    if not blocklist_input:
        return []
    lines = common_utils.get_expected_env_var("blocklist").strip().split("\n")
    macs = []
    for line in lines:
        mac = line.strip().replace(":", "").upper()  # Format MAC address
        if mac:  # ignore empty lines
            macs.append(mac)
    return macs


def should_get_drifted_modems_from_acs_db():
    """
    Determine whether or not we should pull a list of beam mismatched modems
    from the ACS database based on whether that job parameter was chosen.

    :return: True if we should use the ACS database to get a list of drifted
             modems, False otherwise
    """
    return common_utils.get_expected_env_var("max_modems_from_acs_db") != "0"


def get_wait_secs_for_online_after_clear():
    """
    Determine how long to wait for modems to come back
    online after we clear their beam pinnings in Step #2.

    :return: a number representing how many seconds to wait for the modems to come
             back online after we clear their beam pinnings in Step #2
    """
    try:
        wait_minutes_after_clear = common_utils.get_expected_env_var("wait_minutes_after_clear")
        wait_secs_after_clear = int(wait_minutes_after_clear) * SECONDS_IN_A_MINUTE
        return wait_secs_after_clear
    except (RuntimeError, ValueError, TypeError) as ex:
        print(ex)
        return DEFAULT_WAIT_FOR_ONLINE_SECS


def get_wait_secs_for_online_after_cwmp_restart():
    """
    Determine how long to wait for modems to come back
    online after we restart CWMP in Step #5.

    :return: a number representing how many seconds to wait for the modems to come
             back online after we restart CWMP in Step #5
    """
    try:
        wait_minutes_after_cwmp_restart = common_utils.get_expected_env_var(
            "wait_minutes_after_cwmp_restart"
        )
        wait_secs_after_cwmp_restart = int(wait_minutes_after_cwmp_restart) * SECONDS_IN_A_MINUTE
        return wait_secs_after_cwmp_restart
    except (RuntimeError, ValueError, TypeError) as ex:
        print(ex)
        return DEFAULT_WAIT_FOR_ONLINE_SECS


def get_wait_secs_for_online_after_lkg_push():
    """
    Determine how long to wait for modems to come back online after we
    reboot them in Step #12 after pushing good LKG files to them in Step #11.

    :return: a number representing how many seconds to wait for the modems to
             come back online we pushed LKG files to them and rebooted them.
    """
    try:
        wait_minutes_after_clear = common_utils.get_expected_env_var("wait_minutes_after_lkg_push")
        wait_secs_after_clear = int(wait_minutes_after_clear) * SECONDS_IN_A_MINUTE
        return wait_secs_after_clear
    except (RuntimeError, ValueError, TypeError) as ex:
        print(ex)
        return DEFAULT_WAIT_FOR_ONLINE_SECS


def get_beam_from_mtool_output(output, mac):
    """
    By looking through the output of running a command via mtool to
    get modems' beam IDs, obtain the beam ID for a particular modem.

    This is a helper function to check_beams_match_on_modem (Step #7 & Step #15).

    :param output: a string representing the output of running the utstat -L
                   command on a list of modems via mtool
    :param mac: a string representing the MAC address of one of those modems
    :return: a number representing the modem's beam ID,
             or None if it couldn't be determined
    """
    for i in range(len(output) - 3):
        if (
            mtool_utils.format_mac_addr(mac) in output[i]
            and "swVersion:" in output[i + 1]
            and "beamId:" in output[i + 3]
        ):
            try:
                return int(output[i + 3].split()[1])
            except (IndexError, ValueError):
                return None
    return None


def is_goal_beam_in_mtool_output(output, mac, beam):
    """
    Look through the output of running a command via mtool to check
    whether the modem's goal beam is in its Last Known Good file.

    This is a helper function to check_beams_match_on_modem (Step #7 & Step #15).

    :param output: a string representing the output of searching
                   for the beam in the modem's LKG file
    :param mac: a string representing the MAC address of one of those modems
    :param beam: a number representing the beam ID that we're looking
                 for in the LKG file for the modem in question
    :return: True if the modem has its goal beam in its LKG file, False otherwise
    """
    for i in range(len(output) - 3):
        if (
            mtool_utils.format_mac_addr(mac) in output[i]
            and "swVersion:" in output[i + 1]
            and "Beam_Id" in output[i + 3]
            and str(beam) in output[i + 3]
        ):
            return True
    return False


def should_preserve_beam_pinnings():
    """
    Determine based on a checkbox parameter to the job whether or not we should restore
    all the modems whose beam pinnings were cleared to their original beams by the end
    of the job, regardless of whether we were able to put good LKG files on them.

    The upside of this is that the ACS database will preserve the record of what beam they're
    trying to get to, and the downside is that the modems are less likely to come online in
    this state. However, it's the state in which the job found them, so they aren't worse off.

    :return: True to restore all modems' beam pinnings in ACS, False to only restore
             the beam pinning of modems onto which we copied a good LKG file
    """
    return common_utils.check_expected_env_bool("preserve_pinnings")


def is_fast_run():
    """
    Determine based on a checkbox parameter to the job whether or not we should completely
    skip the steps that deal with LKG files in order to focus on restarting CWMP on as many
    modems as possible.

    We can use this mode to manually run the job on as many modems as possible in the wake
    of an outage.

    :return: True to skip the LKG steps, False to do all the steps as normal
    """
    return common_utils.check_expected_env_bool("skip_lkg_steps")


def should_force_lkg_updates():
    """
    Determine based on a checkbox parameter to the job whether or not we should force LKG
    updates on all beam mismatched modems, including the ones that already have their goal
    beam in their LKG file.

    :return: True to update LKG files on modems that already have their goal beam in their
             current LKG file, False to only update modems that don't have their goal beam
             in their LKG file or about whose LKG file we're unsure
    """
    return common_utils.check_expected_env_bool("force_lkg_updates")


def get_mtool_batch_size():
    """
    Determine how many modems to give mtool at once, because
    sometimes it struggles when we give it too many at a time.

    :return: a number representing the max quantity of modems to pass to mtool
             commands at once during this run of the job. This is specified
             by a parameter to the job. If unspecified, a default is used.
    """
    if "mtool_batch_size" in os.environ:
        try:
            batch_size = int(common_utils.get_expected_env_var("mtool_batch_size"))
            return batch_size
        except (ValueError, TypeError) as ex:
            print(ex)
    return MTOOL_BATCH_SIZE_DEFAULT


def print_step(step, description):
    """
    This is a formatting helper function for indicating
    which step we're on in the console output of this job.

    :param step: a number representing what step we're on
    :param description: a string that briefly summarizes what this step entails
    """
    common_utils.print_heading(f"STEP #{step} — {description}")


def list_macs(drifted_modems):
    """
    Convert a list of modems into a grammatically correct noun phrase for printing.

    :param drifted_modems: a list of dictionaries that represent modems
                          that have drifted from their intended beams
    :return: a string that represents a list of MAC addresses
    """
    return common_utils.readable_list([modem["mac"] for modem in drifted_modems])


def list_beams(beam_tuples):
    """
    Convert a list of beams into a grammatically correct noun phrase for printing.

    :param beam_tuples: a list of tuples that contain numbers that represent satellite
                        IDs and beams on those satellites
    :return: a string that represents the input list of satellite and beam pairings
    """
    return common_utils.readable_list([f"sat {sat} beam {beam}" for sat, beam in beam_tuples])
