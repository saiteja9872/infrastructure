"""
Contains generic functionality for making CM-T API calls from Jenkins.
"""

import os
import requests
from libs import common_utils, vault_utils

MAX_RESULTS_FROM_CMT = 10000
JWT_DIR_PATH = os.path.expanduser("~/etc")
JWT_FILE_PATH = os.path.expanduser("~/etc/cmtjwt")
ENV_TO_CMT_API_URL = {
    "dev": "https://api01-fat.dev.naw01.cmt.viasat.io",
    "preprod": "https://api.pre.cmt.viasat.io",
    "prod": "https://api.prod.naw01.cmt.viasat.io",
}

ONE_MINUTE = 60  # seconds


def get_cmt_api_url():
    """
    Get the cmt_api_base_url based on the "environment" parameter to the Jenkins job.

    :return: A string representing the CM-T API base URL.

    """
    return ENV_TO_CMT_API_URL[common_utils.get_expected_env_var("environment")]


def get_cmt_token():
    """
    Checks if the current token is valid and gets a new one if it's missing or invalid.

    :return: a string representing a JWT token to use as credentials for the CM-T API
    """

    # Check whether we already have the JWT token saved in a file. If we don't, obtain a new one.
    try:
        with open(os.path.expanduser(JWT_FILE_PATH), "r") as jwt_file:
            jwt = f"Bearer {jwt_file.read()}"
    except IOError:
        jwt = get_new_cmt_token()

    # Check whether the JWT token we have is valid. If it's not, obtain a new one.
    try:
        response = requests.get(
            get_cmt_api_url() + "/whoami", headers={"Authorization": jwt}, verify=False
        )
        if response.status_code != 200:
            raise ValueError
    except ValueError:
        jwt = get_new_cmt_token()

    # Ensure that the JWT file directory and file have the correct permissions.
    try:
        if oct(os.stat(JWT_DIR_PATH).st_mode) != "0o40700":
            os.chmod(JWT_DIR_PATH, 0o700)
        if oct(os.stat(JWT_FILE_PATH).st_mode) != "0o100700":
            os.chmod(os.path.expanduser(JWT_FILE_PATH), 0o700)
    except Exception as ex:
        print(f"JWT file permissions not set. Exception: {ex}")

    return jwt


