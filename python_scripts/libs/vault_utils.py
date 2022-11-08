"""
Contains generic functionality for interfacing with the Vault API from Jenkins.
"""
import os
import requests
import urllib3
from libs import common_utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VAULT_URL = "https://vault.security.viasat.io:8200"


def get_vault_token(env=None, username=None, password=None):
    """
    Log in to vault.security.viasat.io to get a token.

    :param env: "dev", "preprod", or "prod"
    :param username: Service account username
    :param password: Service account password
    :return: a string representing the client token we'll need to authenticate with Vault
    """
    env = env or os.environ["environment"]
    env = "preprod" if (env == "dev") else env
    username = username or common_utils.get_expected_env_var(f"vault_usr_{env}")
    password = password or common_utils.get_expected_env_var(f"vault_pwd_{env}")

    # Log into Vault.
    response = requests.post(
        f"{VAULT_URL}/v1/auth/ut-devops-{env}/login/{username}",
        headers={"Content-Type": "application/json"},
        json={"password": password},
        verify=False,
    )

    # Parse the Vault token from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["auth"]["client_token"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get Vault token.")


def get_cmt_api_service_account_password(env=None, vault_token=None):
    """
    Retrieve the CM-T API service account password from Vault.

    :param vault_token: our token for accessing vault
    :param env: "preprod" or "prod"
    :return: a string representing the CM-T API service account password
    """
    env = env or os.environ["environment"]
    env = "preprod" if (env == "dev") else env
    vault_token = vault_token or get_vault_token(env)
    service_account_path = f"{VAULT_URL}/v1/secret/viasat/sdp/{env}/ut/serviceaccounts/"
    cmt_api_service_account = f"ut-devops-{env}_cmt_api_user"
    response = requests.get(
        service_account_path + cmt_api_service_account,
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["secret_key"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get CM-T API password.")


def get_service_account_password(username, env=None, vault_token=None):
    """
    Retrieve the service account password for a given username from Vault.

    :param username: account username (e.g. svc_git_ut_jenkins)
    :param vault_token: our token for accessing vault
    :param env: "preprod" or "prod"
    :return: a string representing the service account password
    """
    env = env or os.environ["environment"]
    env = "preprod" if (env == "dev") else env
    vault_token = vault_token or get_vault_token(env)
    service_account_path = f"{VAULT_URL}/v1/secret/viasat/sdp/{env}/ut/serviceaccounts/{username}"
    response = requests.get(
        service_account_path,
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["password"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get Jenkins SVC service account password.")


def get_streamon_private_key(vault_token, env=None):
    """
    Retrieve the service account p4svc_ut_jenkins password from Vault.

    :param vault_token: our token for accessing vault
    :param env: "preprod" or "prod"
    :return: a string representing the private key content
    """
    env = env or os.environ["environment"]
    env = "preprod" if (env == "dev") else env
    service_account_path = (
        f"{VAULT_URL}/v1/secret/viasat/sdp/{env}/ut/viasat/streamon"
        "/security/keys/private/shared_passphrase_xfer/10202021"
    )
    response = requests.get(
        service_account_path,
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the file content from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["file"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get StreamOn RSA private key.")


def get_ut_swkey(vault_token, env=None):
    """
    Retrieve the SWKEY (keysplit) from Vault.

    :param vault_token: our token for accessing vault
    :param env: "preprod" or "prod"
    :return: a string containing the ut keysplit
    """
    env = env or os.environ["environment"]
    env = "preprod" if (env == "dev") else env
    service_account_path = (
        f"{VAULT_URL}/v1/secret/viasat/sdp/{env}/ut/viasat/streamon/security/keys/symmetric/swkey"
    )
    response = requests.get(
        service_account_path,
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the file content from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["file"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get SWKEY content.")


def get_acs_db_service_account_password(vault_token=None):
    """
    Retrieve the ACS database service account password from Vault.

    :param vault_token: our token for accessing vault
    :return: a string representing the ACS database service account password
    """
    vault_token = vault_token or get_vault_token("prod")
    response = requests.get(
        f"{VAULT_URL}/v1/secret/viasat/sdp/prod/ut/serviceaccounts/"
        f"{common_utils.ACS_DB_SERVICE_ACCT_USR}",
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["password"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get ACS database password.")


def get_beam_drift_db_service_account_password(vault_token=None):
    """
    Retrieve the beam drift database service account password from Vault.

    :param vault_token: our token for accessing vault
    :return: a string representing the beam drift database service account password
    """
    vault_token = vault_token or get_vault_token("prod")
    response = requests.get(
        f"{VAULT_URL}/v1/secret/viasat/sdp/prod/ut/serviceaccounts/"
        f"{common_utils.BEAM_DRIFT_DB_SERVICE_ACCT_USER}",
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["password"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get beam drift database password.")


def get_ut_devops_cicd_password(env=None, vault_token=None):
    """
    Retrieve the service account password for the UT DevOps viasat.io account.

    :param env: "preprod", "dev", or "prod"
    :param vault_token: our token for accessing vault
    :return: a string representing a service account password
    """
    env = env or common_utils.get_expected_env_var("environment")
    env = "preprod" if (env == "dev") else env
    vault_token = vault_token or get_vault_token(env)
    response = requests.get(
        f"{VAULT_URL}/v1/secret/viasat/sdp/{env}/ut/serviceaccounts/" f"ut-devops-{env}_cicd",
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            return response.json()["data"]["password"]
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get stream service account password.")


def get_prod_sdp_api_service_account_password(vault_token=None):
    """
    Retrieve the sdp-api service account password from Vault.

    :param vault_token: our token for accessing vault
    :return: a string representing the sdp-api service account password
    """
    vault_token = vault_token or get_vault_token("prod")
    response = requests.get(
        f"{VAULT_URL}/v1/secret/viasat/sdp/prod/ut/serviceaccounts/"
        f"{common_utils.SDP_API_SERVICE_ACCT_USR_VAULT}",
        headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
        verify=False,
        timeout=60,
    )

    # Parse the password from the response and return it.
    try:
        if response.status_code == 200:
            if "sdp_api_pwd_prod" in os.environ:  # overwrite the passwd with local env if needed
                passwd = common_utils.get_expected_env_var("sdp_api_pwd_prod")
            else:
                passwd = response.json()["data"]["password"]
            return passwd
        raise RuntimeError
    except (TypeError, KeyError, ValueError, RuntimeError):
        common_utils.print_http_response(response)
        raise RuntimeError("Failed to get sdp api  password.")
