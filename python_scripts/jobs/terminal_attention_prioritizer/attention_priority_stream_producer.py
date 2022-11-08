"""
Contains functionality for publishing messages to the output databus stream.

The public methods in this file are meant to be called by prioritize_attention_for_terminals.py

NOTES: This file assumes that we're going to have *one* output databus stream where each message
       is tagged with its VNO. We'll need to refactor this file slightly if we instead decide to
       go with a separate output stream for every VNO in order to manage permissions differently.
"""

from datetime import datetime

# from pytz import timezone
from tap_const import (
    VNO_OPTIONS,
    STREAM_NAME,
    VNO_PROP_STR,
    EQUIPMENT_PROP_STR,
    MISPOINT_PROP_STR,
    CABLE_PROP_STR,
    NPV_PROP_STR,
    DATABUS_SCHEMA_VERSION_PROP_STR,
    TIMESTAMP_PROP_STR,
    EQUIPMENT_PRIORITY_PROP_STR,
    RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR,
    MISPOINT_PRIORITY_PROP_STR,
    CABLE_PRIORITY_PROP_STR,
    RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR,
    MAC_PROP_STR,
    DATABUS_TAP_SCHEMA_VERSION_0_0,
)
from libs import common_utils
from libs import vault_utils
from libs.stream_producer import StreamProducer


# Here's an example of an output message that meets the output message schema below.
EXAMPLE_MESSAGE = {
    "mac": "00A0B0DDEEFF",
    "vno": "exederes",
    "schema_version": "tap_0.0",
    "timestamp": 1618955100,
    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 107},
    "mispoint": {"mispoint_priority": 2},
    "cable": {"cable_priority": 3, "recent_ptria_err_event_count": 52},
    "npv": True,  # TODO BBCTERMSW-28558 this is a placeholder, will change when we implement NPV
}

# Below is the JSON schema for the messages that this job will write to the output data stream.
# When making any updates to the output schema, be sure to run the tests in tests/unit_tests.py
# to ensure that the example message above meets the schema and the schema behaves as expected.
OUTPUT_MESSAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        VNO_PROP_STR: {"description": "the name of the VNO", "type": "string", "enum": VNO_OPTIONS},
        MAC_PROP_STR: {"description": "the modem's MAC address", "type": "string"},
        DATABUS_SCHEMA_VERSION_PROP_STR: {
            "description": "the version of the output message schema",
            "type": "string",
        },
        TIMESTAMP_PROP_STR: {
            "description": "the epoch time at which the job that produced this message ran",
            "type": "integer",
        },
        EQUIPMENT_PROP_STR: {
            "description": "info about the priority"
            " for attending to the equipment of this modem",
            "type": "object",
            "properties": {
                EQUIPMENT_PRIORITY_PROP_STR: {
                    "description": "equipment attention priority (high"
                    " numbers mean more urgent need for attention)",
                    "type": "integer",
                },
                RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR: {
                    "description": "the number of recent PHY-related offline events",
                    "type": "integer",
                },
            },
            "required": [EQUIPMENT_PRIORITY_PROP_STR, RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR],
            "additionalProperties": False,
        },
        MISPOINT_PROP_STR: {
            "description": "info about the priority for correcting this modem's pointing'",
            "type": "object",
            "properties": {
                MISPOINT_PRIORITY_PROP_STR: {
                    "description": "mispoint attention priority (high"
                    " numbers mean more urgent need for attention)",
                    "type": "integer",
                },
            },
            "required": [MISPOINT_PRIORITY_PROP_STR],
            "additionalProperties": False,
        },
        CABLE_PROP_STR: {
            "description": "info about the priority for attending to this modem's cable'",
            "type": "object",
            "properties": {
                CABLE_PRIORITY_PROP_STR: {
                    "description": "equipment attention priority (high"
                    " numbers mean more urgent need for attention)",
                    "type": "integer",
                },
                RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR: {
                    "description": "the number of recent PTRIA_ERR events",
                    "type": "integer",
                },
            },
            "required": [CABLE_PRIORITY_PROP_STR, RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR],
            "additionalProperties": False,
        },
        NPV_PROP_STR: {
            "description": "info about the financial impact of not attending to this modem",
            "type": "boolean",  # TODO BBCTERMSW-28558 this will change once we've implemented NPV
        },
    },
    "required": [MAC_PROP_STR, VNO_PROP_STR, DATABUS_SCHEMA_VERSION_PROP_STR, TIMESTAMP_PROP_STR],
    "additionalProperties": False,
}


