"""
Contains the Jumpbox class that enables Jenkins jobs to run commands on the MoDOT jumpboxes.
"""

import os
import sys
import paramiko
from libs.common_utils import get_expected_env_var

ACTIVATE_MODOT_VENV = "source /var/tmp/modot_venv/bin/activate"


class Jumpbox:
    """
    Purpose:
        Enables scripts that are run from a Jenkins job to run commands on the MoDOT jumpbox.

    Environment variables that should be injected by the Jenkins job that's using this class:
        Job parameters:
            "environment" - (optional) preprod or prod
        Secret variables:
            "username_preprod" - a viasat.io username for a preprod
                                 service account with jumpbox access
            "password_preprod" - a viasat.io password for a preprod
                                 service account with jumpbox access
            "username_prod" - a viasat.io username for a prod
                              service account with jumpbox access
            "password_prod" - a viasat.io password for a prod
                              service account with jumpbox access

    Example usage:
        from jumpbox import Jumpbox
        jumpbox = Jumpbox("prod")
        jumpbox.run_command("touch hello.txt")
        output, errors = jumpbox.run_command("ls -la")
        for line in output:
            print(line)
        for error in errors:
            print(error)
        jumpbox.download_file("hello.txt")
        jumpbox.disconnect()
    """

    def __init__(self, environment=None):
        """
        Initialize the Jumpbox class by getting the credentials from the
        environment and establishing an ssh connection to the MoDOT jumpbox.

        :param environment: A string ("preprod" or "prod") representing which
                            environment's jumpbox we should connect to. If omitted,
                            the string will be pulled from an environment variable.
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        environment = environment or get_expected_env_var("environment")
        self.environment = "preprod" if environment == "dev" else environment
        self.hostname = f"jumpbox.ut-devops-{self.environment}.viasat.io"
        self.username = get_expected_env_var(f"username_{self.environment}")
        self.password = get_expected_env_var(f"password_{self.environment}")
        self.connect()

    def connect(self):
        """
        Connect to the MoDOT jumpbox.
        """
        try:
            self.client.connect(
                hostname=self.hostname, username=self.username, password=self.password
            )
            print(f" \nconnected to {self.hostname}")
        except Exception as ex:
            print(f" \nERROR: can't connect to {self.hostname}:\n\t{ex}")
            self.disconnect()
            sys.exit(1)

    def disconnect(self):
        """
        End the ssh connection to the MoDOT jumpbox.
        """
        self.client.close()

    def run_command(self, command, prompt_answers=None, verbose=False):
        """
        Run a command on the MoDOT jumpbox.

        :param command: a string representing a command to run on the MoDOT jumpbox.
        :param prompt_answers: a list of strings representing answers to expected
                               prompts for user input after running the command
        :param verbose: True to print details about the command output and errors to the console,
                        False to run the command silently
        :return: Two lists of strings: the first containing the lines of the output of the command,
                 and the second containing the command's errors. Either list may be empty.
        """
        self.reconnect_if_necessary()

        # Execute the command and pass in answers to any anticipated prompts it generates.
        stdin, stdout, stderr = self.client.exec_command(f"{ACTIVATE_MODOT_VENV}; {command}")
        if prompt_answers:
            for answer in prompt_answers:
                stdin.write(f"{answer}\n")
                stdin.flush()

        # Record the outcome
        output = [line.strip() for line in stdout.readlines()]
        errors = [error.strip() for error in stderr.readlines()]
        if verbose:
            print_command_results(command, output, errors)
        return output, errors

    def download_file(self, file_name, local_file_name=None):
        """
        Download a file from the MoDOT jumpbox to the Jenkins
        server to be exported as an artifact of the running job.

        :param file_name: a string representing the name of the file on the MoDOT jumpbox
        :param local_file_name: a string representing what to rename
                                the file to on the Jenkins server
        """
        self.reconnect_if_necessary()
        try:
            ftp_client = self.client.open_sftp()
            ftp_client.get(file_name, f"{os.environ['WORKSPACE']}/{local_file_name or file_name}")
            ftp_client.close()
            print(
                f" \ndownloaded {file_name} from the jumpbox"
                f"{' as ' + local_file_name if local_file_name else ''}"
            )
        except Exception as ex:
            print(f" \nERROR: failed to download {file_name} from the jumpbox:\n\t{ex}")

    def upload_file(self, file_path, file_name):
        """
        Upload a file from the Jenkins server to the MoDOT jumpbox.

        :param file_path: the path to and name of the file on the Jenkins server
        :param file_name: the name of the file on the Jenkins server
        """
        self.reconnect_if_necessary()
        dst_file_path = f"/tmp/{file_name}"
        try:
            ftp_client = self.client.open_sftp()
            ftp_client.put(f"{os.environ['WORKSPACE']}/{file_path}", dst_file_path)
            ftp_client.close()
            print(f" \nuploaded {file_name} to the jumpbox")
            return True
        except Exception as ex:
            print(
                f" \nERROR: failed to upload {file_path} to {dst_file_path} on the jumpbox:"
                f"\n\t{ex}"
            )
            return False

    def reconnect_if_necessary(self):
        """
        Check whether we're still connected to the
        jumpbox and attempt to reconnect if we're not.
        """
        for _ in range(5):
            try:
                self.client.exec_command("ls", timeout=5)
                return
            except Exception:
                self.connect()

    def clear_any_previous_results(self, prefix="", suffix=""):
        """
        Remove files from previous runs of the job to avoid Jenkins job artifact confusion.

        :param prefix: a string representing the prefix of the files
                       on the Jumpbox that we want to remove
        :param suffix: a string representing the suffix of the files
                       on the Jumpbox that we want to remove
        """
        if prefix or suffix:
            self.run_command(f"rm -f {prefix}*{suffix}")


def print_command_results(command, output, errors):
    """
    Print the output and errors from a command.

    :param command: the command that was run
    :param output: a list of strings representing the output of a command
    :param errors: a list of string representing the errors from a command
    """
    print(" \n------------------------------")
    print(f"command:\n\t{command}")
    print("output:")
    if output:
        for line in output:
            print("\t" + line)
    else:
        print("\t<no output>")
    print("errors:")
    if errors:
        for error in errors:
            print("\t" + error)
    else:
        print("\t<no errors>")
    print("------------------------------")
