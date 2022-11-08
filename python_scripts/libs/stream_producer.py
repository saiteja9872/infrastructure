"""
Contains functionality for writing to a databus stream.

Based on the directions here:
https://wiki.viasat.com/display/DABUS/Getting+Started#GettingStarted-2.CreateYourFirstStream
and the example here:
https://git.viasat.com/databus/idb-examples/blob/master/pidb-example/src/secure-producer.py
"""

import os
from time import sleep
import pexpect
import requests
import idb
from libs import common_utils

# Maps the environment to the URL for the databus stream server
_ENV_TO_STREAM_SERVER_URL = {
    "dev": "https://databus.dev.idb.viasat.io:443",
    "preprod": "https://databus.preprod.idb.viasat.io:443",
    "prod": "https://databus.idb.viasat.io:443",
}

# Maps the environment to the URL for the scrat, the databus GUI
_ENV_TO_SCRAT_SERVER_URL = {
    "dev": "https://scrat.dev.idb.viasat.io",
    "preprod": "https://scrat.preprod.idb.viasat.io",
    "prod": "https://scrat.idb.viasat.io",
}


class StreamProducer:
    """
    The databus stream producer class.

    Usage:

        from libs.stream_producer import StreamProducer

        # The stream name can be found in scrat. The username and password should be for
        # a viasat.io service account that has write permissions to the stream with that name.
        stream_producer = StreamProducer("<username>", "<password>", "<stream name>")
        stream_producer.publish_messages([{"payload": "hello world"}])
        stream_producer.disconnect()
    """

    def __init__(self, usr, pwd, stream_name, env=None):
        """
        Connect to the databus.

        :param usr: a string representing a viasat.io username
        :param pwd: a string representing a viasat.io password
        :param stream_name: a string representing a databus stream name
        :param env: "prod", "preprod", or "dev"
        """
        self.usr = usr
        self.pwd = pwd
        self.stream_name = stream_name
        self.env = env or common_utils.get_environment()
        self.principal_name = f"{usr}@VIASAT.IO"
        self.key_table_file_path = "/tmp/keytab"
        self.bus = None
        self.stream = None
        self.stream_id = None
        self.producer = None
        self._connect()

    def _connect(self):
        """
        Create a keytab file, download the latest kerberos config, use
        these to connect to the databus, then bind to a specific stream
        on the databus and get set up to produce on that stream.
        """
        self._create_key_table_file()
        self._download_kerberos_config()
        self._connect_to_databus()
        self._bind_to_stream()
        self._create_producer()

    def disconnect(self):
        """
        Disconnect from the databus.
        """
        print(" \ndisconnecting from the databus")
        if self.stream:
            if self.producer:
                self.producer.close()
                self.producer = None
            self.stream.close()
            self.stream = None
        self.bus = None

    def is_connected(self):
        """
        Check whether we're connected to a data stream as a producer.

        :return: True if connected, False if not connected
        """
        return self.stream and self.producer

    def publish_messages(self, messages):
        """
        Publish messages to the databus stream.

        :param messages: a list of dictionaries representing the messages to be published
        """
        if self.is_connected():

            print(f" \nsending messages to the {self.stream_name} stream")
            for message in messages:
                if not self._publish_message(message):
                    # If a message fails to send then something is probably
                    # wrong, so we return rather than trying to send the rest.
                    return

            sleep_length = 10
            print(f" \nsleeping for {sleep_length} seconds in case the messages need time to send")
            sleep(sleep_length)
            print(f" \nqueue length: {self.producer.get_queue_length()}")
            print(" \nflushing the queue")
            self.producer.flush()
            print(
                f" \nthe latest message sent to the {self.stream_name}"
                f" stream should be visible at {self.get_scrat_url()}"
            )

        else:
            print(" \nERROR: could not publish messages because we're not connected to the databus")

    def _publish_message(self, message):
        """
        Publish a message to the databus stream.

        :param message: a dictionary representing the message to be published
        :return: True on success, False on failure
        """
        if self.producer:
            try:
                self.producer.send(message)
                return True
            except idb.error.InvalidRequest as ex:
                print(
                    f' \nERROR: failed to publish message\n"{message}"\n{ex}\n'
                    f"stream schema: {self.stream.definition['links'][2]['href']}"
                )
        else:
            print(
                " \nERROR: could not publish message because"
                " we're not connected to a databus stream"
            )
        return False

    def get_scrat_url(self):
        """
        Get the scrat URL at which we'll be able to view the latest
        message sent to this stream to test that it's working.

        :return: a string representing a URL
        """
        if self.stream_id:
            return f"{_ENV_TO_SCRAT_SERVER_URL[self.env]}/#/streams/{self.stream_id}/sample"
        return "<ERROR: we've never connected to a stream>"

    def _create_key_table_file(self):
        """
        Create a key table file using ktutil and save it in /etc/.

        This file will be used to authenticate with the Kerberos cluster that the databus uses.
        """
        print(" \ngenerating key table file")
        try:
            default_prompt = "ktutil:  "
            child = pexpect.spawn("ktutil")
            child.expect(default_prompt)
            try:
                os.remove(self.key_table_file_path)
            except OSError:
                pass
            child.sendline(
                f"add_entry -password -p {self.principal_name} -k 1 -e aes256-cts-hmac-sha1-96"
            )
            child.expect("Password for " + self.principal_name)
            child.sendline(self.pwd)
            child.expect(default_prompt)
            child.sendline("wkt " + self.key_table_file_path)
            child.expect(default_prompt)
            child.sendline("quit")
            child.close()
        except Exception as ex:
            print(f" \nERROR: failed to create keytab file\n\t{ex}")

    def _download_kerberos_config(self):
        """
        Download the kerberos config. This will be used to
        reach the kerberos cluster that the databus uses.
        """

        # Download the kerberos config
        print(" \ndownloading kerberos config")
        response = requests.get(
            "https://api.us-or.viasat.io/api/v1/kerberos/krb5.conf",
            verify=False,
            auth=(self.usr, self.pwd),
        )
        if response.status_code != 200:
            print("ERROR: failed to download kerberos config")
            common_utils.print_http_response(response)
            return

        # Save the kerberos config in a file
        kerberos_conf_path = "/etc/krb5.conf"
        try:
            with open(kerberos_conf_path, "w") as kerberos_conf_file:
                kerberos_conf_file.write(response.text)
        except IOError as ex:
            print(f" \nERROR: failed to write kerberos config to {kerberos_conf_path}\n\t{ex}")

    def _connect_to_databus(self):
        """
        Connect to the databus.
        """
        try:
            print(" \nconnecting to the databus")
            self.bus = idb.Bus(
                endpoint=self._get_stream_server_url(),
                username=self.usr,
                password=self.pwd,
                principal_name=self.principal_name,
                keytabfile=self.key_table_file_path,
            )
        except idb.error.IDBError as ex:
            print(
                f" \nERROR: can't connect to {self.bus.endpoint}"
                f" with username {self.usr}\n\t{ex}"
            )
            self.disconnect()

    def _bind_to_stream(self):
        """
        Bind to a specific stream on the databus.

        Should already have called _connect_to_databus() prior to calling this method.
        """
        if self.bus:
            try:
                print(f" \nbinding to the {self.stream_name} stream")
                self.stream = self.bus.bind(self.stream_name)
                self.stream_id = self.stream.id
            except idb.error.IDBError as ex:
                print(
                    f" \nERROR: could not bind to {self.stream_name}"
                    f" stream at {self.bus.endpoint}\n\t{ex}"
                )
                self.disconnect()
        else:
            print(
                " \nERROR: could not connect to a stream"
                " because we're not connected to the databus"
            )

    def _create_producer(self):
        """
        Create a producer object in order to start
        producing on the stream to which we're connected.

        This function should be called after _connect_to_databus()
        and _bind_to_stream() have been respectively called.
        """
        if self.stream:
            try:
                print(f" \ncreating a producer on the {self.stream_name} stream")
                self.producer = self.stream.producer()
            except idb.error.IDBError as ex:
                print(f" \nERROR: failed to create producer on {self.stream_name} stream:\n\t{ex}")
                self.disconnect()
        else:
            print(" \nERROR: could not create producer because we're not connected to a stream")

    def _get_stream_server_url(self):
        """
        Get the stream server URL associated with the desired environment.

        :param env: a string representing an environment ("prod", "preprod", or "dev")
        :return: a string representing a stream server URL
        """
        return _ENV_TO_STREAM_SERVER_URL[self.env or common_utils.get_environment()]

    def _print_stream_list(self):
        """
        Print the streams visible to the service account with which we've authenticated.

        NOTE: Included here for debugging purposes only.
        """
        if self.bus:
            streams = self.bus.list_streams()
            print(f" \nlisting all {len(streams)} streams at {self.bus.endpoint}:")
            for stream in streams:
                print(
                    f"{stream.identity.name}     "
                    f"({stream.identity.id} {stream.identity.tags or ''})"
                )
        else:
            print(
                " \nERROR: could not list databus streams"
                " because we're not connected to the databus"
            )