def publish_prioritization_metrics(config, prioritization_metrics):
    """
    Publish prioritization metrics to the database.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics
    :param prioritization_metrics: a dictionary of dictionaries of dictionaries where the first
                                   layer of keys are VNOs, the second layer of keys are MAC
                                   addresses, and the value at each MAC address contains all
                                   the information that we've determined about its attention
                                   priorities. Looks like:
                                    {
                                        "exederes": {
                                            "AABBCCDDEEFF": {
                                                "equipment": {
                                                    "equipment_priority": 3,
                                                    "recent_phy_offline_event_count": 107
                                                },
                                                "cable": {...},
                                                "mispoint": {...},
                                                "npv": {...}
                                            },
                                            "FFEEDDCCBBAA": {...},
                                            ...
                                        },
                                        "xci": {...},
                                        ...
                                    }
    """
    messages = _format_prioritization_metrics_as_databus_messages(config, prioritization_metrics)
    _publish_messages_to_databus(messages)


def _format_prioritization_metrics_as_databus_messages(config, prioritization_metrics):
    """
    Format the final results into the format we want them to take on the output databus stream.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics
    :param prioritization_metrics: a dictionary of dictionaries of dictionaries where the first
                                   layer of keys are VNOs, the second layer of keys are MAC
                                   addresses, and the value at each MAC address contains all
                                   the information that we've determined about its attention
                                   priorities. Looks like:
                                    {
                                        "exederes": {
                                            "AABBCCDDEEFF": {
                                                "equipment": {
                                                    "equipment_priority": 3,
                                                    "recent_phy_offline_event_count": 107
                                                },
                                                "cable": {...},
                                                "mispoint": {...},
                                                "npv": {...}
                                            },
                                            "FFEEDDCCBBAA": {...},
                                            ...
                                        },
                                        "xci": {...},
                                        ...
                                    }

    :return: a list of dictionaries representing messages to write to the output databus stream
             that fit the output message schema (see OUTPUT_MESSAGE_SCHEMA dictionary above)
    """
    now = int(datetime.now().timestamp())
    messages = []
    for vno, ut_metrics_dict in prioritization_metrics.items():
        for ut_mac, metrics in ut_metrics_dict.items():
            ut_item = {}
            messages.append(ut_item)
            ut_item[VNO_PROP_STR] = vno
            ut_item[MAC_PROP_STR] = ut_mac
            ut_item[DATABUS_SCHEMA_VERSION_PROP_STR] = DATABUS_TAP_SCHEMA_VERSION_0_0
            ut_item[TIMESTAMP_PROP_STR] = now
            equipment_dict = metrics[EQUIPMENT_PROP_STR] if EQUIPMENT_PROP_STR in metrics else None
            if equipment_dict is not None:
                ut_item[EQUIPMENT_PROP_STR] = {}
                ut_item[EQUIPMENT_PROP_STR][EQUIPMENT_PRIORITY_PROP_STR] = equipment_dict[
                    EQUIPMENT_PRIORITY_PROP_STR
                ]
                ut_item[EQUIPMENT_PROP_STR][
                    RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR
                ] = equipment_dict[RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR]
            cable_dict = metrics[CABLE_PROP_STR] if CABLE_PROP_STR in metrics else None
            if cable_dict is not None:
                ut_item[CABLE_PROP_STR] = {}
                ut_item[CABLE_PROP_STR][CABLE_PRIORITY_PROP_STR] = cable_dict[
                    CABLE_PRIORITY_PROP_STR
                ]
                ut_item[CABLE_PROP_STR][RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR] = cable_dict[
                    RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR
                ]
            mispoint_dict = metrics[MISPOINT_PROP_STR] if MISPOINT_PROP_STR in metrics else None
            if mispoint_dict is not None:
                ut_item[MISPOINT_PROP_STR] = {}
                ut_item[MISPOINT_PROP_STR][MISPOINT_PRIORITY_PROP_STR] = mispoint_dict[
                    MISPOINT_PRIORITY_PROP_STR
                ]
            npv = metrics[NPV_PROP_STR] if NPV_PROP_STR in metrics else None
            if npv is not None:
                ut_item[NPV_PROP_STR] = npv
            else:
                raise ValueError("npv value is None")
    return messages


def _publish_messages_to_databus(messages):
    """
    Publish the messages to the databus.

    :param messages: a list of dictionaries that representing messages to be written to the databus
    """
    env = common_utils.get_environment()
    env = "preprod" if env == "dev" else env
    pwd = vault_utils.get_ut_devops_cicd_password(env=env)
    stream_producer = StreamProducer(f"ut-devops-{env}_cicd", pwd, STREAM_NAME)
    stream_producer.publish_messages(messages)
    stream_producer.disconnect()
