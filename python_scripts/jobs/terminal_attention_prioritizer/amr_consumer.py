"""
Contains functionality for retrieving the Antenna Mispoint
Report (AMR) and parsing relevant information from it.

The public methods in this file are meant to be called by prioritize_attention_for_terminals.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from tap_const import MISPOINT_PROP_STR, MISPOINT_PRIORITY_PROP_STR, PRIORITY_PROP_STR

from libs import sdp_api


def determine_mispoint_priority_metrics(config):
    """
    Determine mispoint priority metrics based on data in the Antenna Mispoint Report.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics

    :return: a dictionary of dictionaries of dictionaries where the first layer of keys are VNOs,
             the second layer of keys are MAC addresses, and the value at each MAC address contains
             its mispoint priority information, like:
             {
                "exederes": {
                    "AABBCCDDEEFF": {
                        "mispoint": {
                            "mispoint_priority": 2,
                        },
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                },
                "xci": {...},
                ...
            }
    """
    amr = _download_latest_antenna_mispoint_report(config)

    results_dict = {}
    for vno in config.get_vnos_for_mispoint_analysis():
        results_dict[vno] = _determine_mispoint_priorities_from_amr(vno, amr)
    return results_dict


def _download_latest_antenna_mispoint_report(config):
    """
    Download the latest antenna mispoint report.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics
    :return: the a dict of  antenna mispoint report keyed by vno
    """
    output_dict = {}
    for vno in config.get_vnos_for_mispoint_analysis():
        output_dict[vno] = sdp_api.get_PPILv2_report_latest_gen_date(vno)

    return output_dict


def _determine_mispoint_priorities_from_amr(vno, amr):
    """
    Parse relevant information from the antenna mispoint report for the modems in a given VNO.
    :param vno: a string representing a VNO
    :param amr: the antenna mispoint report. For example:
      {
      "vno1:
        {
        time :          {0: '2021-08-10 23:22:30', 1: '2021-08-10 23:15:00', 2: '2021-08-06 20:00:00'}
        ntdMacAddress : {0: '11a0bcb1b0b0', 1: '11a0bc2f3fe8', 2: '11a0bc419f1e'}
        realm :         {0: 'bra.telbr.viasat.com', 1: 'bra.telbr.viasat.com', 2: 'bra.telbr.viasat.com'}
        satId :         {0: 16, 1: 16, 2: 16}
        serviceAreaId : {0: 'None', 1: 'None', 2: 'None'}
        logicalBeamId : {0: 53, 1: 61, 2: 61}
        bandId :        {0: 'A', 1: 'A', 2: 'A'}
        numberOfAggregates : {0: 49, 1: 102, 2: 67}
        utAvgFlSinrMeasured :{0: -1.3, 1: 0.2, 2: 1.3}
        utAvgFlSinrPredicted : {0: 3.5, 1: 3.5, 2: 3.5}
        utRlChipRateMeasured : {0: 0.625, 1: 0.625, 2: 0.625}
        utRlChipRatePredicted : {0: 2.5, 1: 2.5, 2: 2.5}
        flGigaSymbolsUsed : {0: 182.325, 1: 155.331, 2: 237.618}
        flGigaSymbolsPredicted : {0: 68.372, 1: 93.199, 2: 178.213}
        flGigaSymbolsWasted : {0: 113.953, 1: 62.132, 2: 59.404}
        flPacketLossRate : {0: 0.000247, 1: 0.0002583, 2: 0.01074}
        priority : {0: 3, 1: 3, 2: 3}
        mispointFlag : {0: True, 1: True, 2: True}
        miscFlag : {0: False, 1: False, 2: False}
        packetLossFlag : {0: False, 1: False, 2: True}
        performanceFlag : {0: True, 1: True, 2: True}
        lastPeakPointSuccessTime : {0: 'None', 1: 'None', 2: 'None'}
        },
      "vno2:
        {
        ...
        }
      }

    :return: a dictionary of dictionaries where the first layer of keys are MAC addresses and
             the value at each MAC address contains its mispoint priority information, like:
                 {
                    "AABBCCDDEEFF": {
                        "mispoint": {
                            "mispoint_priority": 2,
                        },
                    },
                    "FFEEDDCCBBAA": {...},
                    ...
                }
    """
    if amr is None:
        return None

    results_dict = {}
    rows = len(amr[vno]["ntdMacAddress"])

    for index in range(rows):
        mac_address = amr[vno]["ntdMacAddress"][index]
        results_dict[mac_address] = {}
        results_dict[mac_address][MISPOINT_PROP_STR] = {}
        results_dict[mac_address][MISPOINT_PROP_STR][MISPOINT_PRIORITY_PROP_STR] = amr[vno][
            PRIORITY_PROP_STR
        ][index]

    return results_dict
