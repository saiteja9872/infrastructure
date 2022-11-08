"""
Contains functionality for calculating the financial impact of a modem experiencing issues.

NPV stands for net present value. For more information, see
https://wiki.viasat.com/display/LEAP/Net+Present+Value+Report+Summary

The public methods in this file are meant to be called by prioritize_attention_for_terminals.py
"""


def add_npv_calculations(config, results):
    """
    Use the info previously gathered about each modem along with the NPV parameters specified
    by the config to update the results we've collected so far with NPV information.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics
    :param results: (both and input and output parameter), a dictionary of dictionaries of
                    dictionaries where the first layer of keys are VNOs, the second layer of keys
                    are MAC addresses, and the value at each MAC address contains all the
                    information that we've gathered about it so far. The side of effect of this
                    function is to add NPV calculations to this dictionary, like so:
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
                                "amr" : {
                                    "mispoint_priority": "unknown"
                                },
                                "npv": {...}  <------ THIS SECTION WILL BE ADDED BY THIS METHOD!!!!
                            },
                            "FFEEDDCCBBAA": {...},
                            ...
                        },
                        "xci": {...},
                        ...
                    }
    """
    print(" \nTODO BBCTERMSW-28558: add NPV calculations")
    for vno in config.get_vnos_for_npv_analysis():  # only some VNOs may ask for NPV analysis
        pass


# TODO IBBCTERMSW-28558 'm sure we'll be adding many helper functions to this file,
#  at least one for each NPV metric we need to calculate
