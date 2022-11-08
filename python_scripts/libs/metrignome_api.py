"""
Contains generic functionality for making metrignome API calls.
"""

import os
import json
from datetime import timedelta, datetime
import requests
from libs import common_utils, vault_utils

JWT_DIR_PATH = os.path.expanduser("~/etc")
JWT_FILE_PATH = os.path.expanduser("~/etc/metrignomejwt")

ENV_TO_API_URL = {
    "dev": "https://api.dev.metrignome.viasat.io",
    "preprod": "https://api.preprod.metrignome.viasat.io",
    "prod": "https://api.prod.metrignome.viasat.io",
}


def get_metrignome_url(env=None):
    """
    Get the metrignome url based on the "environment" parameter to the Jenkins job.

    :param env: the string "dev", "preprod", or "prod"
    :return: A string representing the metrignome API base URL.

    """
    return ENV_TO_API_URL[env or common_utils.get_environment()]


def get_new_metrignome_token(env=None):
    """
    Request a new metrignome token for the specified vno.

    :param env: the string "dev", "preprod", or "prod"
    :return: a string representing a JWT token to use as credentials for the metrignome API.
    """
    env = env or common_utils.get_environment()

    # Request the JWT token.
    response = requests.get(
        f"https://jwt.us-or.viasat.io/v1/token?stripe=metrignome&name={env}-api",
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


def get_metrignome_token(env=None):
    """
    Checks if the current token is valid and gets a new one if it's missing or invalid.
    :param env: the string "dev", "preprod", or "prod"

    :return: a string representing a JWT token to use as credentials for the metrignome API
    """

    env = env or common_utils.get_environment()
    # Check whether we already have the JWT token saved in a file. If we don't, obtain a new one.
    try:
        with open(os.path.expanduser(JWT_FILE_PATH), "r") as jwt_file:
            jwt = jwt_file.read()
    except IOError:
        jwt = get_new_metrignome_token(env)

    # Check whether the JWT token we have is valid. If it's not, obtain a new one.
    # Try a resouce with minimal overhead
    try:
        from_ts = int((datetime.today() - timedelta(days=2)).timestamp())
        to_ts = int(datetime.today().timestamp())
        params = {"from": f"{from_ts}", "to": f"{to_ts}"}
        response = requests.get(
            get_metrignome_url() + "/v1/metrics/cpuUsage/data",
            headers={"Authorization": f"Bearer {jwt}"},
            verify=False,
            timeout=60,
            params=params,
        )
        if response.status_code != 200:
            print("http request to try jwt token failed (maybe token expired.)")
            common_utils.print_http_response(response)
            raise ValueError
    except ValueError:
        jwt = get_new_metrignome_token(env)

    # Ensure that the JWT file directory and file have the correct permissions.
    try:
        if oct(os.stat(JWT_DIR_PATH).st_mode) != "0o40700":
            os.chmod(JWT_DIR_PATH, 0o700)
        if oct(os.stat(JWT_FILE_PATH).st_mode) != "0o100700":
            os.chmod(os.path.expanduser(JWT_FILE_PATH), 0o700)
    except Exception as ex:
        print(f"JWT file permissions not set. Exception: {ex}")

    return jwt


def get_terminalOfflineEventReason(from_ts, to_ts, vno=None, env=None):
    """
    :param from_ts: timestamp of the collection start time
    :param to_ts: timestamp of the collection start time
    :param env: the string "dev", "preprod", or "prod"
    :return: A dict in the form of
         {'11a0bc72e410': [{'t': 1628007544000, 'v': 26.0},
                           {'t': 1628007552000, 'v': 26.0}
                          ]
         '11a0bc87dea8':  [{'t': 1627932228000, 'v': 21.0}
                          ]
         '00a0bca6d770':  [{'t': 1627954844000, 'v': 21.0}
                           {'t': 1628038199000, 'v': 26.0}
                          ]
         }
    """
    env = env or common_utils.get_environment()
    vno = vno or "exederes"

    from_ts = str(int(from_ts * 1000))
    to_ts = str(int(to_ts * 1000))
    out_dict = {}
    url = f"{get_metrignome_url(env)}/v1/metrics/terminalOfflineEventReason/data"
    headers = {
        "Authorization": f"Bearer {get_metrignome_token(env)}",
        "Accept-Encoding": "gzip,deflate",
        "Accept": "application/json",
        "Content-type": "application/json",
    }
    params = {"from": f"{from_ts}", "to": f"{to_ts}", "vno": f"{vno}", "groupBy": "ntdMacAddress"}
    response = requests.get(url, headers=headers, verify=False, timeout=60, params=params)
    if response.status_code == 200:
        json_content = json.loads(response.content)
        """
        print(f'json_content:{json_content}')
        json_content:{
            'filters': {'vno': 'exederes'},
            'from':    1629221455614,
            'groupBy': ['ntdMacAddress'],
            'to':      1629394255614,
            'name':    'terminalOfflineEventReason',
            'data': [
                {
                    'groupFilters': [{'name': 'ntdMacAddress', 'value': 'ffffffaffffff}],
                    'data': [{'t': 1629224994000, 'v': 3.0}]
                },
                {
                    'groupFilters': [{'name': 'ntdMacAddress', 'value': 'fffffffffffe'}],
                    'data': [{'t': 1629226737000, 'v': 46.0}, {'t': 1629229246000, 'v': 26.0}]
                }
            ]
        }
        """
        if json_content is not None and len(json_content["data"]) > 0:
            data_list = json_content["data"]
            for _, entry in enumerate(data_list):
                group_filters_list = entry["groupFilters"]
                for _, group_filter in enumerate(group_filters_list):
                    if group_filter["name"] == "ntdMacAddress":
                        msid = group_filter["value"]
                out_dict[msid] = entry["data"]
    else:
        common_utils.print_http_response(response)

    return out_dict