def get_new_cmt_token():
    """
    Request a new token for the CM-T API.

    :return: a string representing a JWT token to use as credentials for the CM-T API.
    """
    env = os.environ["environment"]
    env = "preprod" if (env == "dev") else env

    # Request the JWT token.
    response = requests.get(
        "https://jwt.us-or.viasat.io/v1/token?stripe=cmt&token_type=user",
        auth=(
            f"ut-devops-{env}_cmt_api_user",
            vault_utils.get_cmt_api_service_account_password(env),
        ),
        verify=False,
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
    return f"Bearer {token}"


def get_modems(
    sat_id=None,
    beam=None,
    vno=None,
    sw_version=None,
    random=True,
    online=True,
    limit=None,
    verbose=True,
    timeout=300,
):
    """
    Get a list of modems from the CM-T API.

    NOTE: The CM-T API won't return more than 10,000 responses!

    :param sat_id: a number representing the satellite ID
    :param beam: a number representing the beam ID
    :param vno: a string representing the VNO
    :param sw_version: a string representing the software version (including prefix)
    :param limit: A number representing the maximum number of modems to return.
                  If None, CM-T's limitation is 10,000 modems.
    :param random: True to return the list of modems in a random order, False otherwise
    :param online: True to only return modems that are online, False otherwise
    :param verbose: True to print information about the request
                    and results to the user, False otherwise
    :param timeout: a number representing the timeout for the CM-T API call
    :return: a list of strings representing the mac addresses of all the modems running
             on the given satellite ID and beam ID combination
    """
    if verbose:
        print_modem_list_retrieval_info(sat_id, beam, vno, sw_version, limit, online)

    params = {}
    if sat_id and beam:
        params["satellite_id"] = sat_id
        params["beam_id"] = beam
    if vno:
        params["vno"] = vno
    if limit and limit < MAX_RESULTS_FROM_CMT:
        params["limit"] = limit
    if random:
        params["sort"] = "random"
    if online:
        params["online"] = "true"
    if sw_version:
        params["sw_version"] = sw_version

    url = f"{get_cmt_api_url()}/modems"
    response = requests.get(
        url,
        params=params,
        headers={"Authorization": get_cmt_token()},
        verify=False,
        timeout=timeout,
    )
    if response.status_code != 200:
        print(f"failed to get modems (url {url}, params {params}, response {response.text}")
        return []
    modems = response.json() or []
    if verbose:
        print(f"\t-> {len(modems)} found")
    return list(modems)


def print_modem_list_retrieval_info(sat_id, beam, vno, sw_version, limit, online):
    """
    Print information to the user about which modems we're about to retrieve from the CM-T API.

    :param sat_id: a number representing the satellite ID
    :param beam: a number representing the beam ID
    :param vno: a string representing the VNO
    :param sw_version: a string representing the software version (including prefix)
    :param limit: A number representing the maximum number of modems to return.
                  If None, CM-T's limitation is 10,000 modems.
    :param online: True to only return modems that are online, False otherwise
    """
    beam_desc = f" satellite {sat_id}, beam {beam}," if (beam and sat_id) else ""
    vno_desc = f" vno {vno}," if vno else ""
    version_desc = f" sw version {sw_version}," if sw_version else ""
    limit_desc = f" up to {limit}" if limit else ""
    online_desc = " online" if online else ""
    print(
        f" \nrequesting{limit_desc}{online_desc} modems"
        f" on{beam_desc}{vno_desc}{version_desc}".rstrip(",")
    )


def clear_beam_pinning(mac):
    """
    Clear a modem's beam pinning in ACS.

    :param mac: a string representing the MAC address of the
                modem whose ACS record we want to update
    :return: True on success, False otherwise
    """
    return pin_beam(mac, 0, "NOT_SET")


def pin_beam(mac, beam, pol):
    """
    Pin a modem to a beam in ACS.

    :param mac: a string representing the MAC address of the
                modem whose ACS record we want to update
    :param beam: a number representing the beam to which we want to pin the modem in ACS
    :param pol: a string representing the polarization of the beam to which we want to pin
                the modem in ACS; options are "LHCP", "RHCP", "LHCP_CO", "RHCP_CO"

    :return: True on success, False otherwise
    """
    response = requests.put(
        f"{get_cmt_api_url()}/cpe_management/cpe/{mac}",
        json={"Modem": {"PrimaryBeamID": beam, "PrimaryBeamPolarization": pol}},
        headers={"Authorization": get_cmt_token()},
        verify=False,
        timeout=ONE_MINUTE,
    )
    if response.status_code != 200 or common_utils.is_job_verbose():
        common_utils.print_http_response(response)
    return response.status_code == 200


def pin_beam_without_pol(mac, beam):
    """
    Pin a modem to a beam in ACS.

    DEPRECATED!!!!! CALL pin_beam() INSTEAD!!!!!

    :param mac: a string representing the MAC address of the
                modem whose ACS record we want to update
    :param beam: a number representing the beam to which we want to pin the modem in ACS
    :return: True on success, False otherwise
    """
    response = requests.put(
        f"{get_cmt_api_url()}/cpe_management/cpe/{mac}",
        json={"Modem": {"PrimaryBeamID": beam}},
        headers={"Authorization": get_cmt_token()},
        verify=False,
        timeout=ONE_MINUTE,
    )
    if response.status_code != 200 or common_utils.is_job_verbose():
        common_utils.print_http_response(response)
    return response.status_code == 200


def ping_modem(mac):
    """
    Pings a modem to check if it's online.

    param mac: a string representing a modem's MAC address
    :return: True if the modem could be reached, False otherwise
    """
    try:
        return (
            requests.get(
                f"{get_cmt_api_url()}/modems/{mac}/ping",
                params={"count": 2, "interval": 1, "timeout": 3},
                headers={"Authorization": get_cmt_token()},
                verify=False,
                timeout=10,
            ).status_code
            == 200
        )
    except requests.exceptions.ReadTimeout:
        return False


def get_enrichment_data(mac):
    """
    Get CM-T enrichment data for a given modem.

    :param mac: a string representing a modem's MAC address
    :return: an instance of the Response class from the requests
             library representing the response to this HTTP request
    """
    return requests.get(
        f"{get_cmt_api_url()}/modems/{mac}/enrichment",
        headers={"Authorization": get_cmt_token()},
        verify=False,
        timeout=ONE_MINUTE,
    )


def get_cpe_config(mac):
    """
    Returns the ldap options and ACS parameters of a given modem.

    :param mac: a string representing a modem's MAC address
    :return: an instance of the Response class from the requests
             library representing the response to this HTTP request
    """
    return requests.get(
        f"{get_cmt_api_url()}/cpe_management/cpe/{mac}",
        params={"filter": "acs", "type": "modem"},
        headers={"Authorization": get_cmt_token()},
        verify=False,
        timeout=ONE_MINUTE,
    )


def parse_goal_sat_id_from_cpe_config(response):
    """
    Parse the satellite ID from a response to a GET request
    on the /cpe_management/cpe/{mac} endpoint in the CM-T API.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a number representing a satellite ID, or None
    """
    try:
        return int(response.json()["acs"]["modem"]["PrimarySatelliteID"])
    except (TypeError, KeyError, ValueError):
        return None


def parse_goal_beam_from_cpe_config(response):
    """
    Parse the beam ID from a response to a GET request
    on the /cpe_management/cpe/{mac} endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a number representing a beam ID, or None
    """
    try:
        modem_data = response.json()["acs"]["modem"]

        # If present, pending values take precedence because they represent the latest decision.
        if "PendingValues" in modem_data and "PrimaryBeamID" in modem_data["PendingValues"]:
            return int(modem_data["PendingValues"]["PrimaryBeamID"])

        return int(modem_data["PrimaryBeamID"])

    except (TypeError, KeyError, ValueError):
        return None


def parse_goal_pol_from_cpe_config(response):
    """
    Parse the beam ID from a response to a GET request
    on the /cpe_management/cpe/{mac} endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a number representing a beam ID, or None
    """
    try:
        modem_data = response.json()["acs"]["modem"]

        # If present, pending values take precedence because they represent the latest decision.
        if (
            "PendingValues" in modem_data
            and "PrimaryBeamPolarization" in modem_data["PendingValues"]
        ):
            return modem_data["PendingValues"]["PrimaryBeamPolarization"]
        return modem_data["PrimaryBeamPolarization"]

    except (TypeError, KeyError, ValueError):
        return None


def parse_sw_version_from_cpe_config(response):
    """
    Parse the UT software version from a response to a GET
    request on the /cpe_management/cpe/{mac} endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a string representing a software version
    """
    try:
        return response.json()["acs"]["modem"]["SoftwareVersion"]
    except (TypeError, KeyError, ValueError):
        return "<unknown SW version>"


def parse_orig_sat_from_enrichment_data(response):
    """
    Parse the satellite ID from a response to a GET request
    on the /modems/{mac}/enrichment endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a number representing a beam ID, or None
    """
    try:
        return int(response.json()["satellite_id"])
    except (TypeError, KeyError, ValueError):
        return None


def parse_orig_beam_from_enrichment_data(response):
    """
    Parse the beam ID from a response to a GET request
    on the /modems/{mac}/enrichment endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a number representing a beam ID, or None
    """
    try:
        return int(response.json()["beam_id"])
    except (TypeError, KeyError, ValueError):
        return None


def parse_orig_pol_from_enrichment_data(response):
    """
    Parse the beam polarization from a response to a GET request
    on the /modems/{mac}/enrichment endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a string representing a beam polarization, or None
    """
    try:
        return response.json()["beam_polarization"]
    except (TypeError, KeyError, ValueError):
        return None


def parse_vno_from_enrichment_data(response):
    """
    Parse the VNO from a response to a GET request
    on the /modems/{mac}/enrichment endpoint in CM-T.

    :param response: an instance of the Response class from the requests
                     library representing the response to an HTTP request
    :return: a string representing a VNO
    """
    try:
        return response.json()["vno"]
    except (TypeError, KeyError, ValueError):
        return "<unknown vno>"
