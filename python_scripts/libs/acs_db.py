"""
Contains functionality for querying the ACS database (read-only).
"""

import os
from libs import common_utils, vault_utils
from libs.mysql_db import MySqlDb

# The SQL fragment containing the fields that are
# relevant when examining drifted modems' beam info.
MODEM_BEAM_INFO_COLUMNS = (
    "m.cid, ActualSatelliteId, ActualBeamId, ActualBeamPolarization,"
    " PrimarySatelliteId, PrimaryBeamID, PrimaryBeamPolarization,"
    " PrimaryBeamIDPending, PrimaryBeamPolarizationPending,"
    " SoftwareVersion, ActualNspRealm"
)

# A SQL fragment that points at modem beam info in the ACS db (goes in the FROM clause)
MODEM_BEAM_INFO_DATA = (
    "acs_db.vss_Modem m INNER JOIN acs_db.vss_ModemMetaData mmd ON m.cid = mmd.cid"
)

# A SQL fragment that searches for modems whose goal beams and actual beams don't
# match. Defers to the pending goal beam if there is one. Goes in the WHERE clause.
BEAMS_MISMATCHED = (
    "("
    "(PrimaryBeamIDPending is NULL AND (ActualBeamId <> PrimaryBeamID))"
    " OR "
    "(PrimaryBeamIDPending IS NOT NULL AND (ActualBeamId <> PrimaryBeamIDPending))"
    ")"
)

POLARIZATIONS_NOT_NULL = (
    "(ActualBeamPolarization IS NOT NULL"
    " AND NOT (PrimaryBeamPolarization IS NULL AND PrimaryBeamPolarizationPending IS NULL))"
)

# A SQL fragment that filters out modems trying to move to another satellite
# (handovers are outside the scope of our automations) (goes in the WHERE clause)
NOT_TRYING_TO_MOVE_SATELLITES = (
    "(PrimarySatelliteID = ActualSatelliteId"
    " OR PrimarySatelliteID = '' OR PrimarySatelliteID IS NULL)"
)

# A SQL fragment that points at modems that are on the wrong beam (goes after the FROM)
MISMATCHED_BEAMS = (
    f"{MODEM_BEAM_INFO_DATA} WHERE {BEAMS_MISMATCHED}"
    f" AND {POLARIZATIONS_NOT_NULL} AND {NOT_TRYING_TO_MOVE_SATELLITES}"
)

# A SQL fragment that points at modems with blank goal beams (goes after the FROM)
BLANK_GOAL_BEAMS = (
    f"{MODEM_BEAM_INFO_DATA} WHERE (ActualBeamId IS NOT NULL) AND (PrimaryBeamID IS NULL)"
)

# A SQL fragment that points at modems with goal beams that have been cleared by another
# run of this job (goes after the FROM)
CLEARED_GOAL_BEAMS = (
    f"{MODEM_BEAM_INFO_DATA} WHERE "
    f"("
    f"    ("
    f"        (PrimaryBeamIDPending is NULL OR PrimaryBeamIDPending = '')"
    f"         AND "
    f"        (0 = PrimaryBeamID)"
    f"    )"
    f"    OR "
    f"    ("
    f"        (PrimaryBeamIDPending IS NOT NULL AND PrimaryBeamIDPending <> '')"
    f"         AND "
    f"        (0 = PrimaryBeamIDPending)"
    f"    )"
    f")"
    f" AND "
    f"{POLARIZATIONS_NOT_NULL}"
)

# The SQL fragment for the sort order in which we want to pull rows from the ACS db;
# since modems check in with the ACS on their own regular schedules, this allows the
# job to pull modems in a sort of random order (that won't keep pulling the same modems
# each time) in a manner that's a lot faster than a true random sort, which would cause
# the queries to time out.
ORDER = "ORDER BY mmd.last_updated DESC"

