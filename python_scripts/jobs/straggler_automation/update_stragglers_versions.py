"""
Contains lists of global constants used in the update_stragglers.py job.
These versions have the potential to change semi-frequently as apps are updated
"""

# The following lists are acceptable (or unacceptable in some cases) versions for applications

# Acceptable Modoc versions. Last updated: 09/20/2021
# Latest update description: added version 2.5
MODOC_VERSIONS = ["2.4", "2.5"]

# Unacceptable Modoc Rules versions. Last updated: 09/02/2021
# Latest update description: Added version 3.16
MODOC_RULES_UNACCEPTABLE_VERSIONS = [
    "3.8",
    "3.10",
    "3.12",
    "3.15",
    "3.16",
    "ERROR",
    "UNKNOWN",
]

# Unacceptable Allowlist versions. Last updated: 05/11/2022
# Latest update description: changed to catch all 5.2.x versions
ALLOWLIST_UNACCEPTABLE_VERSIONS = [
    "5.0.",
    "5.1.",
    "5.2.",
]

# Acceptable Vstat versions. Last updated: 07/26/2021
# Latest update description:
VSTAT_VERSIONS = [
    "1.2.13",
    "2.1.4",
]

# Acceptable ESP versions. Last updated: 07/26/2021
# Latest update description: add version 0.2.69
ESP_VERSIONS = [
    "0.2.67",
    "0.2.69",
]

# Acceptable UT Statpush versions. Last updated: 07/26/2021
# Latest update description:
STATPUSH_UT_VERSIONS = [
    "3.5",
]

# Acceptable UT2 Statpush versions. Last updated: 08/13/2021
# Latest update description: remove version 3.0
STATPUSH_UT2_VERSIONS = [
    "3.5",
]

# Acceptable DATA Statpush versions. Last updated: 07/26/2021
# Latest update description:
STATPUSH_DATA_VERSIONS = [
    "3.4",
]

# Acceptable SPOCK Statpush versions. Last updated: 10/21/2021
# Latest update description: Added 3.8 for newest cao statpush config
STATPUSH_SPOCK_VERSIONS = [
    "3.4",
    "3.7",
    "3.8",
]

# This is formatted as a list of dictionaries to match the formatting coming from ACS db SQL query
# OTA modems requiring specialized modoc rules. Last updated: 12/03/2021
# Latest update description: Added 4 macs for Craig Cantrell Duluth test station
OTA_MAC_LIST = [
    {"cid": "00A0BC6C7E3B"},
    {"cid": "00A0BC6EB384"},
    {"cid": "00A0BC6C7E2A"},
    {"cid": "00A0BC6EB260"},
    {"cid": "00A0BC72D5F8"},
    {"cid": "00A0BC6EB1EC"},
    {"cid": "00A0BC4B52F8"},
    {"cid": "00A0BC6211F0"},
    {"cid": "00A0BC470174"},
    {"cid": "00A0BC72D9B0"},
    {"cid": "00A0BC72D834"},
    {"cid": "00A0BC72D97C"},
    {"cid": "00A0BC72D97B"},
    {"cid": "00A0BC72D87C"},
    {"cid": "00A0BC6EB1E8"},
    {"cid": "00A0BC6C7E34"},
]


# Translation of hardware types. Some have multiple applicable types
# Legacy UT hardware types. Also known as terminal type 2
UT_HW = [
    "UT_7P3_V1",
    "7-P3_V1",
]

# UT2 hardware types. Also known as SB2+. Also known as terminal type 12
UT2_HW = [
    "10504-UT2_XC_XD_XE_US1_ASIC2V2",
    "UT2_10504UT2_XC/XD/XE_US1_ASIC2v2",
    "10303-UT2_XC_XD_XE_GEN_ASIC2",
    "10304-UT2_XC_XD_XE_GEN_ASIC2V2",
    "10404-UT2_XC_XD_XE_AU1_ASIC2V2",
]

# DATA hardware types. Also known as terminal type 21
DATA_HW = [
    "20000-DATA_P1",
]

# SPOCK hardware types. Also known as terminal type 21
SPOCK_HW = [
    "20100-SPOCK_P1",
]
