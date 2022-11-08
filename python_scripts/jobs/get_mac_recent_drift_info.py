"""
Contains functionality for retrieving timestamp and other details
for the most recent run of a modem through the beam drift job (aka DOORIS)
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
import urllib3
from libs.beam_drift_db import BeamDriftDb
from libs import common_utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_modem_drift_db_info():
    """
    Retrieve the timestamp(s) and reason codes (if applicable)
            of the most recent time DOORIS touched a specific modem
    """
    mac = os.environ["mac"]

    # Format mac address
    formatted_mac = mac.strip().replace(":", "").upper()

    # Query the beam drift database
    beam_drift_db = BeamDriftDb()
    results = list(beam_drift_db.get_single_mac_details(formatted_mac))
    beam_drift_db.database.disconnect()

    # Check for invalid mac
    if not results:
        print(f"\nERROR: {mac} is not a valid mac address.")
        sys.exit()

    # Check for no results
    if not results[0] and not results[1]:
        print(f"\nThere are no entries in the database for {mac}.")
        sys.exit()

    # Print the results from the beam drift database
    print("NOTE: Due to a database migration, the MOST RECENT run record "
          "prior to 2021-08-23 may be missing\n\n")

    print(f"The results for your inquiry of {mac} are as follows:\n")

    if results[0]:
        print(f"The last time we recorded a beam mismatch was on {results[0][0]['updated_at']} GMT.")

    if results[1]:
        print(f"The first beam move failure was on {results[1][0]['added']} GMT.")


def get_results_of_last_run():
    """
    TODO - use timestamp to look up results of last run
    Phase 3 of https://jira.viasat.com/browse/TERMSW-30029
    """


if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        get_modem_drift_db_info()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
