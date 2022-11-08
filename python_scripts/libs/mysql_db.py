"""
Contains functionality for querying a MySQL database.
"""

import mysql.connector as mysql
from tabulate import tabulate


class MySqlDb:
    """
    The MySQL database class
    """

    def __init__(self, usr, pwd, hostname, database):
        """
        Initialize the MySQL class by pulling the credentials
        from Vault and connecting to the MySQL database.
        """
        self.usr = usr
        self.pwd = pwd
        self.hostname = hostname
        self.database = database
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """
        Connect to the database.
        """
        try:
            self.conn = mysql.connect(
                host=self.hostname,
                user=self.usr,
                passwd=self.pwd,
                database=self.database,
                connect_timeout=300,
                autocommit=True,
            )
            self.cursor = self.conn.cursor()
            print(f" \nconnected to {self.hostname}")
        except Exception as ex:
            print(f" \nERROR: can't connect to {self.hostname} with username {self.usr}\n\t{ex}")
            self.disconnect()

    def disconnect(self):
        """
        Disconnect from the database if connected.
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def is_connected(self):
        """
        Determine whether we're connected to the database.

        :return: True if connected, False otherwise
        """
        return self.conn and self.cursor

    def execute_query(self, query, result_expected, params=None, use_dictionary=True, verbose=True):
        """
        Execute a query on the database.

        NOTE: We only have read-only access.

        :param query: a string representing the SQL query to be executed
        :param result_expected: True if we expect the query to return a result, False otherwise
        :param params: a dictionary containing the query's parameters, if it has any
        :param use_dictionary: True to return the results as a list of dictionaries
                               mapping column names to values, False to return the
                               results as a list of tuples containing values
        :param verbose: True to print the query and its result, False otherwise
        :return: a list of strings representing the rows in the output of the query or the
                 empty list if there was no output or if the query couldn't be executed
        """

        # Connect to the database if we weren't already
        if not self.is_connected():
            self.connect()
            if not self.is_connected():
                return []

        try:
            # Ensure that the results will be stored the intended format.
            self.cursor = self.conn.cursor(dictionary=use_dictionary)

            # Execute the query.
            if verbose:
                print(f" \nrunning query:\n{query}")
            self.cursor.execute(query, params=params)
            if verbose:
                print(f" \nran query:\n{self.cursor.statement}")

            # Return the results.
            result = self.cursor.fetchall() if result_expected else []
            if result and verbose:
                self.print_as_table(result)
            return result

        # Log any errors.
        except mysql.errors.ProgrammingError as ex:
            print(f" \nfailed to execute\n{self.cursor.statement}\n{ex}")
            return []

    def print_as_table(self, result, tablefmt="psql"):
        """
        Print the results of a database query in a table format.

        :param result: a list of tuples or a list of dictionaries
                       representing rows in the result of a database query.
        :param tablefmt: (optional) a string representing the table style to use
                         (see https://pypi.org/project/tabulate/ for the list of options)
        """
        if result:
            if type(result[0]) is dict:  # pylint: disable=unidiomatic-typecheck
                print(" \n" + tabulate(result, headers="keys", tablefmt=tablefmt))
            else:
                print(" \n" + tabulate(result, headers=self.cursor.column_names, tablefmt=tablefmt))

    def column_names(self):
        """
        Get the names of the columns in the most recent query.

        :return: a list of strings representing column names for the results of a database query
        """
        if self.cursor:
            return list(self.cursor.column_names)
        return []

    def row_count(self):
        """
        Get the number of rows that were returned by the last query.

        :return: a number representing how many rows were returned by the
                 last SQL query, or -1 if there was no recent query
        """
        if self.cursor:
            return self.cursor.rowcount
        return -1
