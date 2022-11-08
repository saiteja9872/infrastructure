"""
Restarts CWMP on modems that have drifted onto the wrong beam.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
import urllib3
from libs import common_utils
from libs.jumpbox import Jumpbox
from libs import beam_drift_utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# pylint: disable=too-many-locals,too-many-statements,too-many-branches
def restart_cwmp_on_drifted_modems():
    """
    Attempt to move drifted modems to their correct beams.
    """

    # Ensure all variables will be initialized in the finally block.
    jumpbox = None

    try:
        # Step #1 - Get the list of modems on which to run
        # the job and confirm that they're on the wrong beam.
        common_utils.print_heading("checking whether input modems are on the wrong beam")
        modems = beam_drift_utils.get_list_of_drifted_modems()
        macs = [modem[0] for modem in modems]

        # Step #2 - Restart CWMP on drifted modems.
        common_utils.print_heading("restarting CWMP")
        jumpbox = Jumpbox()
        beam_drift_utils.restart_cwmp_on_macs(jumpbox, macs)

    # When we're finished, disconnect from the MoDOT jumpbox and
    # the beam drift database and print a summary of the results.
    finally:
        if jumpbox:
            jumpbox.disconnect()


if __name__ == "__main__":
    # Restart CWMP on modems that are on the wrong beam.
    print(" \n================begin======================")
    try:
        restart_cwmp_on_drifted_modems()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
