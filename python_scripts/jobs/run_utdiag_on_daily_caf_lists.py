"""
This script is used by a Jenkins job to ssh onto the MoDOT jumpbox
and use mtool to run utdiag on the list of modems not statpushing.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libs.jumpbox import Jumpbox, print_command_results
from libs.mtool_utils import (
    mtool_base_cmd,
    UTDIAG_FILE_PATH,
)
from libs.common_utils import timestamp


def run_utdiag_on_modems_not_statpushing():
    """
    Uses mtool on the MoDOT jumpbox to run utdiag on the list of modems not statpushing.
    """
    jumpbox = Jumpbox()
    jumpbox.clear_any_previous_results(prefix="results_")
    jumpbox.clear_any_previous_results(prefix="ut_macs_")
    for network in list_of_networks_to_check():
        command = (
            f"{mtool_base_cmd()} -a utdiag_vwa_modem_list -d true -N {network} -T 30 "
            f"-o results_{network}_{timestamp()} -s {UTDIAG_FILE_PATH} -p false -i"
        )
        output, errors = jumpbox.run_command(
            command, prompt_answers=[jumpbox.password, 2, jumpbox.password, jumpbox.password]
        )
        summary_file_name = find_utdiag_summary_file_name(output)
        if summary_file_name == "error":
            print(f"\nERROR: failed to run utdiag on {network} list:")
            print_command_results(command, output, errors)
        else:
            print(f"\nSUCCESS: ran utdiag on {network} list")
            jumpbox.download_file(summary_file_name)
    jumpbox.disconnect()


def list_of_networks_to_check():
    """
    Get the list of networks from which to pull lists of modems not statpushing.

    The list is determined by boolean parameters to the
    Jenkins job that are stored as environment variables.

    :return: a list of strings to be passed as values to
             the -N arguments in a series of mtool commands
    """
    networks = []
    for network in ["caf-exede", "caf-sdp", "vwa-exede", "vwa-sdp"]:
        if os.environ[network] == "true":
            networks.append(network)
    if not networks:
        print("\nERROR: please choose at least one network")
        sys.exit(0)  # decided not to send a failure notification for this manual error
    return networks


def find_utdiag_summary_file_name(output):
    """
    Get the name of the file that the utdiag summary was stored in.

    :param output: a list of strings representing the output from the mtool command that ran utdiag
    :return: a string representing the file name of the utdiag summary file, or the string
             "error" if the utdiag summary file name cannot be found in the command output
    """
    for line in output:
        if "UT Diag Analysis Summary written to" in line:
            return line.split()[-1:][0]  # the file name is the last word in the line
    return "error"


if __name__ == "__main__":
    # Run utdiag on the list of modems not statpushing.
    print("\n================begin======================")
    try:
        run_utdiag_on_modems_not_statpushing()
    except Exception as ex:
        print(f"\n{ex}")
        raise
    finally:
        print("\n=================end=======================\n")
