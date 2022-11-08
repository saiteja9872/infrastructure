"""
Contains functionality for retrieving a list of modems that we think could possibly
have a pTRIA with a broken polarization switcher because they failed to move to a
beam of an opposite polarization in a previous run of the beam drift correction job.

Note that this is only a slight possibility. Modems returned by
this job probably do NOT have a broken polarization switch.
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


def get_broken_pol_switch_candidates():
    """
    Retrieve a list of modems that we think could possibly have a pTRIA with a
    broken polarization switcher because they failed to move to a beam of an
    opposite polarization in a previous run of the beam drift correction job.
    """
    beam_drift_db = BeamDriftDb()
    beam_drift_db.get_broken_pol_switch_candidates(added_since=added_since(), verbose=True)
    beam_drift_db.database.disconnect()


def added_since():
    """
    Get a timestamp representing most recently added entry we'd like to pull.
    I.e., we'll pull the list of entries added after this time.

    :return: a string representing a GMT timestamp, or None to pull all entries
    """
    if "added_since" in os.environ:
        added_since_ts = os.environ["added_since"]
        try:
            datetime.strptime(added_since_ts, "%Y-%m-%d %H:%M")
            return added_since_ts
        except ValueError as ex:
            print(" \n" + str(ex))
    return None


if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        get_broken_pol_switch_candidates()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
