"""
Diagnose modem issues that are hindering customer performance by looking at recent historical
data from a variety of sources to help VNOs prioritize different types of truck rolls.

The output of this script is the databus stream terminal_attention_priority
TODO BBCTERMSW-28556 insert link to stream here

This script is run automatically on a set schedule by the Jenkins job
terminal-attention-prioritizer, located at
https://jenkins.ut-devops-prod.viasat.io/job/terminal-attention-prioritizer/.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import traceback
import amr_consumer as amr
import outage_hist_consumer as outage_history
import provisioned_modems_consumer as provisioned_modems_list
import npv_calculator as npv
import attention_priority_stream_producer as stream_producer
from _config_handler import Config
from libs import common_utils


def main():
    """
    Aggregate health data for modems, determine priority
    for care, and publish results to the databus.
    """

    # Load and parse the configuration.
    config = Config()

    # Get the list of provisioned modems in the network.
    provisioned_modems = provisioned_modems_list.get_provisioned_modems(config)

    # Get the latest data from the Antenna Mispoint Report.
    amr_info = amr.determine_mispoint_priority_metrics(config)

    # Get the latest modem offline event data.
    equip_info = outage_history.determine_equip_priority_metrics(config)
    cable_info = outage_history.determine_cable_priority_metrics(config)

    # Combine the results from these inputs.
    results = combine_results(
        config=config,
        provisioned_modems=provisioned_modems,
        amr_info=amr_info,
        equip_info=equip_info,
        cable_info=cable_info,
    )

    # Calculate NPV metrics and add them to the combined data.
    npv.add_npv_calculations(config, results)

    # Publish the final results to the databus.
    stream_producer.publish_prioritization_metrics(config, results)


def combine_results(config, provisioned_modems, amr_info, equip_info, cable_info):
    """
    Take the information about each modem in the network that we've gained from
    external sources and combine them so that the information about each modem
    is grouped together.

    NOTE: NPV data isn't included in this function because we want all the data we've gathered
          from external sources to be grouped together first so that we can make internal
          calculations (like NPV metrics) based on the combined data from those external sources.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param provisioned_modems: a dict keyed with VNO valued with a list of strings
                   representing the MAC addresses of all the provisioned modems in the network
    :param amr_info: a dictionary of dictionaries of dictionaries where the first layer of keys are
                    VNOs, the second layer of keys are MAC addresses, and the value at each MAC
                    address contains its AMR information
    :param equip_info: a dictionary of dictionaries of dictionaries where the first layer of keys
                       are VNOs, the second layer of keys are MAC addresses, and the value at each
                       MAC address contains its AMR information
    :param cable_info: a dictionary of dictionaries of dictionaries where the first layer of keys
                       are VNOs, the second layer of keys are MAC addresses, and the value at each
                       MAC address contains its AMR information

    :return: a dictionary of dictionaries of dictionaries where the first layer of keys are VNOs,
             the second layer of keys are MAC addresses, and the value at each MAC address contains
             all the information that we've gathered about it so far, like
             {
                "exederes": {
                    "AABBCCDDEEFF": {
                        "equipment": {
                            "equipment_priority": 3,
                            "recent_phy_offline_event_count": 107
                        },
                        "cable": {
                            "cable_priority": 3,
                            "recent_ptria_err_event_count": 52
                        },
                        "mispoint" : {
                            "mispoint_priority": "unknown"
                        },
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                },
                "xci": {...},
                ...
            }
    """

    results = {}
    for vno in config.get_vno_list():
        results[vno] = {}

    info_keys = ["equipment", "cable", "mispoint"]
    infos = [amr_info, equip_info, cable_info]
    # now populate results with provisioned_modems and empty metrics
    for vno, modems in provisioned_modems.items():
        for mac in modems:
            if vno in results:  # only populated vno in config
                results[vno][mac] = {}
                for key in info_keys:
                    results[vno][mac][key] = {}

    # fill or add items with info metrics to results
    for info in infos:
        for vno in info:
            if vno in results:  # only interested in vno specified in config
                for mac in info[vno]:
                    for info_key, info_val in info[vno][mac].items():
                        if mac not in results[vno]:
                            results[vno][mac] = {}
                        results[vno][mac][info_key] = info_val

    return results


if __name__ == "__main__":
    print(" \n================begin======================")
    try:
        print(f" \nrunning in {common_utils.get_environment()} environment")
        main()
    except Exception:
        common_utils.print_heading("SOMETHING WENT WRONG")
        print()
        traceback.print_exc()
        raise
    finally:
        print(" \n=================end=======================\n")
