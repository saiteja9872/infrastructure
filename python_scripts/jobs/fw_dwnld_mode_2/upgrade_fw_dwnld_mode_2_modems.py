"""
This script is used by a Jenkins job to ssh onto the MoDOT jumpbox and
use mtool to reboot modems that are running old SW versions and have
the latest version of SW staged on them (aka firmware download mode 2).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from libs import mtool_utils
from libs.jumpbox import Jumpbox
from libs.common_utils import timestamp, hw_type_of_sw_version, get_expected_env_var


CMD_FILE_NAME = "reboot_fw_dwnld_mode_2_cmds.txt"
CMD_LOCAL_FILE_PATH = f"jumpbox_communication/{CMD_FILE_NAME}"
CMD_REMOTE_FILE_PATH = f"/tmp/{CMD_FILE_NAME}"


def upgrade_fw_dwnld_mode_2():
    """
    Uses mtool on the MoDOT jumpbox to reboot modems that
    have the desired version of SW already staged on them.
    """

    # Log into the MoDOT prod jumpbox.
    jumpbox = Jumpbox()

    # Clear results from the last time we ran this script.
    jumpbox.clear_any_previous_results(prefix="reboot_results_")

    # Construct the bash commands that we'll want mtool to run and write them to a file.
    add_commands_to_cmd_file()

    # Upload the file containing the bash commands we want to run on each modem to the jumpbox.
    jumpbox.upload_file(CMD_LOCAL_FILE_PATH, CMD_FILE_NAME)

    # Run an mtool command from the jumpbox that will log onto modems on the specified VNO
    # running the specified straggler SW versions and run the list of bash commands we uploaded.
    output_file_name = f"reboot_results_{timestamp()}"
    mtool_utils.run_mtool_command(
        jumpbox,
        f"-a run_commands -c {CMD_REMOTE_FILE_PATH}"
        f" -L {get_expected_env_var('modem_limit')} -v {get_expected_env_var('vnos')}"
        f" -V {get_expected_env_var('old_versions')} -o {output_file_name}",
    )

    # Download the output file that mtool creates with
    # the outcome of all the bash commands we gave it.
    jumpbox.download_file(f"{output_file_name}{mtool_utils.mtool_file_suffix()}")
    jumpbox.disconnect()


def add_commands_to_cmd_file():
    """
    Construct the bash commands that we'll want mtool to run and write them to a file.
    """

    # Create the command that will reboot the modem if the expected SW version if staged.
    desired_version = get_expected_env_var("desired_version")
    hw_type = hw_type_of_sw_version(desired_version)
    reboot_cmd = (
        'SW=`fw_printenv current_sw_image | grep [0-9] -o`; [ "$SW" == 0 ] && SW=1 || SW=2 ;'
        f" [ `head /mnt/boot$SW/{hw_type}.bin"
        " | hexdump -C | head -n 1 | awk '{print $15}'`"
        f" == {hex_of_sw_version_last_digit(desired_version)} ] &&"
        f" [ `version | sed -n '2 p' | awk '{{print $3}}'` != \"{desired_version}\" ]"
        ' && reboot || echo "NO reboot"'
    )

    # Append these commands to the file containing the bash
    # commands that we want mtool to run on the modems.
    with open(CMD_LOCAL_FILE_PATH, "a") as cmd_file:
        cmd_file.writelines(
            [
                f"hexdump -C /mnt/boot1/{hw_type}.bin | head -n 1\n",
                f"hexdump -C /mnt/boot2/{hw_type}.bin | head -n 1\n",
                reboot_cmd,
            ]
        )


def hex_of_sw_version_last_digit(desired_version):
    """
    Get the hex representation of the last number in a SW version.

    :param desired_version: a string representing a UT SW version (e.g. "DATA_3.7.9.13.15")
    :return: a string representing the hex representation of the last number in the input SW
             version (e.g. "0f" for the "15" in "DATA_3.7.9.13.15")
    """
    if "." in desired_version:
        last_digit = desired_version.split(".")[-1]
        if last_digit.isnumeric():
            return format(int(last_digit), "x")
    raise RuntimeError(f'Invalid desired_version "{desired_version}"')


if __name__ == "__main__":
    # Reboot modems that are running old SW versions and have the latest version staged.
    print("\n================begin======================")
    try:
        upgrade_fw_dwnld_mode_2()
    except Exception as ex:
        print(f"\n{ex}")
        raise
    finally:
        print("\n=================end=======================\n")
