"""
Checks if the SNORE Smart Home WiFi active keys in Vault are expired or expiring soon
"""
import os
from datetime import datetime
import sys
import requests
from OpenSSL import crypto

# The minimum number of days remaining in a cert's lifespan before
# we want to send a notification that it expires soon.
BUFFER_DAYS_DEFAULT = 30


def check_snore_key_expiry():
    """
    Main method - check the expiration date of the active SNORE keys to see if they expire soon.
    :return: exit(0) upon success (none of the active keys expires soon),
             exit(1) upon failure (one or more active keys expire soon)
    """

    # Determine whether the user wants us to look up the pre-prod keys, the prod keys, or both
    environments = get_environments()

    # Determine the minimum number of days a cert can have
    # left before the user considers its expiration "soon."
    buffer_days = get_buffer_days()

    # For prod, pre-prod, or both, check all the cert expiration dates and
    # change all_current to False if any of them expires within buffer_days.
    all_current = True
    for environment in environments:
        print(f"\n{environment}------------------------------------------------------------")

        # Get the username and password for the service account we use to access Vault.
        username, password = get_vault_credentials(environment)

        # Use the service account's credentials to log into Vault and get a token.
        vault_token = log_in_to_get_token(username, password, environment)

        # Use the token to retrieve the certificate associated with the SNORE key from Vault.
        json_cert = get_active_cert_from_vault(vault_token, environment)

        # Convert the cert into a format that allows us to
        # easily parse its properties into human readable values.
        pem_cert = convert_cert_to_pem(json_cert)

        # Get the cert's serial number so we can distinguish it from the others.
        serial_num = pem_cert.get_serial_number()

        # Parse the expiration time from the cert.
        expiry_time = parse_expiry_time_from_pem(pem_cert)

        # Calculate the number of days left until the cert expires.
        days_left = (expiry_time - datetime.now()).days

        warning = ""
        expiration_message = "won't expire until"

        # Check whether the cert is already expired.
        if days_left < 0:
            warning = "WARNING: "
            expiration_message = f"expired {abs(days_left)} days ago on"
            all_current = False

        # Check whether the cert will expire soon.
        elif days_left < buffer_days:
            warning = "WARNING: "
            expiration_message = f"will expire in {days_left} days on"
            all_current = False

        # Indicate when the cert will expire.
        print(f"\t{warning}Cert with serial # {serial_num} {expiration_message} {expiry_time}")

        print("------------------------------------------------------------------")

    # If any of the certs expires soon, the job fails.
    if all_current:
        print(
            "\nCongratulations, none of the certs will expire within {} days.\n".format(buffer_days)
        )
        sys.exit(0)
    else:
        print("\nIt's time to update the certs!\n")
        sys.exit(1)


def get_environments():
    """
    Determine whether the user wants us to look up the pre-prod keys, the prod keys, or both.
    :return: a list of strings containing "prod", "preprod", or both
    """
    environments = []
    if os.getenv("PRE_PROD") == "true":
        environments.append("preprod")
    if os.getenv("PROD") == "true":
        environments.append("prod")
    if not environments:
        print(
            "Input parameter error: you must select at least one environment"
            " (prod, preprod, or both)"
        )
        sys.exit(0)
    return environments


def get_buffer_days():
    """
    Parse the buffer days requested by the user into an integer and print an error
    message if that fails.
    :return: the minimum number of days of validity a cert can have left before
             the user wants to generate a notification that it will expire soon
    """
    buffer_days = BUFFER_DAYS_DEFAULT
    buffer_days_string = os.getenv("BUFFER_DAYS")
    try:
        buffer_days = int(buffer_days_string)
    except ValueError:
        print(
            "Input parameter error: BUFFER_DAYS should be an integer, but you put:",
            buffer_days_string,
        )
        print("Continuing with the default of", buffer_days, "days")
    return buffer_days


