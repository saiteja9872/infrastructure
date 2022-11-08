"""
Contains functionality for retrieving relevant outage history data.

The public methods in this file are meant to be called by prioritize_attention_for_terminals.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from datetime import timedelta, datetime
from tap_const import (
    EQUIPMENT_PROP_STR,
    CABLE_PRIORITY_PROP_STR,
    RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR,
    RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR,
    PRIORITY_PROP_STR,
    THRESHOLD_PROP_STR,
    CABLE_PROP_STR,
    PTRIA_OFFLINE_EVENT_CODES,
    PHY_OFFLINE_EVENT_CODES,
    EQUIPMENT_PRIORITY_PROP_STR,
)
from libs import metrignome_api


def determine_equip_priority_metrics(config):
    """
    Determine equipment priority information based on data from the outage history
    time series for all desired VNOs using the parameters specified in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics

    :return: a dictionary of dictionaries of dictionaries where the first layer of keys are VNOs,
             the second layer of keys are MAC addresses, and the value at each MAC address contains
             its equipment priority information, like:
             {
                "exederes": {
                    "AABBCCDDEEFF": {
                        "equipment": {
                            "equipment_priority": 3,
                            "recent_phy_offline_event_count": 107
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
    for vno in config.get_vnos_for_equipment_analysis():
        results[vno] = _determine_equip_priority_metrics_from_query(config, vno)
    return results


def determine_cable_priority_metrics(config):
    """
    Determine cable priority information based on data from the outage history
    time series for all desired VNOs using the parameters specified in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job

    :return: a dictionary of dictionaries of dictionaries where the first layer of keys are VNOs,
             the second layer of keys are MAC addresses, and the value at each MAC address contains
             its cable priority information, like:
             {
                "exederes": {
                    "AABBCCDDEEFF": {
                        "cable": {
                            "cable_priority": 3,
                            "recent_ptria_err_event_count": 52
                        }
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                },
                "xci": {...},
                ...
            }
    """
    results = {}
    for vno in config.get_vnos_for_cable_analysis():
        results[vno] = _determine_cable_priority_metrics_from_query(config, vno)
    return results


def _query_outage_hist_for_offline_events(config, vno, event_dict):
    """
    Query the outage history time series for recent PTRIA_ERR events in a given VNO.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO
    :param event_dict: a list of events

    :return:  A dictionary with the "msid" as key, and the counts for the  outage event in the
              event_dict as value.  Example:
              {'11a0bc61442c': 1, '11a0bc2f3fe8': 6, '11a0bc3a2215': 9}
    """
    out_dict = {}
    days = config.get_interval_days_for_equipment_analysis(vno)
    from_ts = (datetime.today() - timedelta(days=days)).timestamp()
    to_ts = datetime.today().timestamp()
    reason_dict = metrignome_api.get_terminalOfflineEventReason(
        from_ts=from_ts, to_ts=to_ts, vno=vno, env=None
    )
    for msid, item_list in reason_dict.items():
        num_envents = 0
        for _, item in enumerate(item_list):
            if item["v"] in event_dict.keys():
                num_envents += 1
        if num_envents > 0:
            out_dict[msid] = num_envents

    # print(out_dict)
    return out_dict


def _query_outage_hist_for_phy_related_offline_events(config, vno):
    """
    Query the outage history outage history time series
    for recent PHY-related offline events in a given VNO.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO

    :return:  A dictionary with the "msid" as key, and outage event counts as value.  Example:
              {'11a0bc61442c': 1, '11a0bc2f3fe8': 6, '11a0bc3a2215': 9}
    """
    # SELECT COUNT(DISTINCT "__time") AS "num_events", "msid", "tags.vno" as "vno"
    #     FROM "sdpapi.statpush.outage_history"
    #     WHERE "__time" >= CURRENT_TIMESTAMP - INTERVAL '%(days)s' DAY
    #         AND "vno" IN <VNO list>
    #         AND "reason_code" IN (3, 5, 21, 41, 47)
    #     GROUP BY "msid"

    return _query_outage_hist_for_offline_events(config, vno, PHY_OFFLINE_EVENT_CODES)


def _query_outage_hist_for_ptria_err_offline_events(config, vno):
    """
    Query the outage history time series for recent PTRIA_ERR events in a given VNO.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO

    :return:  A dictionary with the "msid" as key, and outage event counts as value.  Example:
              {'11a0bc61442c': 1, '11a0bc2f3fe8': 6, '11a0bc3a2215': 9}
    """

    # service account and make a query that looks something like:
    #
    # SELECT COUNT(DISTINCT "__time") AS "num_events", "msid", "tags.vno" as "vno"
    #     FROM "sdpapi.statpush.outage_history"
    #     WHERE "__time" >= CURRENT_TIMESTAMP - INTERVAL '%(days)s' DAY
    #         AND "vno" = '%(vno)s'
    #         AND "reason_code" = 41
    #     GROUP BY "msid"
    #
    return _query_outage_hist_for_offline_events(config, vno, PTRIA_OFFLINE_EVENT_CODES)


def _determine_priority_metrics_from_query(config, vno, event_count_type):
    """
    Determine equipment priority information for a given VNO based on data from
    the outage history time series and the VNO-specific parameters in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO
    :param event_count_type:  recent_phy_offline_event_count or recent_ptria_err_event_count

    :return: a dictionary of dictionaries where the first layer of keys are MAC addresses and
             the value at each MAC address contains its priority information, like:
                 {
                    "AABBCCDDEEFF": {
                        "equipment": {
                            "equipment_priority": 3,
                            f'{event_count_type}': 107
                        },
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                }
    """
    result_dict = {}
    config_priority_list = None
    event_count_dict = {}
    if event_count_type == RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR:
        config_priority_list = config.get_thresh_to_equipment_priority(vno)
        event_count_dict = _query_outage_hist_for_phy_related_offline_events(config, vno)
    elif event_count_type == RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR:
        config_priority_list = config.get_thresh_to_cable_priority(vno)
        event_count_dict = _query_outage_hist_for_ptria_err_offline_events(config, vno)
    else:
        raise ValueError(f"Invalid event_count_type:{event_count_type}")

    for mac_addr, event_count in event_count_dict.items():
        priority = 0
        result_dict[mac_addr] = {}
        for _, entry in enumerate(config_priority_list):
            priority_config = entry[PRIORITY_PROP_STR]
            config_threshold = entry[THRESHOLD_PROP_STR]
            if event_count > config_threshold:
                priority = priority_config
        if event_count_type == RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR:
            result_dict[mac_addr][EQUIPMENT_PROP_STR] = {}
            result_dict[mac_addr][EQUIPMENT_PROP_STR][EQUIPMENT_PRIORITY_PROP_STR] = priority
            result_dict[mac_addr][EQUIPMENT_PROP_STR][f"{event_count_type}"] = event_count
        elif event_count_type == RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR:
            result_dict[mac_addr][CABLE_PROP_STR] = {}
            result_dict[mac_addr][CABLE_PROP_STR][CABLE_PRIORITY_PROP_STR] = priority
            result_dict[mac_addr][CABLE_PROP_STR][f"{event_count_type}"] = event_count
        else:
            raise ValueError(f"Invalid event_count_type:{event_count_type}")

    return result_dict


def _determine_equip_priority_metrics_from_query(config, vno):
    """
    Determine equipment priority information for a given VNO based on data from
    the outage history time series and the VNO-specific parameters in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO

    :return: a dictionary of dictionaries where the first layer of keys are MAC addresses and
             the value at each MAC address contains its equipment priority information, like:
                 {
                    "AABBCCDDEEFF": {
                        "equipment": {
                            "equipment_priority": 3,
                            "recent_phy_offline_event_count": 107
                        },
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                }
    """
    event_count_type = RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR
    results = _determine_priority_metrics_from_query(config, vno, event_count_type)
    return results


def _determine_cable_priority_metrics_from_query(config, vno):
    """
    Determine cable priority information for a given VNO based on data from
    the outage history time series and the VNO-specific parameters in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO, what thresholds each VNO should use to calculate
                   those metrics, and any general settings for the job
    :param vno: a string representing a VNO
    :param response: the raw SQL query response returned by
                     query_outage_history_for_phy_related_offline_events()
                     TODO BBCTERMSW-28550 figure out what data type / format that'll be in

    :return: a dictionary of dictionaries where the first layer of keys are MAC addresses and
             the value at each MAC address contains its cable priority information, like:
                 {
                    "AABBCCDDEEFF": {
                        "cable": {
                            "cable_priority": 3,
                            "recent_ptria_err_event_count": 52
                        }
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                }
    """
    event_count_type = RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR
    results = _determine_priority_metrics_from_query(config, vno, event_count_type)
    return results
