"""
StreamOn shared passphrase publisher

This job will do the following steps:
    1. Check Artifactory repositories (source and staging) to compare if a
    file is missing on the staging one. If no file is missing, exit with 0
    after this single step.
    2. For all missing files in the staging repo, download them from the
    source repo, extract their content, decrypt it using the RSA private key,
    reencrypt it with secureFileTool using the SWKEY and finally push it
    back to the staging Artifactory repo.
"""

import os
import sys

# Add libs folder to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shutil
import tarfile
import hashlib
import pathlib
import subprocess
import json
from typing import List
from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from libs import vault_utils
from libs import artifactory
from libs import common_utils


TMP_DIR = "streamon_tmp_dir"

# Service Account used to access StreamOn secrets in vault
VAULT_STREAMON_SVC_NAME = "svc_streamon"

# Service Account used to GET/PUT from/to Artifactory
ARTI_JENKINS_SVC_NAME = "svc_git_ut_jenkins"
# This service account is only accessible from the preprod environment
ARTI_JENKINS_SVC_NAME_ENV = "preprod"

# Artifactory URIs endpoints used depending on the environnement
ARTI_URI_STREAMON_PROD = "/streamon-pp-prod/ops"
ARTI_URI_STREAMON_PROD_STAGING = "/bbc-gen-prodstaging/terminal/apps/streamon/shared-pp"

ARTI_URI_STREAMON_PREPROD = "/streamon-pp-preprod/ops"
ARTI_URI_STREAMON_PREPROD_STAGING = "/streamon-pp-preprod/staging-ops"


def remove_extension(filename: str) -> str:
    """
    Remove the extension from any file

    Args:
        filename (str): A file name or a filepath

    Returns:
        str: A string with the filename or the filepath without the extension
    """
    suffixes = ''.join(pathlib.Path(filename).suffixes)
    return filename.replace(suffixes, '')


def get_missing_files_in_staging(
    arti_auth: tuple, arti_src_uri: str, arti_staging_uri: str
) -> List[str]:
    """
    Search for all files that are present in the source directory but not yet
    in the destination folder. Take into account the extension .tsf in the
    destination directory (staging).

    Args:
        auth (tuple): Username and password tuple for Artififactory access
        arti_src_uri (str): URI to directory with tar.gz pushed by ops
        arti_staging_uri (str): URI to directory with tsf files pushed by this job

    Returns:
        [List(str)]: A list of strings with all the URI to the files that are
                    missing in arti_staging_uri
    """
    # Get all files in the source Artifactory destination
    src_files = artifactory.get_artifact_list(arti_auth, arti_src_uri)

    # Get all files in the destination Artifactory that are already converted to TSF
    dst_files = artifactory.get_artifact_list(arti_auth, arti_staging_uri)

    ret_files = []
    for src_file in src_files:
        # Extract only the name (e.g. StreamOn_SharedPP_<wwn>.tar.gz)
        src_filename = os.path.basename(src_file)

        # Remove extensions (.tar.gz)
        filename = remove_extension(src_filename)

        # Only remove
        if f"/{filename}.tsf" not in dst_files:
            ret_files.append(arti_src_uri + src_file)
    return ret_files


def extract_streamon_shared_pp_tarball(tarball_filename: str, tmp_dir: str):
    """
    Extract the files from the tarball into a temporary folder

    Args:
        tarball_filename (str): Tarball path
        tmp_dir (str): Path to temporary folder to store extracted data
    """
    # Extract (untar) tarball to a folder
    with tarfile.open(tarball_filename) as tar:
        tar.extractall(path=tmp_dir)
        tar.close()


def decrypt_streamon_shared_pp(private_rsa_3072_key: str, path: str):
    """
    Decrypt StreamOn shared passphrase using the provided RSA-3072 key.

    Args:
        private_rsa_3072_key (str): RSA-3072 private key in a PEM format.
        path (str): Path to the files to be decrypted

    Returns:
        [type]: The path to the decrypted file.
    """
    rsa_private_key = RSA.importKey(private_rsa_3072_key)
    # The padding PKCS#1 v1.5 is the default one used by openssl
    # See the openssl RSA man page (man openssl rsautl)
    decryptor = PKCS1_v1_5.new(rsa_private_key)

    # Open encrypted file extracted from tarball
    with open(path, "rb") as enc_file:
        print(f"Decrypting {path}")

        # Random data that are returned if the decrypt function fails
        sentinel = Random.get_random_bytes(16)

        # Decrypt the file content using the provided cipher
        decrypted_text = decryptor.decrypt(enc_file.read(), sentinel)

        if sentinel == decrypted_text:
            raise RuntimeError("ERROR: Failed to decrypt file payload")

        # Remove the .enc extension from the path name
        clear_file_path = os.path.splitext(path)[0]

        # Write the content of the clear file
        with open(clear_file_path, "wb") as file:
            file.write(decrypted_text)

        return clear_file_path