def get_vault_credentials(environment):
    """
    Get the credentials for the service account we use to access Vault.
    :param environment: "preprod" or "prod"
    :return: the username and password for the service account
    """
    username = os.getenv("VAULT_USR_PROD" if environment == "prod" else "VAULT_USR_PREPROD")
    password = os.getenv("VAULT_PWD_PROD" if environment == "prod" else "VAULT_PWD_PREPROD")
    return username, password


def log_in_to_get_token(username, password, environment):
    """
    Log in to vault.security.viasat.io to get a token.
    :param username: the username for the service account we use to access Vault
    :param password: the password for the service account we use to access Vault
    :param environment: "preprod" or "prod"
    :return: the client token we'll need to authenticate with Vault
    """

    # Log into Vault.
    url = (
        "https://vault.security.viasat.io:8200/v1/auth/ut-devops-"
        + environment
        + "/login/"
        + username
    )
    headers = {"Content-Type": "application/json"}
    payload = {"password": password}
    response = requests.post(url, headers=headers, json=payload, verify=False)

    # Parse the token from the response.
    response_json = response.json()
    return response_json["auth"]["client_token"]


def get_active_cert_from_vault(vault_token, environment):
    """
    Retrieve the active cert for the SNORE private key from Vault.
    :param vault_token: our token for accessing vault
    :param environment: "preprod" or "prod"
    :return: the active cert in json format from the response provided by Vault
    """
    headers = {"Content-Type": "application/json", "X-Vault-Token": vault_token}
    key_path = f"https://vault.security.viasat.io:8200/v1/secret/viasat/sdp/{environment}/ut/keys/"

    # Retrieve the SNORE private keys from Vault and parse the active slot from the response.
    response = requests.get(f"{key_path}private/snore/tokens", headers=headers, verify=False)
    response_json = response.json()
    active_slot = response_json["data"]["active_slot"]

    # Retrieve the SNORE certs from Vault and parse the active cert from the response.
    response = requests.get(f"{key_path}public/snore/tokens", headers=headers, verify=False)
    response_json = response.json()
    active_cert = response_json["data"][f"kid_{active_slot}"]
    return active_cert


def convert_cert_to_pem(cert):
    """
    Convert a cert from its initial json format into an
    object that allows us to easily access its fields.
    :param cert: a certificate in raw json string format
    :return: an X509 object
    """

    # Get certificate string into pem format.
    reformatted_cert = reformat_cert(cert)

    # Convert the cert from a pem formatted string into an X509 object.
    return crypto.load_certificate(crypto.FILETYPE_PEM, bytes(reformatted_cert, "utf-8"))


def reformat_cert(cert):
    """
    Covert a certificate from its initial json response format into pem format.
    :param cert: a string containing a certificate in json format
    :return: the input string converted to pem format
    """
    header = "-----BEGIN CERTIFICATE-----"
    footer = "-----END CERTIFICATE-----"

    # Temporarily remove the header and footer so we can
    # easily insert a newline every 64 characters in the body.
    cert = cert.replace(header, "")
    cert = cert.replace(footer, "")
    cert = cert.replace('"', "")

    # Insert a newline after every 64 characters in the body of the cert.
    cert = insert_newlines(cert)

    # Put the header and footer back.
    cert = "\n" + header + cert
    return cert + footer + "\n"


def insert_newlines(string, every=64):
    """
    Insert a newline character every specified number of characters in a string
    and make sure the resulting string begins and ends with a newline character.
    Used as a step in converting a json certificate string into pem format.
    :param string: a string
    :param every: the number of characters we want in each line
    :return: the input string with a newline character inserted
             after each requested number of characters
    """
    lines = []
    for i in range(0, len(string), every):
        lines.append(string[i : i + every])  # noqa: E203
    output = "\n".join(lines)
    if output[0] != "\n":
        output = "\n" + output
    if output[-1] != "\n":
        output = output + "\n"
    return output


def parse_expiry_time_from_pem(cert):
    """
    Get a certificate's expiration time.
    :param cert: an X509 object representing a certificate
    :return: a datetime object containing that certificate's expiration time
    """
    return datetime.strptime(cert.get_notAfter().decode("utf-8")[:-1], "%Y%m%d%H%M%S")


check_snore_key_expiry()
