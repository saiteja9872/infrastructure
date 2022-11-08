"""
Contains generic functionality for making SDP API calls from Jenkins.
"""

import os
import time
import datetime
from io import StringIO
import xml.etree.ElementTree as etree
import requests
import pandas
from libs import common_utils, vault_utils

NS = {"default": "http://sdp.viasat.com/sdp/schema/SDP"}

JWT_DIR_PATH = os.path.expanduser("~/etc")
JWT_FILE_PATH = os.path.expanduser("~/etc/sdpjwt")
ENV_TO_SDP_API_URL = {
    "dev": "https://dev.sdpapi.viasat.io",
    "preprod": "https://preprod-internal.sdpapi.viasat.io",
    "prod": "https://prod-internal.sdpapi.viasat.io",
}


def get_sdp_api_url(env=None):
    """
    Get the sdp_api_base_url based on the "environment" parameter to the Jenkins job.

    :param env: the string "dev", "preprod", or "prod"
    :return: A string representing the SDP API base URL.

    """
    return ENV_TO_SDP_API_URL[env or common_utils.get_environment()]


def get_sdp_token(vno, env=None):
    """
    Checks if the current token is valid and gets a new one if it's missing or invalid.
    :param env: the string "dev", "preprod", or "prod"
    :param vno: a string representing the VNO for which we need a token

    :return: a string representing a JWT token to use as credentials for the SDP API
    """

    env = env or common_utils.get_environment()
    # Check whether we already have the JWT token saved in a file. If we don't, obtain a new one.
    try:
        with open(os.path.expanduser(JWT_FILE_PATH), "r") as jwt_file:
            jwt = jwt_file.read()
    except IOError:
        jwt = get_new_sdp_token(vno, env)

    # Check whether the JWT token we have is valid. If it's not, obtain a new one.
    try:
        response = requests.get(
            get_sdp_api_url() + "/whoami",
            headers={"Authorization": jwt},
            verify=False,
            timeout=60,
        )
        if response.status_code != 200:
            raise ValueError
    except ValueError:
        jwt = get_new_sdp_token(vno, env)

    # Ensure that the JWT file directory and file have the correct permissions.
    try:
        if oct(os.stat(JWT_DIR_PATH).st_mode) != "0o40700":
            os.chmod(JWT_DIR_PATH, 0o700)
        if oct(os.stat(JWT_FILE_PATH).st_mode) != "0o100700":
            os.chmod(os.path.expanduser(JWT_FILE_PATH), 0o700)
    except Exception as ex:
        print(f"JWT file permissions not set. Exception: {ex}")

    return jwt


def get_new_sdp_token(vno, env=None):
    """
    Request a new token for the SDP API for the specified vno.

    :param vno: a string representing the VNO for which we need a token
    :param env: the string "dev", "preprod", or "prod"
    :return: a string representing a JWT token to use as credentials for the SDP API.
    """
    if not vno:
        print(f"Unable to get token! get_new_sdp_token for vno: {vno}")
        return None

    env = env or common_utils.get_environment()
    if not env == "prod":
        print(f"Unable to get {env} token! only prod token is supported for now")
        return None

    # Request the JWT token.
    response = requests.get(
        f"https://jwt.us-or.viasat.io/v1/token?stripe=sdpapi-{env}&name={vno}",
        auth=(
            common_utils.SDP_API_SERVICE_ACCT_USR,
            vault_utils.get_prod_sdp_api_service_account_password(),
        ),
        verify=False,
        timeout=60,
    )
    if not response or response.status_code != 200:
        print(f"Unable to get token! Status Code: {response.status_code}")
        return None

    # Store the JWT token in a file so that we don't have to request it every time.
    token = response.text
    local_etc_path = os.path.expanduser(JWT_DIR_PATH)
    if not os.path.exists(local_etc_path):
        os.mkdir(local_etc_path)
        print(f"Required dir ({local_etc_path}) created for storing JWT file.")
    try:
        with open(os.path.expanduser(JWT_FILE_PATH), "w") as jwt_file:
            jwt_file.write(token)
    except IOError as ex:
        print(
            f"Cannot access {JWT_FILE_PATH} directory due to {ex}."
            f" You will have to authenticate each time you run the script."
        )
    return token