def validate_streamon_shared_pp(clear_file_path: str, sha256sum_file_path: str):
    """
    Validate that the SHA256 hash of the clear file matches the bundled sha256
    sum

    Args:
        clear_file_path (str): File system path to the clear text passphrase
        sha256sum_file_path (str): File system path to the sha256sum file
            bundled in the tarball
    Raises:
        RuntimeError: If the sha256 hash doesn't match the expected value
    """
    # Readback what was saved and compute sha256 sum
    with open(clear_file_path, "rb") as file:
        sha256sum = hashlib.sha256(file.read()).hexdigest()

    # Get the expected hash from the tarball
    with open(sha256sum_file_path) as file:
        expected_sha256sum = file.read()

    # Compare the sha256 of the plaintext from the decrypted with the original
    if sha256sum == expected_sha256sum:
        print(f"SHA256 hash verified for {clear_file_path}")
    else:
        raise RuntimeError(
            f"ERROR: File {clear_file_path} can't be "
            f"verified. Expected {expected_sha256sum}, "
            f"got {sha256sum}"
        )


def reencrypt_with_swkey(ut_keysplit: str, clear_file_path: str, tsf_file_path: str):
    """
    Spawn a secureFileTool process that will reencrypt a file using the provided
    SWKEY.

    Args:
        ut_keysplit (str): String containing the SWKEY keysplit for the UT modem
        clear_file_path (str): Path to the decrypted shared passphrase
        tsf_file_path (str): Path to the TSF file generated by secureFileTool
    """
    # Save keysplit to temporary file
    keysplit_path = os.path.join(TMP_DIR, "ut_keysplit")
    with open(keysplit_path, "w") as file:
        file.write(ut_keysplit)

    # Compute absolute path to secureFileTool (bundled in this git repo)
    path_sft = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../executables/secureFileTool/secureFileTool")
    )

    args = (
        path_sft,
        "-g",
        clear_file_path,
        "-o",
        tsf_file_path,
        "-v",
        "1",
        "-t",
        "SWKEY",
        "-k",
        keysplit_path,
    )
    with subprocess.Popen(args, stdout=subprocess.PIPE) as popen:
        popen.wait()
        formatted_output = (
            str(popen.stdout.read().decode("utf-8")).replace("\\n", "\n").replace("\\t", "\t")
        )
        if popen.returncode != 0:
            raise RuntimeError(
                f"ERROR: secureFileTool failed with args {args}:\n"
                f"SecureFileTool output:\n{formatted_output}"
            )

    print(f"TSF successfully generated. SecureFileTool output:\n" f"{formatted_output}")


def decrypt_reencrypt_and_put(  # pylint: disable=too-many-locals
    arti_auth: tuple,
    missing_files_uri: List[str],
    arti_staging_uri: str,
    private_rsa_3072_key: str,
    ut_keysplit: str,
) -> int:
    """
    Main function that will untar, decrypt, reencrypt with SFT and push back
    to Artifactory.

    Args:
        auth (tuple): Username and password tuple used to access Artifactory
        missing_files_uri (List[str]): List of files that were not found in the
            destination Artifactory repo (arti_staging_uri).
        arti_staging_uri (str): Destination Artifactory repo/folder.
        private_rsa_3072_key (str): RSA-3072 private key used to decrypt the
            shared passphrases.
        ut_keysplit (str): UT Keysplit (aka SWKEY) used to reencrypt the files
            into a TSF using secureFileTool utility.

    Return:
        0 if all files in the missing_files_uri argument were handled
        successfully. In case of error, return a positive non-zero representing
        the number of files in missing_files_uri that failed to be handled.
    """
    ret = 0
    for f_uri in missing_files_uri:
        print("-" * 120)
        print(f"Downloading {f_uri}")

        try:
            # Download the missing file
            artifactory.download_file(arti_auth, f_uri)

            # Create temporay directory to extract tarball.
            # Delete it if it already exists
            if not os.path.exists(TMP_DIR):
                os.makedirs(TMP_DIR)
            else:
                shutil.rmtree(TMP_DIR)
                os.makedirs(TMP_DIR)

            # Extract file name from the URI (with extension)
            tarball_filename = os.path.basename(f_uri)

            # Remove extension from name
            base_name = remove_extension(tarball_filename)

            # Extract the tarball into a temporary directory
            extract_streamon_shared_pp_tarball(tarball_filename, TMP_DIR)

            # Decrypt the shared passphrase using the RSA private key
            enc_file_path = os.path.join(TMP_DIR, f"{base_name}.txt.enc")
            clear_file_path = decrypt_streamon_shared_pp(private_rsa_3072_key, enc_file_path)

            # Validate the integrity of the decrypted file against its sha256
            sha256sum_file_path = os.path.join(TMP_DIR, f"{base_name}.txt.sha256sum")
            validate_streamon_shared_pp(clear_file_path, sha256sum_file_path)

            # Use secureFileTool to create a TSF file using the SWKEY
            tsf_file_path = os.path.join(TMP_DIR, f"{base_name}.tsf")
            reencrypt_with_swkey(ut_keysplit, clear_file_path, tsf_file_path)

            # Concatenate the TSF file with the arti_staging_uri, we need full path
            arti_staging_file_uri = os.path.join(arti_staging_uri, f"{base_name}.tsf")

            # PUT the newly TSF file to Artifactory into the staging prod repo
            resp = artifactory.put_file(arti_auth, tsf_file_path, arti_staging_file_uri)

            print(f"Artifact {tsf_file_path} deployed to Artifactory")
            print(json.dumps(resp, indent=2))
        except BaseException as ex:
            print(f"FAILED: Error while handling {f_uri}\n:{ex}")
            ret = ret + 1

        # Cleanup
        shutil.rmtree(TMP_DIR)
    return ret


