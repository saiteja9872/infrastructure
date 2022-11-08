"""
This file contains data file for the unit testing class unit_tests.TestCombiningResults
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jobs.terminal_attention_prioritizer._config_handler import Config
import jobs.terminal_attention_prioritizer._config_handler as config_handler

ENV = "prod"
config_path = (
    f"{os.path.abspath('jobs/terminal_attention_prioritizer')}"
    f"/{config_handler._get_config_file_name(ENV)}"
)
config = Config(config_file_path=config_path)

TESTS = {}

# sunny testing case 1
TESTS["sunny1"] = {
    "inputs": {  # input data
        "vnos": ["exederes"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF1": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            }
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            }
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            }
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        }
    },
}
# sunny testing case 2
TESTS["sunny2"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF1": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_with_empty_provisioned_modems"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF1": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_with_different_provisioned_modems"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEFA", "AABBCCDDEEFB"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF1": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEFA": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
            "AABBCCDDEEFB": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
            "AABBCCDDEEF1": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}
TESTS["rainy_missing_ut_in_equip_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_missing_ut_in_eqpt_cable_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_missing_ut_in_eqpt_cable_mispoint_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "exederes": {
                "AABBCCDDEEF2": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
            "AABBCCDDEEF2": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_missing_one_vno_in_eqip_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "exederes": {
                "AABBCCDDEEF1": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF2": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "exederes": {
                "AABBCCDDEEF1": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF2": {"mispoint": {"mispoint_priority": 2}},
            },
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF2": {
                "equipment": {},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_missing_one_vno_in_eqip_cable_amr_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
            "telbr": {
                "AABBCCDDEEF3": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100}
                },
                "AABBCCDDEEF4": {
                    "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101}
                },
            },
        },
        "cable_info": {
            "telbr": {
                "AABBCCDDEEF3": {"cable": {"cable_priority": 3, "ptria_err_event_count": 100}},
                "AABBCCDDEEF4": {"cable": {"cable_priority": 3, "ptria_err_event_count": 101}},
            },
        },
        "amr_info": {
            "telbr": {
                "AABBCCDDEEF3": {"mispoint": {"mispoint_priority": 1}},
                "AABBCCDDEEF4": {"mispoint": {"mispoint_priority": 2}},
            },
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
            "AABBCCDDEEF2": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
        },
        "telbr": {
            "AABBCCDDEEF3": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 100},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 100},
                "mispoint": {"mispoint_priority": 1},
            },
            "AABBCCDDEEF4": {
                "equipment": {"equipment_priority": 3, "recent_phy_offline_event_count": 101},
                "cable": {"cable_priority": 3, "ptria_err_event_count": 101},
                "mispoint": {"mispoint_priority": 2},
            },
        },
    },
}

TESTS["rainy_missing_all_info"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {"exederes": ["AABBCCDDEEF1", "AABBCCDDEEF2"]},
        "equip_info": {
        },
        "cable_info": {
        },
        "amr_info": {
        },
    },
    "outputs": {  # expected output
        "exederes": {
            "AABBCCDDEEF1": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
            "AABBCCDDEEF2": {
                "equipment": {},
                "cable": {},
                "mispoint": {},
            },
        },
        "telbr": {}
    },
}

TESTS["rainy_missing_all_info_and_provisioned_modems"] = {
    "inputs": {  # input data
        "vnos": ["exederes", "telbr"],  # the list of vnos in the sample data below
        "provisioned_modems": {},
        "equip_info": {
        },
        "cable_info": {
        },
        "amr_info": {
        },
    },
    "outputs": {  # expected output
        "exederes": {
        },
        "telbr": {
        },
    },
}
# populate the above sample expected output with empty vno data for vnos not in
# the inputs
vno_list = config.get_vno_list()
for test_case, test_data in TESTS.items():
    for vno in vno_list:
        if vno not in test_data["inputs"]["vnos"]:
            test_data["outputs"][vno] = {}
