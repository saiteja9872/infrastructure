"""
Contains unit tests for many of the methods used in this job.
"""
# pylint: disable=protected-access

import sys
import os

import unittest
import json
from avro_validator.schema import Schema as Avro_schema

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import amr_consumer
import outage_hist_consumer
from tap_const import (
    MAC_PROP_STR,
    DATABUS_SCHEMA_VERSION_PROP_STR,
    TIMESTAMP_PROP_STR,
    MISPOINT_PRIORITY_PROP_STR,
    EQUIPMENT_PRIORITY_PROP_STR,
    RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR,
    CONFIG_SCHEMA_VERSION_PROP_STR,
    CONFIG_VNO_SCHEMA_VERSION_PROP_STR,
    EQUIPMENT_PROP_STR,
    MISPOINT_PROP_STR,
    CABLE_PROP_STR,
    CABLE_PRIORITY_PROP_STR,
    GLOBAL_SETTINGS_PROP_STR,
    VNO_SPECIFIC_SETTINGS_PROP_STR,
    PRIORITY_PROP_STR,
    THRESHOLD_PROP_STR,
    VNO_PROP_STR,
    NPV_PROP_STR,
    RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR,
)
from prioritize_attention_for_terminals import combine_results
from libs import common_utils
from jobs.terminal_attention_prioritizer._config_handler import Config
import jobs.terminal_attention_prioritizer._config_handler as config_handler
from jobs.terminal_attention_prioritizer import attention_priority_stream_producer as producer


ENV = "prod"
# VNO = "telbr"
VNO = "exederes"


class TestConfigSchema(unittest.TestCase):
    """
    Test that the schema for the config file works as expected
    and that the current config file adheres to the schema.
    """

    def test_actual_configs(self):
        """
        Make sure that the actual configs on which the job will run fit the schema.
        """
        for env in ["prod", "preprod", "dev"]:
            with open(get_test_config_file_path(env), "r") as file:
                config = json.load(file)
                self.assertTrue(
                    common_utils.does_json_instance_fit_schema(
                        config, config_handler.CONFIG_SCHEMA, verbose=True
                    )
                )

    def test_invalid_json(self):
        """
        The schema validation function should reject invalid JSON.
        """
        self.assertFalse(
            common_utils.does_json_instance_fit_schema("no", config_handler.CONFIG_SCHEMA)
        )

    def test_empty_config(self):
        """
        The schema should reject valid JSON that doesn't contain any of the required fields.
        """
        self.assertFalse(
            common_utils.does_json_instance_fit_schema({}, config_handler.CONFIG_SCHEMA)
        )

    def test_minimal_config(self):
        """
        This config has the minimum required fields for the schema to accept it.
        """
        minimal_config = {
            GLOBAL_SETTINGS_PROP_STR: {CONFIG_SCHEMA_VERSION_PROP_STR: "0.0"},
            VNO_SPECIFIC_SETTINGS_PROP_STR: [],
        }
        self.assertTrue(
            common_utils.does_json_instance_fit_schema(
                minimal_config, config_handler.CONFIG_SCHEMA, verbose=True
            )
        )

    def test_that_categories_within_vnos_are_optional(self):
        """
        The schema permits the inclusion of VNOs with no categories of output requested.
        (I.e., these VNOs in this example aren't asking for equipment, cable, amr, or npv
        info to be included in their output) Each category is optional.
        """
        minimal_config = {
            GLOBAL_SETTINGS_PROP_STR: {CONFIG_SCHEMA_VERSION_PROP_STR: "0.0"},
            VNO_SPECIFIC_SETTINGS_PROP_STR: [
                {"vno": "exederes", CONFIG_VNO_SCHEMA_VERSION_PROP_STR: "exederes_0.0"},
                {"vno": "xci", CONFIG_VNO_SCHEMA_VERSION_PROP_STR: "xci_0.0"},
            ],
        }
        self.assertTrue(
            common_utils.does_json_instance_fit_schema(
                minimal_config, config_handler.CONFIG_SCHEMA, verbose=True
            )
        )

    def test_empty_fields_within_vnos(self):
        """
        The schema should reject the config if any of the categories are missing required
        parameters (e.g., the cable category is supposed to specify priority thresholds).
        """
        config = {
            GLOBAL_SETTINGS_PROP_STR: {"schema-version": "0.0"},
            VNO_SPECIFIC_SETTINGS_PROP_STR: [
                {
                    "vno": "exederes",
                    CONFIG_VNO_SCHEMA_VERSION_PROP_STR: "exederes_0.0",
                    CABLE_PROP_STR: {},
                },
                {"vno": "xci", CONFIG_VNO_SCHEMA_VERSION_PROP_STR: "xci_0.0"},
            ],
        }
        self.assertFalse(
            common_utils.does_json_instance_fit_schema(config, config_handler.CONFIG_SCHEMA)
        )

    def test_vnos_missing_schema_version(self):
        """
        The schema should reject the config if any of the VNOs are missing their schema version.
        """
        config = {
            GLOBAL_SETTINGS_PROP_STR: {"schema-version": "0.0"},
            VNO_SPECIFIC_SETTINGS_PROP_STR: [
                {"vno": "exederes", CONFIG_VNO_SCHEMA_VERSION_PROP_STR: "exederes_0.0"},
                {"vno": "xci"},
            ],
        }
        self.assertFalse(
            common_utils.does_json_instance_fit_schema(config, config_handler.CONFIG_SCHEMA)
        )