def get_PPILv2_report_content_types(vno=None, env=None):
    """
    Get a list of PPILv2 report type for a particular VNO.

    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a list ofPPILv2 report supported contentTypes (currently only text/csv)
    """
    env = env or "prod"
    vno = vno or "exederes"
    response = requests.get(
        f"{get_sdp_api_url(env)}/ReportTypes/PPILv2",
        headers={"Authorization": f"Bearer {get_sdp_token(vno, env)}"},
        verify=False,
        timeout=60,
    )
    content_type_list = []
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        content_types = root.findall("default:contentTypes", NS)
        for content_type in content_types:
            value = content_type.find("default:value", NS).text
            content_type_list.append(value)

        return content_type_list
    return {}


def get_PPILv2_available_reports_info(vno=None, env=None):
    """
    Get a dict of available PPILv2 reports keyed by id for a particular VNO.

    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a dict of PPILv2 report keyed with its ID
    The format is the xml document is:
    </Reports>
      <Report>
        <id>390edb54-d7b8-3116-8170-03e8f47f084c</id>
        <reportType>PPILv2</reportType>
        <generationDate>2021-04-14T06:00:52Z</generationDate>
        <beginDate>2021-04-06T00:00:00Z</beginDate>
        <endDate>2021-04-14T05:00:00Z</endDate>
      </Report>
    </Reports>

    """
    env = env or "prod"
    vno = vno or "exederes"
    response = requests.get(
        f"{get_sdp_api_url(env)}/Reports?filter=+reportType=%22PPILv2%22",
        headers={"Authorization": f"Bearer {get_sdp_token(vno, env)}"},
        verify=False,
        timeout=60,
    )
    reports_dict = {}
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        reports = root.findall("default:Report", NS)
        for report in reports:
            report_id = report.find("default:id", NS).text
            gen_date = report.find("default:generationDate", NS).text
            begin_date = report.find("default:beginDate", NS).text
            end_date = report.find("default:endDate", NS).text
            reports_dict[report_id] = {}
            reports_dict[report_id]["generationDate"] = gen_date
            reports_dict[report_id]["beginDate"] = begin_date
            reports_dict[report_id]["endDate"] = end_date
        # print(reports_dict)
        return reports_dict
    return {}


def get_PPILv2_report_by_id(report_id, vno=None, env=None):
    """
    Get a dict of the PPILv2 report with the specified report_id for a particular VNO.
    :param reportid: a string representing report_id of the report
    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a dict of PPILv2 report keyed with its columns
    """

    env = env or "prod"
    vno = vno or "exederes"
    dict_out = {}
    if report_id is None:
        return dict_out

    reports_dict = get_PPILv2_available_reports_info(vno, env)
    if report_id not in reports_dict.keys():
        return None
    url = f"{get_sdp_api_url(env)}/Reports/{report_id}/data"
    headers = {
        "Authorization": f"Bearer {get_sdp_token(vno, env)}",
        "Accept-Encoding": "gzip,deflate",
        "Accept": "text/csv",
        "Content-type": "text/csv",
    }

    response = requests.get(url, headers=headers, verify=False, timeout=60)
    if response.status_code == 200:
        data = StringIO(response.text)
        try:
            data_frame = pandas.read_csv(data)
            dict_out = data_frame.to_dict()
        except Exception as ex:
            print(f"get_PPILv2_report_by_id exception:{ex}")

    return dict_out


def get_PPILv2_report_by_gen_date(gen_date, vno=None, env=None):
    """
    Get a dict of the PPILv2 report with the specified gen_date for a particular VNO.

    :param gen_date: a string representing gen_date of report in the format of '2021-04-14'
    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a dict of PPILv2 report keyed with its columns
    """
    env = env or "prod"
    vno = vno or "exederes"
    dict_out = {}
    report_id_for_gen_date = None

    report_dict = get_PPILv2_available_reports_info(vno, env)
    if len(report_dict) == 0:
        return dict_out

    for report_id, item in report_dict.items():
        report_gen_date = item["generationDate"]
        # format string is "%Y-%m-%dT%H:%M:%SZ", and we only look at the date,
        # which is -10 position
        if gen_date == report_gen_date[:-10]:
            report_id_for_gen_date = report_id
            break

    if report_id_for_gen_date is not None:
        dict_out = get_PPILv2_report_by_id(report_id_for_gen_date, vno, env)
    return dict_out


