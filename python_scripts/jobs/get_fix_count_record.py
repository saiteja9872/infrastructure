"""
Contains functionality for retrieving a record of how many modems have been successfully
moved to their goal beams by previous runs of the beam drift correction job.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
from datetime import datetime
import urllib3
from libs.beam_drift_db import BeamDriftDb
from libs import common_utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_fix_count_record():
    """
    Retrieve the fix count record for previous runs of the beam drift correction job.
    """
    beam_drift_db = BeamDriftDb()
    beam_drift_db.get_fix_count_record(fixed_since=fixed_since(), verbose=True)
    beam_drift_db.database.disconnect()


def fixed_since():
    """
    Get a timestamp representing most recently added entry we'd like to pull.
    I.e., we'll pull the list of entries added after this time.

    :return: a string representing a GMT timestamp, or None to pull all entries
    """
    if "fixed_since" in os.environ:
        fixed_since_ts = os.environ["fixed_since"]
        try:
            datetime.strptime(fixed_since_ts, "%Y-%m-%d %H:%M")
            return fixed_since_ts
        except ValueError as ex:
            print(" \n" + str(ex))
    return None


if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        get_fix_count_record()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
