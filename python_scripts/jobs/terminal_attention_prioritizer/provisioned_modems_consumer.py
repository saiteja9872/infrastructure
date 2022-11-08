"""
Contains functionality for retrieving the list of provisioned modems.

We'll need this to ensure that modems not present in the Antenna Mispoint Report nor in
the outage history time series are still representing in the final output of the job.

The public methods in this file are meant to be called by prioritize_attention_for_terminals.py
"""


def get_provisioned_modems(config):
    """
    Get the list of provisioned modems in the network for each VNO in the config.

    :param config: an instance of the Config class that represents which metrics should be
                   calculated for each VNO and what thresholds each VNO should use to calculate
                   those metrics
    :return: a dictionary in which the keys are strings representing VNOs and the values
             are lists of strings representing all the MAC addresses of modems in those VNOs
    """
    results = {}
    provisioned_modems = _download_list_of_provisioned_modems()
    for vno in config.get_vno_list():
        results[vno] = _parse_downloaded_list_of_provisioned_modems(vno, provisioned_modems)
    return results


def _download_list_of_provisioned_modems():
    """
    Download the list of all the provisioned modems in the network.

    NOTE: we may need to restructure this slightly depending on whether the list
          of modems is available to be downloaded on a per-VNO basis. This file
          structure currently assumes that the whole list is downloaded at once.

    :return: the response returned by our query for the list of provisioned modems
             TODO BBCTERMSW-28552 unsure what format this will be in
    """
    print(" \nTODO BBCTERMSW-28551: get the list of provisioned modems")

    # TODO BBCTERMSW-28551 implement this
    #
    # The list of devices in an active state gets dumped into a zip file in an S3 bucket every
    # night. We can use Amazon Athena to execute SQL queries over the data in the S3 without having
    # to download the entire file. Here’s the documentation on getting access to the bucket &
    # making sure our AWS account is set up to use Athena:
    # https://api.preprod.metrignome.viasat.io/api-docs/ .
    # See Macall for help with accessing the MoDOT AWS VPC.
    #
    # See jobs/delete_expired_s3_bbs.py for an example of how to use the boto3 library to interact
    # with an S3. This may or may not be relevant depending on how Amazon Athena works.

    return ""


def _parse_downloaded_list_of_provisioned_modems(vno, response):
    """
    From the list of downloaded modems, parse out the ones that are in
    the specified VNO.

    NOTE: we may need to restructure this depending on whether the list of
          modems contains VNO information for each modem. we may need to get
          that data from another source.

    :param vno: a string representing a VNO
    :param response: the data returned by download_list_of_provisioned_modems()
                     TODO BBCTERMSW-28552 unsure what format this data will be in
    :return: a list of strings representing the MAC addresses
             of all the provisioned modems in that VNO
    """
    # TODO BBCTERMSW-28552 implement this
    # TODO BBCTERMSW-28552 unit tests in TestProvisionedModemsConsumer
    return {}