class TestConfig(unittest.TestCase):
    """
    Test that the functions in the Config class work as expected.
    """

    @classmethod
    def setUpClass(cls):
        """
        Create an instance of the Config class to run the tests on.
        """
        cls.config = Config(config_file_path=get_test_config_file_path("prod"))
        cls.test_vno = "exederes"

    def test_config_file_not_found(self):
        """
        Tests what happens when the config file cannot be found.
        """
        with self.assertRaises(FileNotFoundError):
            self.config = Config("this_file_does_not_exist.json")

    def test_get_vno_list(self):
        """
        Test get_vno_list().
        """
        vno_list = self.config.get_vno_list()
        self.assertIsInstance(vno_list, list)
        for vno in vno_list:
            self.assertIsInstance(vno, str)

    def test_get_vnos_for_equipment_analysis(self):
        """
        Test get_vno_list().
        """
        vno_list = self.config.get_vnos_for_equipment_analysis()
        self.assertIsInstance(vno_list, list)
        for vno in vno_list:
            self.assertIsInstance(vno, str)

    def test_get_interval_days_for_equipment_analysis(self):
        """
        Test get_interval_days_for_equipment_analysis().
        """
        self.assertIsInstance(
            self.config.get_interval_days_for_equipment_analysis(self.test_vno), int
        )

    def test_get_interval_days_for_cable_analysis(self):
        """
        Test get_interval_days_for_cable_analysis().
        """
        self.assertIsInstance(self.config.get_interval_days_for_cable_analysis(self.test_vno), int)

    def test_get_thresh_to_equipment_priority(self):
        """
        Test get_thresh_to_equipment_priority().
        """
        self.verify_object_is_threshold_list(
            self.config.get_thresh_to_equipment_priority(self.test_vno)
        )

    def test_get_thresh_to_cable_priority(self):
        """
        Test get_thresh_to_cable_priority().
        """
        self.verify_object_is_threshold_list(
            self.config.get_thresh_to_cable_priority(self.test_vno)
        )

    def verify_object_is_threshold_list(self, threshold_list):
        """
        A helper function for the tests to verify that something is a threshold list.

        :param threshold_list: a list of dictionaries that maps priority ratings
                               to thresholds, of the form:
                                    [
                                      {"priority": 1, "threshold": 10},
                                      {"priority": 2, "threshold": 20},
                                      {"priority": 3, "threshold": 30}
                                    ]
        """
        self.assertIsInstance(threshold_list, list)
        for threshold in threshold_list:
            self.assertIsInstance(threshold, dict)
            self.assertIn(PRIORITY_PROP_STR, threshold)
            self.assertIn(THRESHOLD_PROP_STR, threshold)


def get_test_config_file_path(env):
    """
    Get the config file name for running the tests on. The file
    path will be different locally than it is when running the job.

    :param env: a string "prod", "preprod", or "dev"
    :return: a string representing the local file path for the job config
    """
    return (
        f"{os.path.abspath('jobs/terminal_attention_prioritizer')}"
        f"/{config_handler._get_config_file_name(env)}"
    )


class TestOutputSchema(unittest.TestCase):
    """
    Test that the schema for the messages on the output databus stream
    works as expected and that the example message adheres to the schema.
    """

    def test_minimal_output_message(self):
        """
        This message has the minimum required fields for the schema to accept it.
        """
        minimal_message = {
            "mac": "00A0B0DDEEFF",
            "vno": "exederes",
            DATABUS_SCHEMA_VERSION_PROP_STR: "exederes_0.0",
            TIMESTAMP_PROP_STR: 1618955100,
        }
        self.assertTrue(
            common_utils.does_json_instance_fit_schema(
                minimal_message, producer.OUTPUT_MESSAGE_SCHEMA, verbose=True,
            )
        )

    def test_example_output_message(self):
        """
        Test that the example message meets the message schema.
        """
        self.assertTrue(
            common_utils.does_json_instance_fit_schema(
                producer.EXAMPLE_MESSAGE, producer.OUTPUT_MESSAGE_SCHEMA, verbose=True,
            )
        )


