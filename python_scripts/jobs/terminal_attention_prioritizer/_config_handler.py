"""
Contains functionality for determining which VNOs should include which fields in the output
databus messages and for determining VNO-specific parameters needed for calculating the values
that belong in those fields. Also used to keep track of other configurable settings for the
job that aren't VNO-specific.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import json
from tap_const import (
    VNO_OPTIONS,
    VNO_PROP_STR,
    CONFIG_SCHEMA_VERSION_PROP_STR,
    CONFIG_VNO_SCHEMA_VERSION_PROP_STR,
    EQUIPMENT_PROP_STR,
    MISPOINT_PROP_STR,
    CABLE_PROP_STR,
    NPV_PROP_STR,
    GLOBAL_SETTINGS_PROP_STR,
    VNO_SPECIFIC_SETTINGS_PROP_STR,
    PHY_OFFLINE_EVENT_THRESH_PROP_STR,
    DAYS_PROP_STR,
    THRESH_TO_EQUIPMENT_PRIORITY_PROP_STR,
    PTRIA_ERR_EVENT_THRESH_PROP_STR,
    THRESH_TO_CABLE_PRIORITY_PROP_STR,
    THRESHOLD_LIST_DEFN_STR,
    PRIORITY_PROP_STR,
    THRESHOLD_PROP_STR,
)
from libs import common_utils

# This is the JSON schema for the configuration file for this job. See config.json for the config
# itself. The config in that file will be validated against this schema at the beginning of the
# job. When making any updates to the config and/or the config schema, be sure to run the tests
# in tests/unit_tests.py to ensure that the config meets the schema and that the schema behaves
# as expected.
CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        GLOBAL_SETTINGS_PROP_STR: {
            "description": "settings that apply to the whole run of the job",
            "type": "object",
            "properties": {
                CONFIG_SCHEMA_VERSION_PROP_STR: {
                    "description": "the schema version for the whole config",
                    "type": "string",
                }
            },
            "required": [CONFIG_SCHEMA_VERSION_PROP_STR],
            "additionalProperties": False,
        },
        VNO_SPECIFIC_SETTINGS_PROP_STR: {
            "description": "settings that specify VNO-specific parameters",
            "type": "array",
            "items": {"$ref": f"#/definitions/{VNO_SPECIFIC_SETTINGS_PROP_STR}"},
        },
    },
    "required": [GLOBAL_SETTINGS_PROP_STR, VNO_SPECIFIC_SETTINGS_PROP_STR],
    "additionalProperties": False,
    "definitions": {
        VNO_SPECIFIC_SETTINGS_PROP_STR: {
            "description": "defines what categories belong in the output messages for a particular"
            "VNO and what thresholds should be used to calculate values in those categories",
            "type": "object",
            "properties": {
                VNO_PROP_STR: {
                    "description": "the name of the VNO",
                    "type": "string",
                    "enum": VNO_OPTIONS,
                },
                CONFIG_VNO_SCHEMA_VERSION_PROP_STR: {
                    "description": "the schema version specific to this VNO",
                    "type": "string",
                },
                EQUIPMENT_PROP_STR: {
                    "description": "the parameters required to calculate"
                    " equipment priority for a modem in the given VNO",
                    "type": "object",
                    "properties": {
                        PHY_OFFLINE_EVENT_THRESH_PROP_STR: {
                            "description": "specifies how many phy-related offline"
                            " events in a given period warrant each equipment priority rating",
                            "type": "object",
                            "properties": {
                                DAYS_PROP_STR: {
                                    "description": "the period of days over which to look",
                                    "type": "integer",
                                },
                                THRESH_TO_EQUIPMENT_PRIORITY_PROP_STR: {
                                    "description": "a mapping of phy offline event"
                                    " counts to equipment priority ratings",
                                    "$ref": f"#/definitions/{THRESHOLD_LIST_DEFN_STR}",
                                },
                            },
                            "required": [DAYS_PROP_STR, THRESH_TO_EQUIPMENT_PRIORITY_PROP_STR],
                            "additionalProperties": False,
                        }
                    },
                    "required": [PHY_OFFLINE_EVENT_THRESH_PROP_STR],
                    "additionalProperties": False,
                },
                MISPOINT_PROP_STR: {
                    "description": "the parameters required to calculate the mispoint"
                    " priority in for a modem in the given VNO",
                    "type": "boolean",
                },
                CABLE_PROP_STR: {
                    "description": "the parameters required to calculate cable"
                    " priority for a modem in the given VNO",
                    "type": "object",
                    "properties": {
                        PTRIA_ERR_EVENT_THRESH_PROP_STR: {
                            "description": "specifies how many ptria error"
                            " events in a given period warrant each cable priority rating",
                            "type": "object",
                            "properties": {
                                DAYS_PROP_STR: {
                                    "description": "the period of days over which to look",
                                    "type": "integer",
                                },
                                THRESH_TO_CABLE_PRIORITY_PROP_STR: {
                                    "description": "a mapping of ptria error event"
                                    " counts to cable priority ratings",
                                    "$ref": f"#/definitions/{THRESHOLD_LIST_DEFN_STR}",
                                },
                            },
                            "required": [DAYS_PROP_STR, THRESH_TO_CABLE_PRIORITY_PROP_STR],
                            "additionalProperties": False,
                        }
                    },
                    "required": [PTRIA_ERR_EVENT_THRESH_PROP_STR],
                    "additionalProperties": False,
                },
                NPV_PROP_STR: {
                    "description": "the parameters required to"
                    " calculate the NPV for a modem in the specified VNO",
                    "type": "boolean",
                },
            },
            "required": [VNO_PROP_STR, CONFIG_VNO_SCHEMA_VERSION_PROP_STR],
            "additionalProperties": False,
        },
        THRESHOLD_LIST_DEFN_STR: {
            "description": "a mapping of thresholds to priority ratings",
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    PRIORITY_PROP_STR: {
                        "type": "integer",
                        "description": "a priority (higher numbers are higher priority)",
                    },
                    THRESHOLD_PROP_STR: {
                        "type": "integer",
                        "description": "the minimum threshold to earn that priority",
                    },
                },
                "required": [PRIORITY_PROP_STR, THRESHOLD_PROP_STR],
                "additionalProperties": False,
            },
        },
    },
}


class Config:
    """
    The config class. Used to determine which VNOs should include which fields in the output
    databus messages and to pass any VNO-specific parameters needed for calculating the values
    that belong in those fields. Also used to keep track of other configurable settings for the
    job that aren't VNO-specific.

    This class provides helper functions for accessing fields in the config that abstracts
    the actual construction of the config and the strings used in it from the user (where the user
    is the functions in other files used for this job). Any time a method needs info from the
    config, add a function to do so here (rather than sharing the property and definition name
    strings outside of this file). This class is the only thing that should be imported outside
    of this file.
    """

    def __init__(self, config_file_path=None, env=None):
        """
        Load the config when the class is initialized.
        """
        config_file_path = config_file_path or _get_config_file_path(env)
        self._config = {}
        self._load_config(config_file_path)

    def _load_config(self, config_file_path):
        """
        Read in the job's configuration file and validate it against the config schema.

        :param config_file_path: the absolute path to the job's configuration file
        """
        print(" \nloading config")
        try:
            with open(config_file_path, "r") as file:
                config = json.load(file)
                print(" \nvalidating config against schema")
                if common_utils.does_json_instance_fit_schema(
                    instance=config, schema=CONFIG_SCHEMA
                ):
                    self._config = config
                else:
                    print(" \nconfig did not fit config schema")
                    sys.exit(0)
        except FileNotFoundError:
            print(" \nunable to locate config file")
            raise

    def get_vno_list(self):
        """
        Get the list of VNOs for the job to run on.

        :return: a list of strings representing the VNOs that the job is configured to include
        """
        return [vno[VNO_PROP_STR] for vno in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]]

    def get_vnos_for_cable_analysis(self):
        """
        Get the list of VNOs that want their cable priority analyzed per the config.

        :return: a list of strings representing VNOs
        """
        return self._get_vnos_for_category(CABLE_PROP_STR)

    def get_vnos_for_equipment_analysis(self):
        """
        Get the list of VNOs that want their equipment priority analyzed per the config.

        :return: a list of strings representing VNOs
        """
        return self._get_vnos_for_category(EQUIPMENT_PROP_STR)

    def get_vnos_for_mispoint_analysis(self):
        """
        Get the list of VNOs that want their mispoint priority analyzed per the config.

        :return: a list of strings representing VNOs
        """
        return self._get_vnos_for_category(MISPOINT_PROP_STR)

    def get_vnos_for_npv_analysis(self):
        """
        Get the list of VNOs that want their NPV priority analyzed per the config.

        :return: a list of strings representing VNOs
        """
        return self._get_vnos_for_category(CABLE_PROP_STR)

    def _get_vnos_for_category(self, category):
        """
        Get the list of VNOs that have requested a particular analysis category per the config.

        :param category: a string representing a modem health analysis category
                         (e.g. "equipment", "cable", "amr", "npv")
        :return: a list of strings representing VNOs
        """
        return [
            vno[VNO_PROP_STR]
            for vno in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]
            if category in vno
        ]

    def get_interval_days_for_cable_analysis(self, vno):
        """
        Get the period of days over which to check
        for PTRIA_ERR events for the given VNO.

        :param vno: a string representing a VNO
        :return: a number representing a period of days
        """
        for vno_settings in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]:
            if vno_settings[VNO_PROP_STR] == vno:
                return vno_settings[CABLE_PROP_STR][PTRIA_ERR_EVENT_THRESH_PROP_STR][DAYS_PROP_STR]
        raise RuntimeError(f"VNO {vno} not found in config")

    def get_interval_days_for_equipment_analysis(self, vno):
        """
        Get the period of days over which to check for
        PHY-related offline events for the given VNO.

        :param vno: a string representing a VNO
        :return: a number representing a period of days
        """
        for vno_settings in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]:
            if vno_settings[VNO_PROP_STR] == vno:
                return vno_settings[EQUIPMENT_PROP_STR][PHY_OFFLINE_EVENT_THRESH_PROP_STR][
                    DAYS_PROP_STR
                ]
        raise RuntimeError(f"VNO {vno} not found in config")

    def get_thresh_to_cable_priority(self, vno):
        """
        Determine what thresholds for the count of recent PTRIA_ERR events are
        needed for each cable priority rating for the given VNO per the config.

        :param vno: a string representing a VNO
        :return: a list of dictionaries that maps priority ratings
                 to PTRIA_ERR event thresholds, of the form:
                    [
                      {"priority": 1, "threshold": 10},
                      {"priority": 2, "threshold": 20},
                      {"priority": 3, "threshold": 30}
                    ]
        """
        for vno_settings in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]:
            if vno_settings[VNO_PROP_STR] == vno:
                return vno_settings[CABLE_PROP_STR][PTRIA_ERR_EVENT_THRESH_PROP_STR][
                    THRESH_TO_CABLE_PRIORITY_PROP_STR
                ]
        raise RuntimeError(f"VNO {vno} not found in config")

    def get_thresh_to_equipment_priority(self, vno):
        """
        Determine what thresholds for the count of recent PHY-related offline events
        are needed for each equipment priority rating for the given VNO per the config.

        :param vno: a string representing a VNO
        :return: a list of dictionaries that maps priority ratings to recent
                 PHY offline event thresholds, of the form:
                    [
                      {"priority": 1, "threshold": 10},
                      {"priority": 2, "threshold": 20},
                      {"priority": 3, "threshold": 30}
                    ]
        """
        for vno_settings in self._config[VNO_SPECIFIC_SETTINGS_PROP_STR]:
            if vno_settings[VNO_PROP_STR] == vno:
                return vno_settings[EQUIPMENT_PROP_STR][PHY_OFFLINE_EVENT_THRESH_PROP_STR][
                    THRESH_TO_EQUIPMENT_PRIORITY_PROP_STR
                ]
        raise RuntimeError(f"VNO {vno} not found in config")


def _get_config_file_path(env=None):
    """
    Get the file path for the config for this job.

    :param env: a string "dev", "preprod", or "prod"
    :return: a string representing the file path of the job configuration
    """
    return (
        f"{os.path.abspath('python_scripts/jobs/terminal_attention_prioritizer')}"
        f"/{_get_config_file_name(env)}"
    )


def _get_config_file_name(env=None):
    """
    Get the file name for the config for this job.

    :param env: a string "dev", "preprod", or "prod"
    :return: a string representing the file name of the job configuration
    """
    return f"config_{env or common_utils.get_environment()}.json"
