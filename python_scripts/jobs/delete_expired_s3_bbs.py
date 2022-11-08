"""
Deletes expired blackboxes from the bbserver
S3 and records which ones were deleted.
"""

import os
from datetime import datetime
import boto3

# the maximum number of days old a blackbox can be before we want to delete it
MAX_DAYS_OLD = 50


def delete_expired_bbs_from_s3():
    """
    Main method — deletes expired blackboxes from
    the S3 and records which ones were deleted.
    """
    blackboxes = list_blackboxes_in_s3()
    num_deleted = 0
    for bb in blackboxes:
        bb_name = bb.key
        days_old = parse_bb_age_from_name(bb_name)
        if days_old > MAX_DAYS_OLD:
            bb.delete()
            num_deleted += 1
            print("deleted", bb_name)
    print_success_message(num_deleted)


def list_blackboxes_in_s3():
    """
    Accesses the S3 bucket corresponding to the
    "environment" parameter of the job (prod or preprod)
    and retrieves a list of the blackbox objects inside it.

    :return: a list of the blackbox objects in the S3
    """
    environment = os.environ["ENVIRONMENT"]
    print("\n\nChecking {} S3 for expired blackboxes.\n".format(environment))
    access_id = os.environ["AWS_ACCESS_KEY_ID_" + environment.upper()]
    access_key = os.environ["AWS_SECRET_ACCESS_KEY_" + environment.upper()]
    s3 = boto3.resource("s3", aws_access_key_id=access_id, aws_secret_access_key=access_key)
    bucket_name = (
        "ut-devops-prod-bbserver-s3" if environment == "prod" else "ut-devops-preprod-s3-bbserver"
    )
    bucket = s3.Bucket(bucket_name)  # pylint: disable=no-member
    blackbox_list = bucket.objects.all()
    return blackbox_list


def parse_bb_age_from_name(name):
    """
    Parses the age of the blackbox from its name.

    :param name: the name of the blackbox (looks like "ut_C_YYYY-MM-DD[...].tar.gz")
    :return: the number of days since the blackbox was first created
    """
    try:
        year = int(name[5:9])
        month = int(name[10:12])
        day = int(name[13:15])
        creation_date = datetime(year, month, day)
        days_old = (datetime.today() - creation_date).days

    # If the date cannot be parsed from the blackbox, treat it as expired.
    except ValueError:
        print('date could not be parsed from "{}"'.format(name))
        days_old = MAX_DAYS_OLD + 1

    return days_old


def print_success_message(num_deleted):
    """
    Prints the outcome of the job.

    :param num_deleted: the number of the blackboxes that
                        were just deleted from the S3
    """
    if num_deleted:
        print(
            "\nDeleted {} blackbox(es) older than {} days from the S3.\n".format(
                num_deleted, MAX_DAYS_OLD
            )
        )
    else:
        print("\nThere were no blackboxes older than {} days in the S3.\n".format(MAX_DAYS_OLD))


delete_expired_bbs_from_s3()
