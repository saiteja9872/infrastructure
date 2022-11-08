"""
Contains generic helper functions that could be useful in a broad variety of contexts.
"""

import os
from math import floor, ceil
from datetime import datetime
import json
from json import JSONDecodeError
import jsonschema

ACS_DB_SERVICE_ACCT_USR = "modot_read_only"
BEAM_DRIFT_DB_SERVICE_ACCT_USER = "ut-devops-prod_local-db-usr"

# if we have sdp_api_usr_prod defined in our env, we will use it instead of
# service account
if "sdp_api_usr_prod" in os.environ.keys():
    SDP_API_SERVICE_ACCT_USR = os.environ["sdp_api_usr_prod"]
else:
    SDP_API_SERVICE_ACCT_USR = "ut-devops-prod_cicd"

SDP_API_SERVICE_ACCT_USR_VAULT = "ut-devops-prod_cicd"


def hw_type_of_sw_version(sw_version):
    """
    Parse the HW type from a software version containing the HW prefix.

    :param sw_version: a string representing a UT SW version (e.g. "DATA_3.7.9.13.15")
    :return: a string representing the HW type for that version (e.g. "data")
    """
    if "_" in sw_version:
        hw_type = sw_version.split("_")[0].lower()
        if hw_type:
            return hw_type
    raise RuntimeError(f"Invalid SW version \"{sw_version}\" (missing '<HW type>_' prefix)")


def timestamp():
    """
    Get the current epoch time in seconds.

    Used to ensure that results files have unique names.

    :return: the current epoch time in seconds
    """
    return round(datetime.now().timestamp())


def readable_list(items):
    """
    Convert a list of items into a grammatically correct noun
    phrase with the commas and conjunctions in the right places.

    :param items: a list
    :return: a string that contains the item in the input list separated by commas and conjunctions
    """
    length = len(items)
    if length == 0:
        return ""
    if length == 1:
        return items[0]
    if length == 2:
        return " and ".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def print_heading(title):
    """
    A formatting helper function for printing a heading.

    :param title: the title of the heading we want to print
    """
    heading_length = 100
    margin_length = (heading_length - 4 - len(title)) / 2
    print(
        f" \n"
        f"+{'-' * (heading_length - 2)}+\n"
        f"|{' ' * floor(margin_length)} {title} {' ' * ceil(margin_length)}| \n"
        f"+{'-' * (heading_length - 2)}+"
    )


def print_http_response(response):
    """
    Print a response to an HTTP request.

    :param response: an instance of the Response class from the requests library
    """
    if response is not None:

        # Format request info.
        request = response.request
        if request.body:
            try:
                request_body_info = (
                    f" with body:\n"
                    f"{json.dumps(json.loads(request.body.decode('utf-8')), indent=2)}\n"
                )
            except (JSONDecodeError, ValueError, AttributeError):
                request_body_info = f" with body:\n{request.body}\n"
        else:
            request_body_info = " "

        # Format response info.
        try:
            response_body_info = json.dumps(response.json(), indent=2)
        except (JSONDecodeError, ValueError, AttributeError):
            response_body_info = response.text

        # Print everything.
        print(
            f" \n{request.method} request to {request.url}{request_body_info}"
            f"returned status {response.status_code} and response:\n{response_body_info}"
        )


def get_expected_env_var(var):
    """
    Get the value of an environment variable or raise
    an exception if that variable has not been set.

    :param var: a string representing the name of the environment
                variable that we expect to be set
    :return: a string representing the value assigned to that environment variable
    """
    try:
        val = os.environ[var]
        if val is None:
            raise KeyError
    except KeyError:
        raise RuntimeError(f"Expected environment variable {var} not found")
    return val


def get_environment():
    """
    Get the environment (prod, preprod, or dev) we're running this job in.

    :return: a string "prod", "preprod", or "dev"
    """
    env = get_expected_env_var("environment").lower()
    if env not in ["preprod", "prod", "dev"]:
        raise RuntimeError(f'environment "{env}" not one of "prod", "preprod", "dev"')
    return env


def check_expected_env_bool(var):
    """
    Determine the value of a boolean environment variable.

    Used to determine whether checkbox parameters to the Jenkins job running
    this code were checked.

    :param var: a string representing the name of the boolean environment variable
    :return: True if the environment variable's value is "true" (e.g. its corresponding
             checkbox parameter is checked), False otherwise
    """
    return get_expected_env_var(var) == "true"


def is_job_verbose():
    """
    Determine whether the Jenkins job calling this function is running in verbose mode.

    Used as a helper function to other functions that want to decide how many details to print.

    :return: True if the job is in verbose mode, False otherwise
    """
    return check_expected_env_bool("verbose")


def batches(listy, chunk_size):
    """
    Turn a list into a list of lists of uniform size.

    For example,
    input: listy=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], n=3
    output: [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11]]

    :param listy: a list
    :param chunk_size: the desired chunk size
    :return: a list of lists that represents the input list divided into chunks of the desired size
    """
    return [listy[i : i + chunk_size] for i in range(0, len(listy), chunk_size)]


def is_valid_number(something):
    """
    Check if something is a number.

    :param something: hopefully a number
    :return: True if the input is a valid number, False otherwise
    """
    try:
        int(something)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_bool(something):
    """
    Check if something is a boolean.

    :param something: hopefully a boolean
    :return: True if the input is a valid boolean, False otherwise
    """
    return isinstance(something, bool)


def is_valid_sql_timestamp(stamp):
    """
    Check if a string is a valid timestamp of the
    form "%Y-%m-%d %H:%M" (e.g. "2021-03-01 23:34")

    :param stamp: a string representing a timestamp
    :return: True if it's a valid SQL timestamp, False otherwise
    """
    try:
        datetime.strptime(stamp, "%Y-%m-%d %H:%M")
        return True
    except (ValueError, TypeError):
        return False


def is_valid_beam_pol(pol):
    """
    Check whether a string is a valid beam polarization

    :param pol: a beam polarization

    :return: True if the input param is a valid beam polarization, False otherwise
    """
    return pol and pol in ["LHCP", "RHCP", "LHCP_CO", "RHCP_CO", "NOT_SET"]


def does_json_instance_fit_schema(instance, schema, verbose=False):
    """
    Validate a JSON instance against a schema.

    :param instance: a dictionary representing the JSON instance to be validated
    :param schema: a dictionary representing the JSON schema to validate the instance against
    :param verbose: True to print the details of any validation errors, False otherwise
    :return: True on success, False on failure
    """
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as err:
        if verbose:
            print(err)
    return False