def handle_streamon_shared_pp():
    """
    Main method that will:
        1. Check Artifactory repositories (source and staging) to compare if a
        file is missing on the staging one. If no file is missing, exit with 0
        after this single step.
        2. For all missing files in the staging repo, download them from the
        source repo, extract their content, decrypt it using the RSA private key,
        reencrypt it with secureFileTool using the SWKEY and finally push it
        back to the staging Artifactory repo.

    Return:
        0 if all files in the missing_files_uri argument were handled
        successfully. In case of error, return a positive non-zero representing
        the number of files in missing_files_uri that failed to be handled.
    """
    env = common_utils.get_expected_env_var("environment")

    print(f"Environment is {env}")
    # Use the Artifactory endpoint depending on the selected environnement
    arti_src_uri = ARTI_URI_STREAMON_PROD if env == "prod" else ARTI_URI_STREAMON_PREPROD
    arti_staging_uri = (
        ARTI_URI_STREAMON_PROD_STAGING if env == "prod" else ARTI_URI_STREAMON_PREPROD_STAGING
    )

    print(f"arti_src_uri is {arti_src_uri}")
    print(f"arti_staging_uri is {arti_staging_uri}")

    # Service account to get and push to Artifactory
    svc_ut_jenkins = ARTI_JENKINS_SVC_NAME
    # Retrieve the service account password from Vault
    svc_ut_jenkins_pwd = vault_utils.get_service_account_password(
        svc_ut_jenkins, ARTI_JENKINS_SVC_NAME_ENV
    )

    # StreamOn Vault service account username
    vlt_svc_streamon = common_utils.get_expected_env_var(f"vault_streamon_{env}_usr")
    # StreamOn Vault service account password
    vlt_svc_streamon_pwd = common_utils.get_expected_env_var(f"vault_streamon_{env}_pwd")

    # Authentication credentials used in all accesses to Artifactory
    arti_auth = (svc_ut_jenkins, svc_ut_jenkins_pwd)

    # Compare both endpoints and return all the files that are missing in the
    # arti_staging_uri compared to the arti_src_uri
    missing_files_uri = get_missing_files_in_staging(arti_auth, arti_src_uri, arti_staging_uri)
    if not missing_files_uri:
        print(
            f"All the files from {arti_src_uri} are present "
            f"in {arti_staging_uri}. No action required."
        )
        sys.exit(0)

    print(f"Missing files in {arti_staging_uri} found:\n- {missing_files_uri}\n")

    # Even though we have two RSA keys, one prod and one preprod, only
    # a single StreamOn service account exist. This single service account has
    # access to both stripes (prod and preprod)
    streamon_vault_env = env

    # Use the streamon vault service account's credentials to log
    # into Vault and get a token
    streamon_vault_token = vault_utils.get_vault_token(
        env=streamon_vault_env, username=vlt_svc_streamon, password=vlt_svc_streamon_pwd
    )

    # Get the private RSA 3072 key to decrypt ops payload
    private_rsa_3072_key = vault_utils.get_streamon_private_key(
        streamon_vault_token, streamon_vault_env
    )

    # Use the token to retrieve the UT KeySplit from vault
    ut_keysplit = vault_utils.get_ut_swkey(streamon_vault_token, streamon_vault_env)

    # Main function that will untar, decrypt, reencrypt with SFT and push back
    # to Artifactory
    return decrypt_reencrypt_and_put(
        arti_auth, missing_files_uri, arti_staging_uri, private_rsa_3072_key, ut_keysplit
    )


if __name__ == "__main__":
    sys.exit(handle_streamon_shared_pp())
