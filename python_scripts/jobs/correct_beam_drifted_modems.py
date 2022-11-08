"""
Contains functionality for attempting to correct modems that have drifted onto the wrong beam.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
import urllib3
from libs import common_utils
from libs.beam_drift_db import BeamDriftDb
from libs.jumpbox import Jumpbox
from libs import beam_drift_utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# pylint: disable=too-many-locals,too-many-statements,too-many-branches
def correct_drifted_modems():
    """
    Attempt to move drifted modems to their correct beams.
    """

    # Ensure all variables will be initialized in the finally block.
    jumpbox = None
    beam_drift_db = None
    already_matched_already_pinned = None
    already_matched_failed_to_pin = None
    no_initial_goal = None
    goal_on_different_satellite = None
    failed_to_check_start_state = None
    failed_to_clear = None
    offline_after_clear = None
    failed_to_restart_cwmp = None
    offline_after_cwmp_restart = None
    on_goal_beam_after_cwmp_restart = None
    failed_to_check_beam_after_cwmp_restart = None
    failed_to_back_up_lkg = None
    goal_beam_in_lkg_same_pol = None
    goal_beam_in_lkg_opp_pol = None
    no_lkg_found = None
    error_pushing_lkg = None
    failed_to_re_pin = None
    offline_after_reboot = None
    on_wrong_beam_opp_pol = None
    on_wrong_beam_same_pol = None
    failed_to_check_beam = None
    on_goal_beam = None
    already_matched_pin_success = None
    already_matched_pin_fail = None
    already_matched_pin_error = None
    not_pinned_to_goal = None
    unable_to_check_final_pinning = None
    pushed_lkg_files = []
    online_after_reboot = []

    try:
        # Step #1 - Get the list of modems on which to run
        # the job and confirm that they're on the wrong beam.
        beam_drift_utils.print_step(1, "checking whether input modems are on the wrong beam")
        modems = beam_drift_utils.get_list_of_drifted_modems()
        beam_drift_db = BeamDriftDb()
        (
            drifted_modems,
            already_matched,
            no_initial_goal,
            goal_on_different_satellite,
            failed_to_check_start_state,
        ) = beam_drift_utils.get_modems_on_wrong_beam(beam_drift_db, modems)

        # Step #2 - Temporarily clear the goal beams of drifted modems in ACS so they can stop
        #           trying to move to a beam that they're unable to get online on. We need them
        #           to get into a stable state on their current (bad) beam in order to fix their
        #           LKG files so they can move to the correct beam.
        beam_drift_utils.print_step(2, "clearing beam pinnings")
        cleared, failed_to_clear = beam_drift_utils.clear_beam_pinnings(
            beam_drift_db, drifted_modems
        )

        # Step #3 - Ensure that the modems that are already on their goal beams are pinned to them.
        beam_drift_utils.print_step(
            3, "ensuring modems already on their goal beams are pinned to them in ACS"
        )
        (
            already_matched_newly_pinned,
            already_matched_already_pinned,
            already_matched_failed_to_pin,
        ) = beam_drift_utils.pin_to_goal_beams(already_matched)

        # Step #4 - Wait for the modems whose beam pinnings we cleared in Step #2 to come online.
        beam_drift_utils.print_step(
            4, "waiting for modems to come online now that their beam pinnings are cleared"
        )
        online_after_clear, offline_after_clear = beam_drift_utils.wait_till_modems_are_online(
            cleared, beam_drift_utils.get_wait_secs_for_online_after_clear()
        )

        # Step #5 - Restart CWMP on drifted modems.
        beam_drift_utils.print_step(5, "restarting CWMP")
        jumpbox = Jumpbox()
        restarted_cwmp, failed_to_restart_cwmp = beam_drift_utils.restart_cwmp(
            jumpbox, online_after_clear
        )

        # Step #6 - If any modems were restarted by CWMP, wait for them to come online.
        beam_drift_utils.print_step(
            6, "waiting for any modems rebooted by CWMP to come back online"
        )
        (
            online_after_cwmp_restart,
            offline_after_cwmp_restart,
        ) = beam_drift_utils.wait_till_modems_are_online(
            restarted_cwmp, beam_drift_utils.get_wait_secs_for_online_after_cwmp_restart()
        )

        # Step #7 - Check whether modems are on the correct beam now.
        beam_drift_utils.print_step(
            7, "checking whether the CWMP restart got modems on the right beam"
        )
        (
            on_goal_beam_after_cwmp_restart,
            on_wrong_beam_opp_pol_after_cwmp_restart,
            on_wrong_beam_same_pol_after_cwmp_restart,
            failed_to_check_beam_after_cwmp_restart,
        ) = beam_drift_utils.check_beams_match_on_modem(
            jumpbox, beam_drift_db, online_after_cwmp_restart, flag_pol_swap_issue_on_failure=False
        )

        if beam_drift_utils.is_fast_run():
            # If the "fast run" box was checked, skip Step #8 - Step #13 & Step #15
            common_utils.print_heading("skipping Step #8 - Step #13")

        else:
            # Step #8 - Check if the modems have the goal beam in the LKG files. If they don't,
            #           we'll proceed with updating those LKG files in Step #11.
            beam_drift_utils.print_step(8, "check if goal beam info is missing from LKG file")
            (
                goal_beam_not_in_lkg,
                goal_beam_in_lkg_same_pol,
                goal_beam_in_lkg_opp_pol,
                unknown_if_goal_in_lkg,
            ) = beam_drift_utils.check_if_goal_beam_in_lkg(
                jumpbox,
                beam_drift_db,
                on_wrong_beam_same_pol_after_cwmp_restart
                + on_wrong_beam_opp_pol_after_cwmp_restart,
            )

            # Step #9 - For each beam to which any modem in this batch is trying to move,
            #           obtain an LKG file from a modem currently online on that beam.
            beam_drift_utils.print_step(
                9, "retrieving good LKG files from online modems on goal beams"
            )
            if beam_drift_utils.should_force_lkg_updates():
                modems_whose_lkg_we_want_to_update = (
                    goal_beam_not_in_lkg
                    + goal_beam_in_lkg_same_pol
                    + goal_beam_in_lkg_opp_pol
                    + unknown_if_goal_in_lkg
                )
            else:
                modems_whose_lkg_we_want_to_update = goal_beam_not_in_lkg + unknown_if_goal_in_lkg
            found_good_lkg, no_lkg_found = beam_drift_utils.get_good_lkg_files(
                jumpbox, modems_whose_lkg_we_want_to_update
            )

            # Step #10 - Back up the modems' existing LKG files just
            #            in case something goes wrong in Step #11.
            beam_drift_utils.print_step(10, "backing up existing LKG files on drifted modems")
            backed_up_lkg_files, failed_to_back_up_lkg = beam_drift_utils.back_up_lkg_files(
                jumpbox, found_good_lkg
            )

            # Step #11 - Push the good LKG files that we obtained in Step #9 onto the drifted
            #            modems. This should give them the information they need to successfully
            #            get online on the beam to which they're trying to move.
            beam_drift_utils.print_step(11, "pushing good LKG files to drifted modems")
            pushed_lkg_files, error_pushing_lkg = beam_drift_utils.push_good_lkg_files(
                jumpbox, backed_up_lkg_files
            )

            # Step #12 - Reboot modems. Now that the modems have good LKG files on them,
            #           they'll hopefully come back on the correct beam after we reboot them.
            beam_drift_utils.print_step(
                12, "rebooting drifted modems that now have good LKG files on them"
            )
            beam_drift_utils.reboot_modems(jumpbox, pushed_lkg_files)

            # Step #13 - Wait for the modems that we rebooted in Step #12 to come back online.
            beam_drift_utils.print_step(
                13, "waiting for modems to come back online after we rebooted them"
            )
            (
                online_after_reboot,
                offline_after_reboot,
            ) = beam_drift_utils.wait_till_modems_are_online(
                pushed_lkg_files, beam_drift_utils.get_wait_secs_for_online_after_lkg_push()
            )

        # Step #14 - Restore the modems' beam pinnings in ACS, undoing what we did in Step #2.
        beam_drift_utils.print_step(14, "re-pinning modems to their goal beams in ACS")
        if beam_drift_utils.should_preserve_beam_pinnings():
            modems_to_re_pin = drifted_modems
        elif beam_drift_utils.is_fast_run():
            modems_to_re_pin = on_goal_beam_after_cwmp_restart
        else:
            modems_to_re_pin = pushed_lkg_files
        _, failed_to_re_pin = beam_drift_utils.re_pin_beams(modems_to_re_pin)

        if beam_drift_utils.is_fast_run():
            # If the "fast run" box was checked, skip Step #8 - Step #13 & Step #15
            common_utils.print_heading("skipping Step #15")

        else:
            # Step #15 - Use utstat -L to check whether the modems that we rebooted in
            #            Step #12 came back online on the correct beam. If they didn't, check
            #            whether the beam that they did come online on has a polarization
            #            opposite to that of the beam to which they failed to move. If it
            #            does, this could indicate a broken polarity switch on an AB modem.
            beam_drift_utils.print_step(
                15, "checking whether modems came back online on the correct beam"
            )
            (
                on_goal_beam,
                on_wrong_beam_opp_pol,
                on_wrong_beam_same_pol,
                failed_to_check_beam,
            ) = beam_drift_utils.check_beams_match_on_modem(
                jumpbox, beam_drift_db, online_after_reboot, flag_pol_swap_issue_on_failure=True
            )
            beam_drift_db.record_fix_counts(
                fixed_by_cwmp_restart=len(on_goal_beam_after_cwmp_restart),
                fixed_by_lkg_update=len(on_goal_beam),
                verbose=common_utils.is_job_verbose(),
            )

        # Step #16 - Check the final beam pinnings in ACS and ensure that the modems
        #            we expected to be pinned to their goal beams actually are.
        beam_drift_utils.print_step(16, "checking whether beam re-pinnings went through in CM-T")
        (
            already_matched_pin_success,
            already_matched_pin_fail,
            already_matched_pin_error,
        ) = beam_drift_utils.checks_beams_pinned_to_goals(already_matched_newly_pinned)
        (
            _,
            not_pinned_to_goal,
            unable_to_check_final_pinning,
        ) = beam_drift_utils.checks_beams_pinned_to_goals(online_after_reboot)

    # When we're finished, disconnect from the MoDOT jumpbox and
    # the beam drift database and print a summary of the results.
    finally:
        if jumpbox:
            jumpbox.disconnect()
        if beam_drift_db:
            beam_drift_db.database.disconnect()
        print_results(
            already_matched_already_pinned=already_matched_already_pinned,
            already_matched_failed_to_pin=already_matched_failed_to_pin,
            no_initial_goal=no_initial_goal,
            goal_on_different_satellite=goal_on_different_satellite,
            failed_to_check_start_state=failed_to_check_start_state,
            failed_to_clear=failed_to_clear,
            offline_after_clear=offline_after_clear,
            failed_to_restart_cwmp=failed_to_restart_cwmp,
            offline_after_cwmp_restart=offline_after_cwmp_restart,
            on_goal_beam_after_cwmp_restart=on_goal_beam_after_cwmp_restart,
            failed_to_check_beam_after_cwmp_restart=failed_to_check_beam_after_cwmp_restart,
            failed_to_back_up_lkg=failed_to_back_up_lkg,
            goal_beam_in_lkg_same_pol=goal_beam_in_lkg_same_pol,
            goal_beam_in_lkg_opp_pol=goal_beam_in_lkg_opp_pol,
            no_lkg_found=no_lkg_found,
            error_pushing_lkg=error_pushing_lkg,
            failed_to_re_pin=failed_to_re_pin,
            offline_after_reboot=offline_after_reboot,
            on_wrong_beam_opp_pol=on_wrong_beam_opp_pol,
            on_wrong_beam_same_pol=on_wrong_beam_same_pol,
            failed_to_check_beam=failed_to_check_beam,
            on_goal_beam=on_goal_beam,
            already_matched_pin_success=already_matched_pin_success,
            already_matched_pin_fail=already_matched_pin_fail,
            already_matched_pin_error=already_matched_pin_error,
            not_pinned_to_goal=not_pinned_to_goal,
            unable_to_check_final_pinning=unable_to_check_final_pinning,
        )


def print_results(  # pylint: disable=too-many-locals
    already_matched_already_pinned,  # pylint: disable=unused-argument
    already_matched_failed_to_pin,  # pylint: disable=unused-argument
    no_initial_goal,  # pylint: disable=unused-argument,
    goal_on_different_satellite,  # pylint: disable=unused-argument,
    failed_to_check_start_state,  # pylint: disable=unused-argument
    failed_to_clear,  # pylint: disable=unused-argument
    offline_after_clear,  # pylint: disable=unused-argument
    failed_to_restart_cwmp,  # pylint: disable=unused-argument
    offline_after_cwmp_restart,  # pylint: disable=unused-argument
    on_goal_beam_after_cwmp_restart,  # pylint: disable=unused-argument
    failed_to_check_beam_after_cwmp_restart,  # pylint: disable=unused-argument
    goal_beam_in_lkg_same_pol,  # pylint: disable=unused-argument
    goal_beam_in_lkg_opp_pol,  # pylint: disable=unused-argument
    failed_to_back_up_lkg,  # pylint: disable=unused-argument
    no_lkg_found,  # pylint: disable=unused-argument
    error_pushing_lkg,  # pylint: disable=unused-argument
    failed_to_re_pin,  # pylint: disable=unused-argument
    offline_after_reboot,  # pylint: disable=unused-argument
    on_wrong_beam_opp_pol,  # pylint: disable=unused-argument
    on_wrong_beam_same_pol,  # pylint: disable=unused-argument
    failed_to_check_beam,  # pylint: disable=unused-argument
    on_goal_beam,  # pylint: disable=unused-argument
    already_matched_pin_success,  # pylint: disable=unused-argument
    already_matched_pin_fail,  # pylint: disable=unused-argument
    already_matched_pin_error,  # pylint: disable=unused-argument
    not_pinned_to_goal,  # pylint: disable=unused-argument
    unable_to_check_final_pinning,  # pylint: disable=unused-argument
):
    """
    Print the results from running this job.

    :param already_matched_already_pinned: a list of dictionaries representing the modems that were
                                           already on their goal beam and pinned to their goal beam
                                           in ACS prior to running this job.

    :param already_matched_failed_to_pin: a list of dictionaries representing the modems that were
                                          already on their goal beam prior to running this job, but
                                          whose pinning we failed update in ACS

    :param no_initial_goal: a list of dictionaries representing the modems that didn't have a
                            beam pinning in ACS prior to running this job without a goal beam
                            override specified and were therefore excluded from the beam drift
                            correction process

    :param goal_on_different_satellite: a list of dictionaries representing the modems that are
                                        trying to move to a satellite other than the one on which
                                        they're currently online and were therefore excluded from
                                        the beam drift correction process

    :param failed_to_check_start_state: a list of dictionaries representing the modems whose
                                        records we were unable to look up in the ACS and were
                                        therefore excluded from the beam drift correction process

    :param failed_to_clear: a list of dictionaries representing the modems whose beam pinnings
                            couldn't be cleared in ACS

    :param offline_after_clear: a list of dictionaries representing the modems that didn't come
                                back online after their beam pinnings were cleared

    :param failed_to_restart_cwmp: a list of dictionaries representing modems on which we
                                   failed to restart CWMP

    :param offline_after_cwmp_restart: a list of dictionaries representing that didn't come
                                       back online after we restarted CWMP

    :param on_goal_beam_after_cwmp_restart: a list of dictionaries representing modems that came
                                            online on their goal beams after we restarted CWMP

    :param failed_to_check_beam_after_cwmp_restart: a list of dictionaries representing modems whose
                                                    current beam we failed to check after we
                                                    restarted CWMP

    :param goal_beam_in_lkg_same_pol: a list of dictionaries representing modems that already had
                                      their goal beam in their LKG but still cannot move to a beam
                                      with the same polarization after restarting CWMP

    :param goal_beam_in_lkg_opp_pol: a list of dictionaries representing modems that already had
                                     their goal beam in their LKG but still cannot move to a beam
                                     with the opposite polarization after restarting CWMP

    :param failed_to_back_up_lkg: a list of dictionaries representing the modems whose LKG files
                                  we weren't able to back up

    :param no_lkg_found: a list of dictionaries representing the modems from whose goal beam we
                         weren't able to pull down an example good LKG file

    :param error_pushing_lkg: a list of dictionaries representing the modems to which we were
                              unable to push a new LKG file

    :param failed_to_re_pin: a list of dictionaries representing the modems to which we were
                             unable to re-pin goal beams in ACS

    :param offline_after_reboot: a list of dictionaries representing the modems that never came
                                 back online after we rebooted them

    :param on_wrong_beam_opp_pol: a list of dictionaries representing the modems that, even after
                                  we pushed a good LKG file to them, still came back on the wrong
                                  beam of an opposite polarization to that of the beam to which
                                  they were trying to move

    :param on_wrong_beam_same_pol: a list of dictionaries representing the modems that, even after
                                   we pushed a good LKG file to them, still came back on the wrong
                                   beam of the same polarization as that of the beam to which they
                                   were trying to move

    :param failed_to_check_beam: a list of dictionaries representing the modems whose final beams
                                 we were unable to determine via utstat -L

    :param on_goal_beam: a list of dictionaries representing the modems that were successfully
                         moved to their goal beam without issues

    :param already_matched_pin_error: a list of dictionaries representing the modems that were
                                      already on their goal beams prior to running the jobs and
                                      whose beam pinnings we thought we updated successfully but
                                      weren't able to be confirmed in ACS at the end of the job

    :param already_matched_pin_fail: a list of dictionaries representing the modems that were
                                     already on their goal beams prior to running the jobs and
                                     whose beam pinnings we thought we updated successfully but
                                     didn't actually end up updated in ACS

    :param already_matched_pin_success: a list of dictionaries representing the modems that were
                                        already on their goal beams prior to running the jobs but
                                        whose pinning we successfully updated in ACS

    :param not_pinned_to_goal: a list of dictionaries representing the modems that were not pinned
                               to their goal beam in ACS yet when the job ended

    :param unable_to_check_final_pinning: a list of dictionaries representing the modems whose
                                          final beam pinnings we were unable to confirm
    """
    common_utils.print_heading("SUMMARY OF RESULTS")
    outcomes = locals()
    scenarios = {
        "no_initial_goal": "These modems' goal beam could not be determined in Step #1",
        "goal_on_different_satellite": "These modems are trying to move to a beam on a different"
        " satellite from the one they're currently on, which is outside the scope of this job",
        "failed_to_check_start_state": "We were unable to check whether these modems"
        " had a mismatched goal beam and actual beam in CM-T in Step #1",
        "failed_to_clear": "These modems' beam pinning couldn't be cleared in CM-T in Step #2",
        "already_matched_already_pinned": "These modems were already on their goal beam and already"
        " pinned to their goal beam in ACS in Step #3",
        "already_matched_failed_to_pin": "These modems were already on their goal beam, but they"
        " weren't pinned to their goal beam in ACS and we failed to fix that in Step #3",
        "already_matched_pin_success": "These modems were already on their goal beams prior to"
        " running the job, but we successfully updated their beam pinnings in ACS in Step #3",
        "offline_after_clear": "These modems didn't come online after"
        f" {beam_drift_utils.get_wait_secs_for_online_after_clear()} seconds in Step #4 after"
        " their beam pinning was cleared in Step #2",
        "failed_to_restart_cwmp": "We weren't able to restart CWMP on these modems in Step #5",
        "offline_after_cwmp_restart": "These modems never came online after"
        f" {beam_drift_utils.get_wait_secs_for_online_after_cwmp_restart()}"
        f" seconds in Step #6 after we restarted CWMP on them in Step #5",
        "failed_to_check_beam_after_cwmp_restart": "We failed to check in Step #7 whether these"
        " modems were on their goal beams after we restarted CWMP in Step #5",
        "on_goal_beam_after_cwmp_restart": "These modems were successfully moved to their goal"
        " beams after a CWMP restart in Step #5",
        "goal_beam_in_lkg_same_pol": "In Step #8 we determined that these modems already had their"
        " goal beam in their LKG but still failed to move to a beam"
        " with the same polarization after restarting CWMP in Step #5",
        "goal_beam_in_lkg_opp_pol": "In Step #8 we determined that these modems already had their"
        " goal beam in their LKG but still failed to move to a beam"
        " with the opposite polarization after restarting CWMP in Step #5"
        " (possible broken polarity switcher)",
        "no_lkg_found": "We were unable to pull down an example good"
        " LKG file for these modems in Step #9",
        "failed_to_back_up_lkg": "We were unable to back up the"
        " existing LKG file on these modems in Step #10",
        "error_pushing_lkg": "We failed to push a new LKG file to these modems in Step #11",
        "failed_to_re_pin": "We were unable to re-pin these modems to their goal beams in Step #14",
        "offline_after_reboot": "These modems didn't come back online after"
        f" {beam_drift_utils.get_wait_secs_for_online_after_lkg_push()} seconds in Step"
        f" #13 after we pushed the good LKG file in Step #11 and rebooted them in Step #12",
        "on_wrong_beam_opp_pol": "In Step #15, these modems came back online on the wrong"
        " beam of a polarization opposite to that of their goal beam"
        " even after we updated their LKG files in Step #11"
        " (possible broken polarity switcher)",
        "on_wrong_beam_same_pol": "In Step #15, these modems came back online on the wrong"
        " beam of the same polarization as that of their goal beam even after we updated their LKG"
        " files in Step #11",
        "failed_to_check_beam": "We were unable to check what beam"
        " these modems ended up on in Step #15 after we updated their LKG files in Step #11",
        "already_matched_pin_fail": "These modems were already on their goal beams prior to running"
        " the job, and we got a 200 OK when we tried to update their beam"
        " pinnings in Step #3, but in Step #16 we found that their"
        " pinning didn't actually get updated in ACS",
        "already_matched_pin_error": "These modems were already on their goal beams prior to"
        " running the job, and we got a 200 OK when we tried to update their beam"
        " pinnings in Step #3, but we were unable to confirm in Step #16"
        " whether or not the pinnings actually got updated in ACS",
        "on_goal_beam": "These modems were successfully moved to their goal beams after we"
        " updated their LKG files in Step #11",
        "not_pinned_to_goal": "We got a 200 OK when we tried to re-pin these modems to their"
        " goal beams in ACS in Step #14, but we determined in Step #16 that"
        " this re-pinning hadn't gone through (yet)",
        "unable_to_check_final_pinning": "We got a 200 OK when we tried to re-pin these modems to"
        " their goal beams in ACS in Step #14, but we were unable to confirm"
        " in Step #16 whether or not this re-pinning had through"
        " at the end of the job",
    }
    for scenario, message in scenarios.items():
        if scenario in outcomes and outcomes[scenario]:
            print(" \n----------------------------")
            print(f"{message}:")
            outcome = outcomes[scenario]
            beam_drift_utils.print_modems_verbose(outcome)
            print("----------------------------")


if __name__ == "__main__":
    # Fix modems that are on the wrong beam.
    print(" \n================begin======================")
    try:
        correct_drifted_modems()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