# The default list of realms on whose modems our automations are permitted to operate.
PERMITTED_REALMS_DEFAULT = [
    # US residential
    "aut.res.viasat.com",
    "abr.res.viasat.com",
    "abp.res.viasat.com",
    "sb2.res.viasat.com",
    "biz.res.viasat.com",
    "com.res.viasat.com",
    "mx1.res.viasat.com",
    "mx2.res.viasat.com",
    "mx3.res.viasat.com",
    "mx4.res.viasat.com",
    "mx7.res.viasat.com",
    "mx8.res.viasat.com",
    "sc1.res.viasat.com",
    "sc2.res.viasat.com",
    "pr1.res.viasat.com",
    "pr2.res.viasat.com",
    "mx6.res.viasat.com",
    "exp.res.viasat.com",
    "ht1.res.viasat.com",
    "q01.res.viasat.com",
    "q02.res.viasat.com",
    "q03.res.viasat.com",
    "q04.res.viasat.com",
    "360.res.viasat.com",
    "cao.res.viasat.com",
    # brazil residential
    "bra.brres.viasat.com",
    "rw1.brres.viasat.com",
    "rw2.brres.viasat.com",
    "bra.telbr.viasat.com",
    "per.telbr.viasat.com",
    "br1.brcwf.viasat.com",
    # mexico residential
    "mx5.mxres.viasat.com",
    "mx6.mxres.viasat.com",
    "lte.mxres.viasat.com",
    # XCI
    "hts.xplornet.com",
]

# List of Brazil Realms
ALL_BRAZIL_REALMS = [
    "bra.brres.viasat.com",
    "rw1.brres.viasat.com",
    "rw2.brres.viasat.com",
    "bra.telbr.viasat.com",
    "per.telbr.viasat.com",
    "br1.brcwf.viasat.com",
]

# List of hardware types in Brazil residential network
BRAZIL_RES_HW_TYPES = [
    'UT_7P3_V1',
    '7-P3_V1',
    '10504-UT2_XC_XD_XE_US1_ASIC2V2',
    'UT2_10504UT2_XC/XD/XE_US1_ASIC2v2',
    '10303-UT2_XC_XD_XE_GEN_ASIC2',
    '10304-UT2_XC_XD_XE_GEN_ASIC2V2',
    '10404-UT2_XC_XD_XE_AU1_ASIC2V2',
]

# The SQL fragment for excluding unprovisioned, offline, non-Viasat and maritime modems
# cid not equal to '' will eliminate unprovisioned modems
# state not equal to 4 will eliminate offline modems (4 is the code used by ACS for
# offline modems; there is no string equivalent in ACS)
# software version not like 'SPOCK_4.0.0.%%' will eliminate maritime modem builds
# software version not like 'MOBTEST_%%' will exclude DATA modems acting as mobility
# cid like '00A0BC%%' will ensure only Viasat modems are found in the database query
MODEM_STRAGGLER_EXCLUSIONS = (
    "cid != '' AND state != 4 AND softwareVersion NOT LIKE 'SPOCK_4.0.0.%%' AND softwareVersion "
    "NOT LIKE 'MOBTEST_%%' AND cid LIKE '00A0BC%%'"
)

MODEM_EXCLUSIONS_ON_OR_OFFLINE = (
    "cid != '' AND softwareVersion NOT LIKE 'SPOCK_4.0.0.%%' AND softwareVersion "
    "NOT LIKE 'MOBTEST_%%' AND cid LIKE '00A0BC%%'"
)

# The SQL fragment containing the columns and database for finding modem application stragglers
MODEM_STRAGGLER_COLUMNS_DB_MODEMS = (
    f"cid FROM acs_db.CPEManager_CPEs WHERE {MODEM_STRAGGLER_EXCLUSIONS} AND hardwareVersion IN "
)

# The SQL fragment containing the standard query for missing apps or older app versions
MODEM_STRAGGLER_DIFF_INNER_DB = "cid FROM AXServiceTable WHERE cid LIKE '00A0BC%%' AND"

# The SQL fragment containing the standard query for app queries outside of the app version
MODEM_STRAGGLER_APPS = "servicetype = 'App' AND"