class TestOutputStreamProducer(unittest.TestCase):
    """
    Test the internal helper functions in attention_priority_stream_producer.py
    """

    PRIORITIZATION_METRICS_EXAMPLE = {
        "exederes": {
            "AABBCCDDEEFE": {
                "equipment": {"equipment_priority": 2, "recent_phy_offline_event_count": 107},
                "cable": {"cable_priority": 3, "recent_ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 3},
                "npv": True,
            }
        }
    }

    def test_format_prioritization_metrics_as_databus_messages(self):
        """
        Test _format_prioritization_metrics_as_databus_messages()
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        databus_msg = producer._format_prioritization_metrics_as_databus_messages(
            config, self.PRIORITIZATION_METRICS_EXAMPLE
        )
        # print(databus_msg)
        self.assertTrue(
            common_utils.does_json_instance_fit_schema(
                databus_msg[0], producer.OUTPUT_MESSAGE_SCHEMA, verbose=True
            )
        )

    def test_publish_prioritization_metrics(self):
        """
        Test publish_prioritization_metrics()
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        databus_msg = producer._format_prioritization_metrics_as_databus_messages(
            config, self.PRIORITIZATION_METRICS_EXAMPLE
        )
        producer.publish_prioritization_metrics(config, self.PRIORITIZATION_METRICS_EXAMPLE)


class TestCombiningResults(unittest.TestCase):
    """
    Test the combine_results() function in prioritize_attention_for_terminals.py
    """

    RESOUCES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "/resources"))
    sys.path.insert(0, RESOUCES_PATH)
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "./resources/")))
    from combined_cases import TESTS

    def test_combine_results(self):
        """
        Test the combine_results() function in prioritize_attention_for_terminals.py
        This only test the sunny case of this function
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        for test_case, test_data in self.TESTS.items():
            print(f"run test_combine_results case: {test_case}")
            input_data = test_data["inputs"]
            expected_results = test_data["outputs"]
            results = combine_results(
                config=config,
                provisioned_modems=input_data["provisioned_modems"],
                amr_info=input_data["amr_info"],
                equip_info=input_data["equip_info"],
                cable_info=input_data["cable_info"],
            )
            if results != expected_results:
                print("results:")
                print("=====================================================")
                print(results)
                print("=====================================================")
                print("expected_results:")
                print("=====================================================")
                print(expected_results)
                print("=====================================================")
                print("=====================================================")
            self.assertTrue(results == expected_results)


class TestOutageHistConsumer(unittest.TestCase):
    """
    Test the internal helper functions in outage_hist_consumer.py
    """

    @unittest.skip("Run this before submit!")
    def test_format_python(self):
        """
        run format_python
        """
        print("run format_python outage_hist_consumer.py")
        os.system(
            "./format_python.sh \
                    -m read ./jobs/terminal_attention_prioritizer/outage_hist_consumer.py"
        )

    def test_query_outage_hist_for_phy_related_offline_events(self):
        """
        Test _query_outage_hist_for_phy_related_offline_events().
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        events_dict = outage_hist_consumer._query_outage_hist_for_phy_related_offline_events(
            config, vno=VNO
        )
        offline_uts = len(events_dict)
        print("Test _query_outage_hist_for_phy_related_offline_events() ")
        print(
            f"_query_outage_hist_for_phy_related_offline_events vno:{VNO},offline_uts:{offline_uts}"
        )
        if offline_uts > 0:
            # print(events_dict)
            mac_address_1 = next(iter(events_dict))
            event_count = events_dict[mac_address_1]
            self.assertTrue(event_count > 0)

    def test_query_outage_hist_for_ptria_err_offline_events(self):
        """
        Test _query_outage_hist_for_ptria_err_offline_events().
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        events_dict = outage_hist_consumer._query_outage_hist_for_ptria_err_offline_events(
            config, vno=VNO
        )
        # the ptria error may not have accured
        offline_uts = len(events_dict)
        print(
            f"test_query_outage_hist_for_ptria_err_offline_events vno:{VNO},offline_uts:{offline_uts}"
        )
        if offline_uts > 0:
            # print(events_dict)
            mac_address_1 = next(iter(events_dict))
            event_count = events_dict[mac_address_1]
            self.assertTrue(event_count > 0)

    def test_determine_equip_priority_metrics_from_query(self):
        """
        Test _determine_equip_priority_metrics_from_query().
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        results = outage_hist_consumer._determine_equip_priority_metrics_from_query(config, VNO)
        offline_uts = len(results)
        print(
            f"test_determine_equip_priority_metrics_from_query vno:{VNO},offline_uts:{offline_uts}"
        )
        if offline_uts > 0:
            # print(results)
            mac_address_1 = next(iter(results))  # only check the first entry to save time
            self.assertTrue(len(mac_address_1) == 12)
            equipment = results[mac_address_1][EQUIPMENT_PROP_STR]
            equipment_priority = equipment[EQUIPMENT_PRIORITY_PROP_STR]
            self.assertTrue(0 <= equipment_priority <= 3)
            recent_phy_offline_event_count = equipment[RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR]
            self.assertTrue(isinstance(recent_phy_offline_event_count, int))

    def test_determine_cable_priority_metrics_from_query(self):
        """
        Test _determine_cable_priority_metrics_from_query().
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        results = outage_hist_consumer._determine_cable_priority_metrics_from_query(config, VNO)
        offline_uts = len(results)
        print(
            f"test_determine_cable_priority_metrics_from_query vno:{VNO},offline_uts:{offline_uts}"
        )
        if offline_uts > 0:
            # print(results)
            mac_address_1 = next(iter(results))  # only check the first entry to save time
            self.assertTrue(len(mac_address_1) == 12)
            cable = results[mac_address_1][CABLE_PROP_STR]
            cable_priority = cable[CABLE_PRIORITY_PROP_STR]
            self.assertTrue(0 <= cable_priority <= 3)
            recent_cable_offline_event_count = cable[RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR]
            self.assertTrue(isinstance(recent_cable_offline_event_count, int))

    def test_determine_equip_priority_metrics(self):
        """
        Test determine_equip_priority_metrics().
        """
        print("test_determine_equip_priority_metrics")
        config = Config(config_file_path=get_test_config_file_path(ENV))
        results = outage_hist_consumer.determine_equip_priority_metrics(config)
        if len(results):
            # print(results)
            for vno, item in results.items():
                print(f"test_determine_equip_priority_metrics vno:{vno} start")
                print(f"total offline uts: {len(item)}")
                self.assertTrue(vno in config.get_vnos_for_equipment_analysis())
                mac_address_1 = next(iter(item))  # only check the first entry to save time
                self.assertTrue(len(mac_address_1) == 12)
                equipment = item[mac_address_1][EQUIPMENT_PROP_STR]
                equipment_priority = equipment[EQUIPMENT_PRIORITY_PROP_STR]
                self.assertTrue(0 <= equipment_priority <= 3)
                recent_phy_offline_event_count = equipment[RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR]
                self.assertTrue(isinstance(recent_phy_offline_event_count, int))
                print(f"test_determine_equip_priority_metrics vno:{vno} end")

    def test_determine_cable_priority_metrics(self):
        """
        Test determine_cable_priority_metrics()
        """
        print("test_determine_cable_priority_metrics")
        config = Config(config_file_path=get_test_config_file_path(ENV))
        results = outage_hist_consumer.determine_cable_priority_metrics(config)
        if len(results):
            # print(results)
            for vno, item in results.items():
                print(f"test_determine_cable_priority_metrics vno:{vno} start")
                self.assertTrue(vno in config.get_vnos_for_equipment_analysis())
                print(vno)
                if item is not None and len(item) > 0:
                    mac_address_1 = next(iter(item))  # only check the first entry to save time
                    self.assertTrue(len(mac_address_1) == 12)
                    cable = item[mac_address_1][CABLE_PROP_STR]
                    cable_priority = cable[CABLE_PRIORITY_PROP_STR]
                    self.assertTrue(0 <= cable_priority <= 3)
                    recent_ptria_err_event_count = cable[RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR]
                    self.assertTrue(isinstance(recent_ptria_err_event_count, int))
                print(f"test_determine_cable_priority_metrics vno:{vno} end")


class TestAmrConsumer(unittest.TestCase):
    """
    Test the internal helper functions in amr_consumer.py.
    """

    @unittest.skip("Run this before submit!")
    def test_format_python(self):
        """
        run format_python
        """
        os.system(
            "./format_python.sh -m read ./jobs/terminal_attention_prioritizer/amr_consumer.py"
        )

    def test_download_latest_antenna_mispoint_report(self):
        """
        Test _download_latest_antenna_mispoint_report().
        """
        config = Config(config_file_path=get_test_config_file_path(ENV))
        amr = amr_consumer._download_latest_antenna_mispoint_report(config)
        self.assertTrue(VNO in amr.keys())
        # for key, value in amr.items():
        #     print(key,':', value)
        #     print('=========================================')

    def test_determine_mispoint_priority_metrics(self):
        """
        Test _determine_mispoint_priorities_from_amr().
        """

        config = Config(config_file_path=get_test_config_file_path("prod"))
        reports = amr_consumer.determine_mispoint_priority_metrics(config)
        self.assertTrue("exederes" in reports.keys())
        mac_address_1 = next(iter(reports["exederes"]))
        self.assertTrue(mac_address_1)
        priority = reports["exederes"][mac_address_1][MISPOINT_PROP_STR][MISPOINT_PRIORITY_PROP_STR]
        self.assertTrue(5 > priority > 0)


class TestAvroSchema(unittest.TestCase):
    """
    Test the TAP databu's Avro schema.
    """

    RESOUCES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources"))
    AVRO_SCHEMA = os.path.join(RESOUCES_PATH, "databus_stream_schema.avsc")
    TEST_RESOUCES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "./resources"))
    AVRO_SCHEMA_INVALID = os.path.join(TEST_RESOUCES_PATH, "databus_stream_schema_invalid.avsc")

    EXAMPLE_MESSAGE_GOOD = {
        MAC_PROP_STR: "00A0B0DDEEFF",
        VNO_PROP_STR: "exederes",
        DATABUS_SCHEMA_VERSION_PROP_STR: "exederes_0.0",
        TIMESTAMP_PROP_STR: 1618955100,
        EQUIPMENT_PROP_STR: {
            EQUIPMENT_PRIORITY_PROP_STR: 3,
            RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR: 107,
        },
        MISPOINT_PROP_STR: {MISPOINT_PRIORITY_PROP_STR: 2},
        CABLE_PROP_STR: {CABLE_PRIORITY_PROP_STR: 3, RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR: 52},
        NPV_PROP_STR: True,
    }

    EXAMPLE_MESSAGE_BAD = {
        MAC_PROP_STR: "00A0B0DDEEFF",
        VNO_PROP_STR: "exederes",
        DATABUS_SCHEMA_VERSION_PROP_STR: "exederes_0.0",
        TIMESTAMP_PROP_STR: 1618955100,
        EQUIPMENT_PROP_STR: {
            EQUIPMENT_PRIORITY_PROP_STR: "three",  # instead of 3
            RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR: 107,
        },
        MISPOINT_PROP_STR: {MISPOINT_PRIORITY_PROP_STR: 2},
        CABLE_PROP_STR: {CABLE_PRIORITY_PROP_STR: 3, RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR: 52},
        NPV_PROP_STR: True,
    }

    def test_valid_schema_data(self):
        """
        test the valid databus schema and message
        """
        avro_schema = Avro_schema(self.AVRO_SCHEMA)
        parsed_schema = avro_schema.parse()
        result = parsed_schema.validate(self.EXAMPLE_MESSAGE_GOOD)
        self.assertTrue(result)

    def test_invalid_schema_data(self):
        """
        test the invalid databus schema or message
        """
        avro_schema = Avro_schema(self.AVRO_SCHEMA_INVALID)
        with self.assertRaises(ValueError):
            parsed_schema = avro_schema.parse()
            parsed_schema.validate(self.EXAMPLE_MESSAGE_GOOD)

        avro_schema = Avro_schema(self.AVRO_SCHEMA)
        parsed_schema = avro_schema.parse()
        with self.assertRaises(ValueError):
            parsed_schema.validate(self.EXAMPLE_MESSAGE_BAD)


class TestNpvCalculator(unittest.TestCase):
    """
    Test the internal helper functions in npv_caclulator.py.
    """

    # TODO BBCTERMSW-28558


class TestProvisionedModemsConsumer(unittest.TestCase):
    """
    Test the internal helper functions in provisioned_modems_consumer.py.
    """

    def test_parse_downloaded_list_of_provisioned_modems(self):
        """
        Test _parse_downloaded_list_of_provisioned_modems().
        """
        # TODO BBCTERMSW-28552


# Run all the tests in this file.
if __name__ == "__main__":
    unittest.main()
