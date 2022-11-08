"""
This script is used by a Jenkins job to ssh onto the MoDOT jumpbox
and use mtool to run a command for any/all CAO modems in the beta trial
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libs.jumpbox import Jumpbox
from libs.mtool_utils import run_mtool_command
from libs.common_utils import get_expected_env_var
from packaging import version


def fix_libraries_on_cao_modems():
    """
    Uses mtool to find and fix modems participating in the CAO beta trial
    """
    cao_version = get_expected_env_var("version_number")

    # Validate version number
    validate_ver_number(cao_version)

    jumpbox = Jumpbox()

    # Clear any residual files from running this job
    jumpbox.clear_any_previous_results(prefix="ut_macs_cao")
    jumpbox.clear_any_previous_results(prefix="ut_out_cao")

    # Acquire the modems running the CAO software build
    run_mtool_command(jumpbox, f"-a get_ut_info -o ut_out_cao -v exederes -L 500 -V SPOCK_{cao_version}")

    # Format the output to be only a list of mac addresses
    jumpbox.run_command("grep -io '[0-9a-f:]\{15\}[0-9a-f]\{2\}' ut_out_cao_*.txt > ut_macs_cao_temp.txt")

    # Delete the now unused file
    jumpbox.clear_any_previous_results(prefix="ut_out_cao")

    # Print the modem macs that will be affected by this job
    cao_mac_list = jumpbox.run_command("cat ut_macs_cao_temp.txt")
    print(cao_mac_list[0])

    # Touch the park_clear file so the libraries will be fixed upon next reboot
    run_mtool_command(jumpbox, "-a run_commands -m ut_macs_cao_temp.txt -C 'touch /mnt/jffs2/config/park_clear'")

    # Cleanup
    jumpbox.clear_any_previous_results(prefix="ut_macs_cao")
    jumpbox.clear_any_previous_results(prefix="ut_out_cao")

    # No need to capture output at this time.
    jumpbox.disconnect()


def validate_ver_number(ver):
    """
    A function to validate a version number was received by user input
    :param ver: The version number supplied by user input in Jenkins
    :return: a properly formatted software version number
    """
    try:
        if version.Version(ver):
            pass
    except Exception:
        print(f"\n\nYou supplied {ver} which is not a valid version number\n"
              f"Please try again or use the default value provided by Jenkins\n")
        sys.exit()


if __name__ == "__main__":
    print("\n================begin======================")
    try:
        fix_libraries_on_cao_modems()
    except Exception as ex:
        print(f"\n{ex}")
        raise
    finally:
        print("\n=================end=======================\n")
