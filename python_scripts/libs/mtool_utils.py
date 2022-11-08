"""
Contains functionality for using Jenkins to run mtool commands via the MoDOT jumpboxes.
"""

import os
from datetime import datetime

MTOOL_FILE_PATH_ON_JB = "/var/tmp/modot_tools/modem_tool/modem_tool.py"
UTDIAG_FILE_PATH = "/usr/sbin/ut_scriptfile.sh"


def run_mtool_command(jumpbox, mtool_args, verbose=True, prompt_answers=None):
    """
    Run an mtool command on the MoDOT jumpbox.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param mtool_args: a string containing the arguments to be passed to the mtool command,
                       excluding -i because -i will be added automatically
    :param verbose: True if we want to print the results of running the mtool command,
                    False otherwise
    :param prompt_answers: a list of strings representing answers to expected
                           prompts for user input after running the command
    :return:
    """
    prompt_answers = prompt_answers or [jumpbox.password, jumpbox.password, jumpbox.password]
    return jumpbox.run_command(
        f"{mtool_base_cmd()} -i {mtool_args}", verbose=verbose, prompt_answers=prompt_answers
    )


def mtool_base_cmd():
    """
    Get the base command to run mtool.

    If the mtool-file-path environment variable is present, this will
    override the default location in order to test custom mtool changes.

    :return: a string representing the command that Jenkins will need
             to run on the jumpbox in order to run mtool
    """
    return (
        "setfacl -R -m u:sshproxy:rwx ~/ > /dev/null 2>&1 ;"
        " sudo -E PATH=$PATH -u sshproxy /var/tmp/modot_venv/bin/python"
        f" {os.environ['mtool_file_path'] or MTOOL_FILE_PATH_ON_JB}"
    )


def create_mac_list_file(jumpbox, file_name, macs):
    """
    Create a file on the MoDOT jumpbox containing a list of MAC addresses that can then
    be passed to mtool via the -m argument to perform some action on those modems.

    :param jumpbox: an instance of the class used to connect to the MoDOT jumpbox
    :param file_name: a string representing the name of the file to be created
    :param macs: a list of strings representing the MAC addresses to put in the file
    """
    mac_list = "\n".join(macs)
    jumpbox.run_command(f"rm {file_name}; touch {file_name}; echo '{mac_list}' >> {file_name}")


def mtool_file_suffix():
    """
    Get the suffix that mtool would automatically add to an output file name.

    :return: a string representing the suffix that mtool automatically appends to output files.
    """
    return f"_{datetime.now().strftime('%Y-%m-%d')}.txt"


def check_if_cmd_no_output_succeeded(output, mac):
    """
    By looking through the output of running a command via mtool that has no expected output
    at the command level, determine whether this command succeeded for a particular modem.

    :param output: a string representing the output of running
                   a command on a list of modems via mtool
    :param mac: a string representing the MAC address of one of those modems
    :return: True if the command succeeded for that modem, False otherwise
    """
    for i in range(len(output) - 2):
        if (
            format_mac_addr(mac) in output[i]
            and "swVersion:" in output[i + 1]
            and "ran successfully" in output[i + 2]
        ):
            return True
    return False


def check_if_cmd_had_expected_output(output, mac, expected_output):
    """
    By looking through the output of running a command via mtool that expects stdout output at the
    command level, determine whether this command had the expected output for a particular modem.

    :param output: a string representing the output of running
                   a command on a list of modems via mtool
    :param mac: a string representing the MAC address of one of those modems
    :param expected_output: a string representing a phrase we expect to find
                            in the stdout of the command we used mtool to run
    :return: True if the command had the expected output for that modem, False otherwise
    """
    for i in range(len(output) - 3):
        if (
            format_mac_addr(mac) in output[i]
            and "swVersion:" in output[i + 1]
            and expected_output in output[i + 3]
        ):
            return True
    return False


def format_mac_addr(mac):
    """
    Format a MAC address into uppercase colon separated format.

    :param mac: a string representing the MAC address to format
    """
    if ":" not in mac:
        mac = ":".join(mac[i : i + 2] for i in range(0, 12, 2))  # noqa: E203
    return mac.upper()