def get_timestamp_from_report_time(time_str):
    """
    :param time_str: A time string in the format of ""%Y-%m-%dT%H:%M:%SZ""
    :return: the timestamp
    """

    fmt_str = "%Y-%m-%dT%H:%M:%SZ"
    time_tuple = datetime.datetime.strptime(time_str, fmt_str).timetuple()
    timestamp = time.mktime(time_tuple)
    return timestamp


def get_PPILv2_report_latest_gen_date(vno=None, env=None):
    """
    Get a dict of the PPILv2 report with the latest gen_date for a particular VNO.

    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a dict of PPILv2 report keyed with its columns
        {
        time :          {0: '2021-08-10 23:22:30', 1: '2021-08-10 23:15:00', 2: '2021-08-06 20:00:00'}
        ntdMacAddress : {0: '11a0bcb1b0b0', 1: '11a0bc2f3fe8', 2: '11a0bc419f1e'}
        realm :         {0: 'bra.telbr.viasat.com', 1: 'bra.telbr.viasat.com', 2: 'bra.telbr.viasat.com'}
        satId :         {0: 16, 1: 16, 2: 16}
        serviceAreaId : {0: 'None', 1: 'None', 2: 'None'}
        logicalBeamId : {0: 53, 1: 61, 2: 61}
        bandId :        {0: 'A', 1: 'A', 2: 'A'}
        numberOfAggregates : {0: 49, 1: 102, 2: 67}
        utAvgFlSinrMeasured :{0: -1.3, 1: 0.2, 2: 1.3}
        utAvgFlSinrPredicted : {0: 3.5, 1: 3.5, 2: 3.5}
        utRlChipRateMeasured : {0: 0.625, 1: 0.625, 2: 0.625}
        utRlChipRatePredicted : {0: 2.5, 1: 2.5, 2: 2.5}
        flGigaSymbolsUsed : {0: 182.325, 1: 155.331, 2: 237.618}
        flGigaSymbolsPredicted : {0: 68.372, 1: 93.199, 2: 178.213}
        flGigaSymbolsWasted : {0: 113.953, 1: 62.132, 2: 59.404}
        flPacketLossRate : {0: 0.000247, 1: 0.0002583, 2: 0.01074}
        priority : {0: 3, 1: 3, 2: 3}
        mispointFlag : {0: True, 1: True, 2: True}
        miscFlag : {0: False, 1: False, 2: False}
        packetLossFlag : {0: False, 1: False, 2: True}
        performanceFlag : {0: True, 1: True, 2: True}
        lastPeakPointSuccessTime : {0: 'None', 1: 'None', 2: 'None'}
        }
    """
    env = env or "prod"
    vno = vno or "exederes"
    dict_out = {}

    report_dict = get_PPILv2_available_reports_info(vno, env)
    if len(report_dict) == 0:
        return dict_out

    latest_id = next(iter(report_dict.keys()))
    latest_gen_date = report_dict[latest_id]["generationDate"]
    for report_id, item in report_dict.items():
        gen_date = item["generationDate"]
        if get_timestamp_from_report_time(gen_date) > get_timestamp_from_report_time(
            latest_gen_date
        ):
            latest_id = report_id
            latest_gen_date = gen_date

    dict_out = get_PPILv2_report_by_id(latest_id, vno, env)
    # print(dict_out['time'][0])
    # print(len(dict_out['ntdMacAddress']))
    return dict_out


def get_ut_mac_addrs_from_PPILv2_report_latest_gen_date(vno=None, env=None):
    """
    Get list of ut macAddresses from the PPILv2 report with the latest
    gen_date for a particular VNO.

    :param vno: a string representing a VNO (e.g. "brres",
                "exederes", "mxres", "telbr", "xci", "brcwf")
    :param env: the string "dev", "preprod", or "prod"
    :return:  a list of macAddresses
    """
    mac_address_list = []
    dict_out = get_PPILv2_report_latest_gen_date(vno, env)
    if len(dict_out) > 0:
        mac_address_list = dict_out["ntdMacAddress"].values()
    return mac_address_list