class AcsDb:
    """
    The ACS database class
    """

    def __init__(self):
        """
        Initialize the AcsDb class by pulling the credentials
        from Vault and connecting to the MySQL database.
        """
        usr = common_utils.ACS_DB_SERVICE_ACCT_USR
        pwd = vault_utils.get_acs_db_service_account_password()
        hostname = common_utils.get_expected_env_var("acs_db_hostname")
        db_name = "acs_db"
        self.database = MySqlDb(usr, pwd, hostname, db_name)

    def connect(self):
        """
        Connect to the ACS database.
        """
        print(" \nattempting to connect to the ACS database")
        self.database.connect()

    def get_drifted_modems(self, use_dictionary=True, limit=None):
        """
        Retrieve the list of modems on the wrong beam from the ACS database.
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param limit: a number representing the maximum quantity
                      of modems to pull from the database
        :return: a list of dictionaries or tuples that contain
                 (mac, current sat, current beam, goal sat, goal beam)
        """
        if limit and not common_utils.is_valid_number(limit):
            print(f' \nERROR: non-integer limit "{limit}" provided')
            limit = None
        permitted_realms = get_permitted_realms()
        format_str = ", ".join(["%s"] * len(permitted_realms))
        if limit is None:
            return self.database.execute_query(
                f"SELECT {MODEM_BEAM_INFO_COLUMNS} FROM {MISMATCHED_BEAMS}"
                f" AND ActualNspRealm IN (%s) {ORDER};" % format_str,
                params=tuple(permitted_realms),
                result_expected=True,
                use_dictionary=use_dictionary,
            )
        return self.database.execute_query(
            f"SELECT {MODEM_BEAM_INFO_COLUMNS} FROM {MISMATCHED_BEAMS}"
            f" AND ActualNspRealm IN (%s) {ORDER} LIMIT %%s;" % format_str,
            params=tuple(permitted_realms) + (int(limit),),
            result_expected=True,
            use_dictionary=use_dictionary,
        )

    def get_modems_with_blank_goal_beams(self, use_dictionary=True, limit=None):
        """
        Get modems from the ACS that have blank goal beams.
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param limit: a number representing the maximum quantity
                      of modems to pull from the database
        :return: a list of dictionaries or tuples that contain
                (mac, current sat, current beam, goal sat, goal beam, realm)
        """
        if limit and not common_utils.is_valid_number(limit):
            print(f' \nERROR: non-integer limit "{limit}" provided')
            limit = None
        permitted_realms = get_permitted_realms()
        format_str = ", ".join(["%s"] * len(permitted_realms))
        if limit is None:
            return self.database.execute_query(
                f"SELECT {MODEM_BEAM_INFO_COLUMNS}, ActualNspRealm"
                f" FROM {BLANK_GOAL_BEAMS} AND ActualNspRealm IN (%s);" % format_str,
                params=tuple(permitted_realms),
                result_expected=True,
                use_dictionary=use_dictionary,
            )
        return self.database.execute_query(
            f"SELECT {MODEM_BEAM_INFO_COLUMNS}, ActualNspRealm"
            f" FROM {BLANK_GOAL_BEAMS} AND ActualNspRealm IN (%s) LIMIT %%s;" % format_str,
            params=tuple(permitted_realms) + (int(limit),),
            result_expected=True,
            use_dictionary=use_dictionary,
        )

    def get_modems_with_cleared_goal_beams(self, use_dictionary=True, limit=None):
        """
        Get modems from the ACS that have goal beams set to 0.
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param limit: a number representing the maximum quantity
                      of modems to pull from the database
        :return: a list of dictionaries or tuples that contain
                (mac, current sat, current beam, goal sat, goal beam, realm)
        """
        if limit and not common_utils.is_valid_number(limit):
            print(f' \nERROR: non-integer limit "{limit}" provided')
            limit = None
        permitted_realms = get_permitted_realms()
        format_str = ", ".join(["%s"] * len(permitted_realms))

        if limit is None:
            return self.database.execute_query(
                f"SELECT {MODEM_BEAM_INFO_COLUMNS}, ActualNspRealm"
                f" FROM {CLEARED_GOAL_BEAMS} AND ActualNspRealm IN (%s);" % format_str,
                params=tuple(permitted_realms),
                result_expected=True,
                use_dictionary=use_dictionary,
            )
        return self.database.execute_query(
            f"SELECT {MODEM_BEAM_INFO_COLUMNS}, ActualNspRealm"
            f" FROM {CLEARED_GOAL_BEAMS} AND ActualNspRealm IN (%s) LIMIT %%s;" % format_str,
            params=tuple(permitted_realms) + (int(limit),),
            result_expected=True,
            use_dictionary=use_dictionary,
        )

    def get_app_stragglers(self, app, hardware, helper_string=None):
        """
        Get modems from the ACS that are not running the expected application version.
        :param app: application name used to find the correct SQL query pattern
        :param hardware: a list of acceptable hardware versions for that application
        :param helper_string: an SQL fragment used in the SQL query parameters
                                in most cases, will be a list containing a single string
                                in some cases, will be a list of strings containing version numbers
                                    ex. statpush on spock runs several different versions
        :return: a list of dictionaries containing mac addresses
        """
        straggler_modems_from_db = []

        # Error check the max limit sent by Jenkins. Default to 100 if the check fails
        max_modem_limit = common_utils.get_expected_env_var("max_num_modems")
        if max_modem_limit and not common_utils.is_valid_number(max_modem_limit):
            print(f' \nERROR: non-integer limit "{max_modem_limit}" provided')
            max_modem_limit = 100

        # Format helpers are used to insert the desired number of %s entries
        # which will then be replaced by the "params" that are sent to
        # execute_query for safe sql queries
        format_hw_str = ", ".join(["%s"] * len(hardware))
        format_app_str = "".join("%s")
        format_helper_str = ""
        if helper_string:
            if len(helper_string) == 1:
                format_helper_str = "".join("%s")
            elif len(helper_string) > 1:
                format_helper_str = ", ".join(["%s"] * len(helper_string))

        # Build the SQL query based on the application selected in Jenkins
        try:
            if app in ["modoc", "esp", "vstats", "statpush"]:
                # Looks for applicable modems that do not have the app entirely
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid NOT IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} {MODEM_STRAGGLER_APPS}"
                    " value3 = %s)"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_app_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + (str(app),) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
                # Then looks for applicable modems that have the app but an out of date version
                if helper_string:
                    sql_string = (
                        f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                        " AND cid NOT IN"
                        f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} {MODEM_STRAGGLER_APPS}"
                        " value6 IN (%s))"
                        " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                    )
                    straggler_modems_from_db += self.database.execute_query(
                        sql_string,
                        params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                        result_expected=True,
                        verbose=False,
                    )
            elif app in ["statpush_by_hw"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid NOT IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} {MODEM_STRAGGLER_APPS}"
                    " value5 IN (%s))"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["bb_url", "blueout"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid NOT IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " valueProps LIKE %s)"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )

            elif app in ["fl_unlock"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid NOT IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " servicetype = 'satelliteinterface' AND value3 IN (21600))"
                    " ORDER BY RAND () LIMIT 0, %%s" % format_hw_str
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["modoc_rules"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " servicetype = 'App' and value10 LIKE %s)"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["fw_dwld"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " servicetype = 'Modem' AND value24 IS NULL)"
                    " ORDER BY RAND () LIMIT 0, %%s" % format_hw_str
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["allowlist"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " valueProps LIKE %s)"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["shield_localhost"]:
                # Note, this is a temporary addition, see TERMSW-32980
                sql_string = (
                    "SELECT cid FROM acs_db.CPEManager_CPEs WHERE state != "
                    "4 AND cid LIKE '00A0BC%%' AND hardwareVersion IN (%s) "
                    f"AND cid IN (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} "
                    "servicetype = 'ModemMetaData' and value10 = 3) "
                    "LIMIT 0, %%s" % format_hw_str
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False
                )
            elif app in ["vstat_42x_fix"]:
                # Note, this is a temporary addition, see TERMSW-33245
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND softwareVersion LIKE %s AND cid IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " servicetype = 'App' AND value3 = 'vstats' AND"
                    " value10 != 'CurrentStatus=Running with 2.1.4')"
                    " ORDER BY RAND () LIMIT 0, %%s" % (format_hw_str, format_helper_str)
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + tuple(helper_string) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
            elif app in ["vwa"]:
                sql_string = (
                    f"SELECT {MODEM_STRAGGLER_COLUMNS_DB_MODEMS}(%s)"
                    " AND cid IN"
                    f" (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB}"
                    " servicetype = 'VWA' and right(value4,11) != value6)"
                    " ORDER BY RAND () LIMIT 0, %%s" % format_hw_str
                )
                straggler_modems_from_db += self.database.execute_query(
                    sql_string,
                    params=tuple(hardware) + (int(max_modem_limit),),
                    result_expected=True,
                    verbose=False,
                )
                
            return straggler_modems_from_db
        except Exception as error_msg:
            return error_msg

    def get_all_brazil_modems(self, use_dictionary=True):
        """
        A function to get a list of mac addresses from the ACS
        database based on realm, excluding mobile terminals.

        :return: a list of dictionaries containing software version and mac addresses
        """
        format_str = ", ".join(["%s"] * len(ALL_BRAZIL_REALMS))
        format_hw_str = ", ".join(["%s"] * len(BRAZIL_RES_HW_TYPES))
        all_brazil_modems = self.database.execute_query(
            f"SELECT softwareVersion,cid FROM acs_db.CPEManager_CPEs "
            f"WHERE {MODEM_EXCLUSIONS_ON_OR_OFFLINE} AND hardwareVersion IN "
            f"(%s) AND cid IN (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} "
            f"servicetype = 'Modem' AND value2 IN (%s))"
            % (format_hw_str, format_str),
            params=tuple(BRAZIL_RES_HW_TYPES) + tuple(ALL_BRAZIL_REALMS),
            result_expected=True,
            use_dictionary=use_dictionary,
            verbose=False,
        )
        return all_brazil_modems

    def get_online_brazil_modems(self, use_dictionary=True):
        """
        A function to get a list of online mac addresses from the ACS
        database based on realm, excluding offline and mobile terminals.

        :return: a list of dictionaries containing software version and mac addresses
        """
        # Error check the max limit sent by Jenkins. Default to 100 if the check fails
        max_modem_limit = common_utils.get_expected_env_var("max_num_modems")
        if max_modem_limit and not common_utils.is_valid_number(max_modem_limit):
            print(f' \nERROR: non-integer limit "{max_modem_limit}" provided')
            max_modem_limit = 100

        format_str = ", ".join(["%s"] * len(ALL_BRAZIL_REALMS))
        format_hw_str = ", ".join(["%s"] * len(BRAZIL_RES_HW_TYPES))
        online_brazil_modems = self.database.execute_query(
           f"SELECT softwareVersion,{MODEM_STRAGGLER_COLUMNS_DB_MODEMS}"
           f"(%s) AND cid IN (SELECT {MODEM_STRAGGLER_DIFF_INNER_DB} "
           f"servicetype = 'Modem' AND value2 IN (%s)) ORDER BY RAND () LIMIT 0, %%s"
           % (format_hw_str, format_str),
           params=tuple(BRAZIL_RES_HW_TYPES) + tuple(ALL_BRAZIL_REALMS) + (int(max_modem_limit),),
           result_expected=True,
           use_dictionary=use_dictionary,
           verbose=False,
        )
        return online_brazil_modems


def get_permitted_realms():
    """
    Generate the list of realms that should be permitted.
    :return: a list of strings representing realms
    """
    permitted_realms = PERMITTED_REALMS_DEFAULT
    if "realms_for_acs_db_query" in os.environ:
        user_provided_realms = [
            realm.strip()
            for realm in os.environ["realms_for_acs_db_query"].strip().split("\n")
            if realm
        ]
        permitted_realms = [
            realm for realm in user_provided_realms if realm in PERMITTED_REALMS_DEFAULT
        ]
    return permitted_realms
