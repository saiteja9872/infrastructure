"""
Backs up Jenkins' secrets to an S3 bucket in case we
lose our Jenkins instance and can't recover its secrets.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError


def back_up_jenkins_secrets_to_s3():
    """
    Backs up Jenkins' secrets to our S3 bucket.
    """

    # Create a tar file containing the Jenkins secrets.
    tar_file_name = "secrets.tgz"
    local_tar_file_path = f"/tmp/{tar_file_name}"
    tar_up_jenkins_secrets(local_tar_file_path)

    # Upload that tar file to a folder in the S3 bucket.
    bucket = "ut-devops-prod-general-s3"
    folder_in_bucket = "jenkins"
    upload_file_to_s3_folder(local_tar_file_path, bucket, folder_in_bucket, tar_file_name)


def tar_up_jenkins_secrets(output_file_path):
    """
    Puts the jenkins secrets into a tar file at the specified file path on the Jenkins server.

    :param output_file_path: a string representing the file path at which we'd
                             like to store the tar file containing the backup
                             of the contents of the Jenkins Credentials Manager
    """
    print_line()

    if os.system(f"cd /var/lib/jenkins; tar czvf {output_file_path} secret* credentials.xml") != 0:
        print("failed to tar up jenkins credentials")
        print_line()
        sys.exit(1)

    print(f"copied jenkins secrets into {output_file_path}")


def upload_file_to_s3_folder(local_file_path, bucket, remote_folder, remote_file_name):
    """
    Uploads a specified file to a specified folder in a specified S3 bucket.

    The folder will be created automatically if it doesn't already exist.
    If a file of the same name is already present in the folder, that file
    will be overwritten.

    :param local_file_path: a string representing the complete file path to the local
                            file that we want to upload
    :param bucket: a string representing the name of the S3 bucket to which we'd like to
                   upload the file
    :param remote_folder: a string representing the name of the S3 bucket's folder to
                          which we'd like to upload the file
    :param remote_file_name: a string representing what we want the file's name to be
                             inside the S3
    """
    s3 = define_s3_object()
    try:
        with open(local_file_path, "rb") as data:
            print(
                f"attempting to upload {local_file_path} to "
                f"{remote_folder} folder in {bucket} bucket"
            )
            s3.meta.client.upload_fileobj(data, bucket, f"{remote_folder}/{remote_file_name}")

    except FileNotFoundError:
        print(f"unable to find {local_file_path} on Jenkins server")
        print_line()
        sys.exit(1)

    except ClientError as ex:
        print(f'failed to log in to S3; error was: "{ex}"')
        print_line()
        sys.exit(1)

    print("upload succeeded")
    print_line()


def define_s3_object():
    """
    Defines the object we'll need to access S3 using credentials provided by the Jenkins job.

    :return: a boto3 resource object that we should be able to use to access the S3
    """
    access_id = os.environ["AWS_ACCESS_KEY_ID_PROD"]
    access_key = os.environ["AWS_SECRET_ACCESS_KEY_PROD"]
    return boto3.resource("s3", aws_access_key_id=access_id, aws_secret_access_key=access_key)


def print_line():
    """
    Used to isolate relevant info in the job output to enhance readability.
    """
    print("\n-------------------------------------------------------------------------------\n")


if __name__ == "__main__":
    back_up_jenkins_secrets_to_s3()
