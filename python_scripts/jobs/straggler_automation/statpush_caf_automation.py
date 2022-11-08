"""
This script is used by a Jenkins job to ssh onto the MoDOT jumpbox
and use mtool to run common fixes for modems not statpushing
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from libs.jumpbox import Jumpbox
from libs.mtool_utils import (
    run_mtool_command,
    create_mac_list_file,
)
from libs.common_utils import batches

DEFAULT_BATCH_SIZE = 35
MAC_LIST_FILE_NAME = "ut_macs_caf.txt"


def fix_statpush_on_caf_lists():
    """
    Uses mtool to find and fix modems not statpushing per CAF team
    """
    jumpbox = Jumpbox()
    jumpbox.run_command("sshca-client -v")

    # Acquire the lists for SDP and Exede from CAF via mtool
    run_mtool_command(jumpbox, "-a utdiag_vwa_modem_list -N caf-exede -d false", verbose=False,)
    run_mtool_command(jumpbox, "-a utdiag_vwa_modem_list -N caf-sdp -d false", verbose=False,)
    modems, _ = jumpbox.run_command("cat ut_macs_caf_[es]*")

    if len(modems) == 0:
        print("No macs found in the caf report. Exiting...")
        sys.exit(0)
    elif len(modems) > 500:
        print(f"Found {len(modems)} modems. Please verify the quantity and run manually.")
        sys.exit(0)
    else:
        print(f"\n====================note=====================")
        print(f"Attempting to fix {len(modems)} modem(s)")
        groups = batches(modems, DEFAULT_BATCH_SIZE)
        counter = 1
        command_to_run = 'statpush_setup restart; utusage_setup restart; sudo statpush_setup restart'
        profile_to_push = 'modot_statpush_config_<hw type>'

        for group in groups:
            print(f"Working on batch {counter} of {len(groups)}")
            create_mac_list_file(jumpbox, MAC_LIST_FILE_NAME, group)
            output, _ = run_mtool_command(
                jumpbox, f"-a run_commands -m {MAC_LIST_FILE_NAME} -C '{command_to_run}'",
                verbose=False,
            )
            output, _ = run_mtool_command(
                jumpbox, f"-a push_profile -m {MAC_LIST_FILE_NAME} -P '{profile_to_push}'",
                verbose=False,
            )
            counter += 1
        jumpbox.clear_any_previous_results(prefix="ut_macs_")
    jumpbox.disconnect()


if __name__ == "__main__":
    print("\n================begin======================")
    try:
        fix_statpush_on_caf_lists()
    except Exception as ex:
        print(f"\n{ex}")
        raise
    finally:
        print("\n=================end=======================\n")
