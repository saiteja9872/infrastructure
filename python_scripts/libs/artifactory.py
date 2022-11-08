"""
Contains generic functionality for interfacing with the Artifactory REST API
"""

import os
import hashlib
from typing import List, Tuple
import requests
from libs import common_utils

ARTI_API = "https://artifactory.viasat.com/artifactory/api/storage"
ARTI_BASE_URL = "https://artifactory.viasat.com/artifactory"
LIST_SUFFIX = "?list"


def put_file(auth: Tuple[str], src_path: str, dest_uri: str) -> str:
    """
    Use the Artifactory REST API to deploy a file to a given path.

    Args:
        auth (tuple): Username and password tuple used to access Artifactory
        src_path (str): File system path to the file to be deployed.
        dest_uri (str): URI to the file (e.g. MyRepo/MyFile.txt)

    Returns:
        [str]: Return the download URI for the ressource if it has been
               correctly deployed
    """
    with open(src_path, "rb") as file:
        md5sum = hashlib.md5(file.read()).hexdigest()
        file.seek(0)
        sha1sum = hashlib.sha1(file.read()).hexdigest()
        file.seek(0)
        sha256sum = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)
        headers = {
            "X-Requested-With": "Python requests",
            "content-type": "application/octet-stream",  # Generic content-type
            "X-Checksum-Md5": md5sum,
            "X-Checksum-Sha1": sha1sum,
            "X-Checksum-Sha256": sha256sum,
        }
        resp = requests.put(f"{ARTI_BASE_URL}{dest_uri}", auth=auth, data=file, headers=headers)
        try:
            if resp.status_code in (201, 200):
                return resp.json()
            raise RuntimeError
        except (TypeError, KeyError, ValueError, RuntimeError):
            common_utils.print_http_response(resp)
            raise RuntimeError(f"Failed to PUT {dest_uri}")


def get_artifact_list(auth: Tuple[str], path: str) -> List[str]:
    """
    Gets list of files in artifactory folder

    Args:
        auth (tuple): Username and password tuple used to access Artifactory
        path (str): path within Artifactory repo and folder to scan
                    (e.g streamon-pp-preprod/ops)

    Returns:
        list: list of strings with the file URIs found in the given repo/folder
    """
    # Extract uri from each element of artifacts list and return as list of strings
    # ignore any folders encountered
    resp = requests.get(ARTI_API + path + LIST_SUFFIX + "&listFolders=0", auth=auth)
    resp.raise_for_status()
    raw_list = resp.json()["files"]
    return [x["uri"] for x in raw_list]


def download_file(auth: Tuple[str], uri: str):
    """
    Download a file from Artifactory and save it to the disk.

    Args:
        auth (tuple): Username and password tuple used to access Artifactory
        uri (str): Path to the Artifactory repository and subfolders
    """
    resp = requests.get(f"{ARTI_BASE_URL}{uri}", auth=auth)
    resp.raise_for_status()
    with open(os.path.basename(uri), "wb") as file:
        file.write(resp.content)
