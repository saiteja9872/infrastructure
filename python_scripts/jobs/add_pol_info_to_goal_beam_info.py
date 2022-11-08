"""
Contains functionality for transitioning to a new goals table that contains goal polarization info.

NOTE: This script only needed to be run once, which happened on 25 Aug 2021,
      but I'm leaving it in the git repo for historical reference.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
import urllib3
from libs import common_utils
from libs.beam_drift_db import BeamDriftDb
from libs.acs_db import AcsDb

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def add_pol_info_to_goal_beam_info():
    """
    Populate the new goals table with info about the polarizations of modems' goal beams.
    """
    succeeded = []
    goal_unknown = []

    # Get the list of modems whose beams are pinned to 0 in ACS.
    acs_db = AcsDb()
    modems_pinned_to_zero = acs_db.get_modems_with_cleared_goal_beams(
        limit=common_utils.get_expected_env_var("limit")
    )
    acs_db.database.disconnect()

    # Connect to the beam drift database.
    beam_drift_db = BeamDriftDb()

    # For each modem whose goal beam is pinned to zero, parse its goal beam polarization from
    # ACS and look up its real goal beam in the old goals table in our local database. Then,
    # combine this information and update the new goals table.
    for modem in modems_pinned_to_zero:
        mac = modem["cid"]
        goal_pol = modem["PrimaryBeamPolarizationPending"] or modem["PrimaryBeamPolarization"]
        saved_goal_info = beam_drift_db.look_up_goal_without_pol(mac, verbose=False)

        # Combine this information in the new goal beams table.
        if saved_goal_info:
            goal_beam = saved_goal_info["goal_beam"]
            goal_sat = saved_goal_info["goal_sat"]
            beam_drift_db.update_goal(mac, goal_sat, goal_beam, goal_pol)
            succeeded.append(mac)

        # There's nothing we can do if we don't have a modem's goal on record. This should be rare.
        else:
            print(f" \nno known goal for {mac}")
            goal_unknown.append(mac)

    # Disconnect from the beam drift database.
    beam_drift_db.database.disconnect()

    # Print the results.
    if succeeded:
        succeeded_str = "\n".join(succeeded)
        print(
            f" \nsuccessfully migrated the records for these {len(succeeded)} modems:\n"
            + succeeded_str
        )
    if goal_unknown:
        goal_unknown_str = "\n".join(goal_unknown)
        print(
            f" \nwe don't have any goal beams on record for these {len(goal_unknown)} modems:\n"
            + goal_unknown_str
        )


if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        add_pol_info_to_goal_beam_info()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
