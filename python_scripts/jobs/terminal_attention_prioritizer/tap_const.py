"""
tap.constant.py
This file specify the constants for the terminal_attention_prioritizer job
"""

# databus stream name
# STREAM_NAME = "terminal_attention_priority"
STREAM_NAME = "ut-tap"

# Used for parsing XML data returned by the SDP API
NS = {"default": "http://sdp.viasat.com/sdp/schema/SDP"}

# seconds
ONE_MINUTE = 60

# The valid possible VNO options.
# See https://wiki.viasat.com/display/SDP/VNO-to-Realm+Mapping.
VNO_OPTIONS_RESIDENTIAL = [
    "brcwf",
    "brres",
    "exederes",
    # "iccwf",
    # "lacwf",
    # "mtres",
    "mxres",
    # "rwres",
    "telbr",
    # "vsgbs",
    "xci",
    # "vsxgd",
]
VNO_OPTIONS_MOBILITY = [
    "auscmob",
    "bizav",
    "gmbc1",
    "vscar",
    "vsxmb",
]
# VNO_OPTIONS = VNO_OPTIONS_RESIDENTIAL + VNO_OPTIONS_MOBILITY
VNO_OPTIONS = VNO_OPTIONS_RESIDENTIAL

PTRIA_OFFLINE_EVENT_CODES = {41: "MAC_RESCAN_PTRIA_ERROR"}  # pTRIA Communications Error
PHY_OFFLINE_EVENT_CODES = {
    3: "MAC_RESCAN_RNG_ABORT",  # Received RNG-RSP Abort message
    5: "MAC_RESCAN_LINK_LOSS",  # Forward-link lost and fell offline
    21: "MAC_RESCAN_KEEPALIVE",  # Periodic RNG-RSP feedback timeout
    41: "MAC_RESCAN_PTRIA_ERROR",  # pTRIA Communications Error
    47: "MAC_RESCAN_NO_RL_MAPS",  # UT took itself offline due to loss of RL maps (experimental)
}

# Property and definition name strings
MAC_PROP_STR = "mac"
VNO_PROP_STR = "vno"
CONFIG_SCHEMA_VERSION_PROP_STR = "global-schema-version"
CONFIG_VNO_SCHEMA_VERSION_PROP_STR = "vno-schema-version"
DATABUS_SCHEMA_VERSION_PROP_STR = "schema_version"
TIMESTAMP_PROP_STR = "timestamp"
EQUIPMENT_PROP_STR = "equipment"
EQUIPMENT_PRIORITY_PROP_STR = "equipment_priority"
RECENT_PHY_OFFLINE_EVENT_COUNT_PROP_STR = "recent_phy_offline_event_count"
MISPOINT_PROP_STR = "mispoint"
MISPOINT_PRIORITY_PROP_STR = "mispoint_priority"
CABLE_PROP_STR = "cable"
CABLE_PRIORITY_PROP_STR = "cable_priority"
RECENT_PTRIA_ERR_EVENT_COUNT_PROP_STR = "recent_ptria_err_event_count"
NPV_PROP_STR = "npv"
GLOBAL_SETTINGS_PROP_STR = "global-settings"
VNO_SPECIFIC_SETTINGS_PROP_STR = "vno-specific-settings"
PHY_OFFLINE_EVENT_THRESH_PROP_STR = "phy-offline-event-thresh"
DAYS_PROP_STR = "days"
THRESH_TO_EQUIPMENT_PRIORITY_PROP_STR = "thresh-to-equipment-priority"
PTRIA_ERR_EVENT_THRESH_PROP_STR = "ptria-err-event-thresh"
THRESH_TO_CABLE_PRIORITY_PROP_STR = "thresh-to-cable-priority"
THRESHOLD_LIST_DEFN_STR = "threshold-list"
PRIORITY_PROP_STR = "priority"
THRESHOLD_PROP_STR = "threshold"

# databus terminal_attention_priority stream schema version
DATABUS_TAP_SCHEMA_VERSION_0_0 = "tap_0_0"
