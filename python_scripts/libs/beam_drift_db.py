"""
Contains functionality for querying the beam drift database. We use this
database to keep track of information across runs of the beam drift job.
"""

from netaddr import valid_mac
from libs.mysql_db import MySqlDb
from libs import common_utils, vault_utils


class BeamDriftDb:
    """
    The beam drift database class
    """

    def __init__(self):
        """
        Initialize the BeamDriftDb class by pulling the credentials
        from Vault and connecting to the MySQL database.
        """
        usr = common_utils.BEAM_DRIFT_DB_SERVICE_ACCT_USER
        pwd = vault_utils.get_beam_drift_db_service_account_password()
        hostname = "beam-drift-db.cacxgne3yan9.us-east-1.rds.amazonaws.com"
        db_name = "drifted_modems"
        self.database = MySqlDb(usr, pwd, hostname, db_name)

    def connect(self):
        """
        Connect to the ACS database.
        """
        print(" \nattempting to connect to the beam drift database")
        self.database.connect()

    def update_goal(self, mac, goal_sat, goal_beam, goal_pol, verbose=False):
        """
        Update a modem's goal beam in the local database.

        :param mac: a string representing a modem's MAC address
        :param goal_sat: a number representing the modem's goal satellite ID
        :param goal_beam: a number representing the modem's goal beam ID
        :param goal_pol: a string representing the modem's goal beam polarization
                         ("LHCP", "RHCP", "LHCP_CO", "RHCP_CO")
        :param verbose: True to print the query and its result, False otherwise
        """
        if not (
            valid_mac(mac)
            and common_utils.is_valid_number(goal_sat)
            and common_utils.is_valid_number(goal_beam)
            and common_utils.is_valid_beam_pol(goal_pol)
        ):
            print(
                f' \nERROR: invalid MAC address "{mac}", goal sat "{goal_sat}",'
                f' goal beam "{goal_beam}", or goal pol "{goal_pol}"'
            )
            return

        self.database.execute_query(
            "INSERT INTO goals(mac, goal_sat, goal_beam, goal_pol)"
            " VALUES (%(mac)s, %(goal_sat)s, %(goal_beam)s, %(goal_pol)s)"
            " ON DUPLICATE KEY UPDATE"
            " goal_sat=%(goal_sat)s, goal_beam=%(goal_beam)s, goal_pol=%(goal_pol)s;",
            params={"mac": mac, "goal_sat": goal_sat, "goal_beam": goal_beam, "goal_pol": goal_pol},
            result_expected=False,
            verbose=verbose,
        )

    def look_up_goal(self, mac, use_dictionary=True, verbose=True):
        """
        Look up the goal beam for a modem in our local database.

        :param mac: a string representing a MAC addresses for a
                    modem whose goal beam info we want to look up
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param verbose: True to print the query and its result, False otherwise
        :return: a dictionary representing the goal beam of this modem; looks like:
                 {"mac": "AABBCCDDEEFF", "goal_sat": 999, goal_beam: "999", goal_pol: "LHCP"}
        """
        if not valid_mac(mac):
            print(f' \nERROR: invalid MAC address "{mac}"')
            return {}

        result = self.database.execute_query(
            "SELECT goal_sat, goal_beam, goal_pol FROM goals WHERE mac = %(mac)s;",
            params={"mac": mac},
            result_expected=True,
            use_dictionary=use_dictionary,
            verbose=verbose,
        )
        return result[0] if result else {}

    def look_up_goal_without_pol(self, mac, use_dictionary=True, verbose=True):
        """
        Look up the goal beam for a modem in the old version of our database.

        DEPRECATED!!!! Use look_up_goal().

        :param mac: a string representing a MAC addresses for a
                    modem whose goal beam info we want to look up
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param verbose: True to print the query and its result, False otherwise
        :return: a dictionary representing the goal beam of this modem; looks like:
                 {"mac": "AABBCCDDEEFF", "goal_sat": 999, goal_beam: "999", goal_pol: "LHCP"}
        """
        if not valid_mac(mac):
            print(f' \nERROR: invalid MAC address "{mac}"')
            return {}

        result = self.database.execute_query(
            "SELECT goal_sat, goal_beam FROM goals_without_poles WHERE mac = %(mac)s;",
            params={"mac": mac},
            result_expected=True,
            use_dictionary=use_dictionary,
            verbose=verbose,
        )
        return result[0] if result else {}

    def flag_unhelpable_modem(self, mac, sat, cross_pol, verbose=False):
        """
        Flag a modem as having a possible issue switching polarizations.

        :param mac: a string representing a modem's MAC address
        :param sat: a number representing the modem's satellite ID
        :param cross_pol: a boolean representing whether the modem was attempting
                          to move to a beam of an opposite polarization
        :param verbose: True to print the query and its result, False otherwise
        """
        if not valid_mac(mac):
            print(f' \nERROR: invalid MAC address "{mac}"')
            return
        if not common_utils.is_valid_number(sat):
            print(f" \nERROR: invalid satellite ID {sat}")
            return
        if not common_utils.is_valid_bool(cross_pol):
            print(f" \nERROR: invalid boolean {cross_pol}")
            return

        self.database.execute_query(
            "INSERT INTO will_not_move (mac, sat, cross_pol)"
            " SELECT %(mac)s, %(sat)s, %(cross_pol)s"
            " where not exists (select mac from will_not_move where mac = %(mac)s);",
            params={"mac": mac, "sat": sat, "cross_pol": cross_pol},
            result_expected=False,
            verbose=verbose,
        )

    def get_broken_pol_switch_candidates(self, added_since=None, verbose=False):
        """
        Retrieve the list of modems that have been flagged
        as having a possible issue switching polarizations.

        :param added_since: a string representing a GMT timestamp in the form of
               "2021-03-01 23:34" that represents the oldest entry age in the list
               we want to pull
        :param verbose: True to print the query and its result, False otherwise
        """
        if added_since and not common_utils.is_valid_sql_timestamp(added_since):
            print(
                f' \nERROR: invalid SQL timestamp "{added_since}".'
                f' Should be in the form "2021-03-01 23:34"'
            )
            added_since = None

        if added_since:
            self.database.execute_query(
                "SELECT * FROM failed_move_to_opp_pol"
                " WHERE added BETWEEN %(added_since)s and NOW();",
                params={"added_since": added_since},
                result_expected=True,
                verbose=verbose,
            )
        else:
            self.database.execute_query(
                "SELECT * FROM failed_move_to_opp_pol;",
                result_expected=True,
                verbose=verbose,
            )

    def record_fix_counts(self, fixed_by_cwmp_restart, fixed_by_lkg_update, verbose=False):
        """
        Record how many modems were fixed by this run of the job.

        :param fixed_by_cwmp_restart: a number representing how many modems this run
                                      of the job was able to move to their correct beam
                                      via a CWMP restart
        :param fixed_by_lkg_update: a number representing how many modems this run of the job
                                    was able to move to their correct beam via an LKG update
        :param verbose: True to print the query and its result, False otherwise
        """

        # Validate inputs.
        if not common_utils.is_valid_number(
            fixed_by_cwmp_restart
        ) or not common_utils.is_valid_number(fixed_by_lkg_update):
            print(
                f' \nERROR: fixed_by_cwmp_restart "{fixed_by_cwmp_restart}" and'
                f' fixed_by_lkg_update "{fixed_by_lkg_update}" should both be numbers'
            )
            return

        # Update the database.
        self.database.execute_query(
            "INSERT INTO fixed_count(fixed_by_cwmp_restart, fixed_by_lkg_update)"
            " VALUES (%(fixed_by_cwmp_restart)s, %(fixed_by_lkg_update)s);",
            params={
                "fixed_by_cwmp_restart": fixed_by_cwmp_restart,
                "fixed_by_lkg_update": fixed_by_lkg_update,
            },
            result_expected=False,
            verbose=verbose,
        )

    def get_fix_count_record(self, fixed_since=None, verbose=False):
        """
        Get a record of how many modems each run of the
        job has successfully moved to their correct beams.

        :param fixed_since: a string representing a GMT timestamp in the form of
               "2021-03-01 23:34" that represents the oldest entry age in the table
               we want to pull
        :param verbose: True to print the query and its result, False otherwise
        """

        # Validate inputs.
        if fixed_since and not common_utils.is_valid_sql_timestamp(fixed_since):
            print(
                f' \nERROR: invalid SQL timestamp "{fixed_since}".'
                f' Should be in the form "2021-03-01 23:34"'
            )
            fixed_since = None

        # Query the database.
        if fixed_since:
            self.database.execute_query(
                "SELECT * FROM fixed_count"
                " WHERE job_finished BETWEEN %(fixed_since)s and NOW();",
                params={"fixed_since": fixed_since},
                result_expected=True,
                verbose=verbose,
            )
        else:
            self.database.execute_query(
                "SELECT * FROM fixed_count;",
                result_expected=True,
                verbose=verbose,
            )

    def get_single_mac_details(self, mac):
        """
        Get a record of the last time a particular mac was
            found in the beam drift database and any other
            records of interest

        :param mac: modem mac address
        :return: a list of timestamps or nulls depending on sql query
        """

        # Error check mac address
        if not valid_mac(mac):
            # Sending an empty list which triggers an error in get_mac_recent_drift_info.py
            return []

        result_goals = self.database.execute_query(
            "SELECT updated_at FROM goals WHERE mac = %(mac)s;",
            params={"mac": mac},
            result_expected=True,
            verbose=False,
        )

        result_move = self.database.execute_query(
            "SELECT added FROM will_not_move WHERE mac = %(mac)s;",
            params={"mac": mac},
            result_expected=True,
            verbose=False,
        )

        return result_goals, result_move

    def get_brazil_records(self, table):
        """
        A function to retrieve a list of modems in the brazil odu table.

        :param table: name of a table to retrieve contents
        :return: a list of dictionaries containing mac addresses
        """
        format_table = (table,)
        return self.database.execute_query(
            "SELECT mac FROM %s;" % format_table,
            result_expected=True,
            verbose=False,
        )

    def add_brazil_records(self, mac, table):
        """
        A function to add a mac address to the brazil odu table.

        :param mac: a string representing a mac address
        :param table: name of table to add to
        """
        self.database.execute_query(
            "INSERT IGNORE INTO %s (mac) VALUES ('%s')" % (table, mac),
            result_expected=False,
            verbose=False,
        )

    def delete_brazil_records(self, table):
        """
        A function to delete all records from the brazil odu table.

        :param table: name of table to clear
        """
        format_table = (table,)
        self.database.execute_query(
            "TRUNCATE TABLE %s" % format_table,
            result_expected=False,
            verbose=False,
        )
