#!/usr/bin/env python2

# Filename: artiPurgeTool.py
# Classification: UNCLASSIFIED
#
# Copyright (C) 2018 ViaSat, Inc.
# All rights reserved.
# The information in this software is subject to change without notice and
# should not be construed as a commitment by ViaSat, Inc.
#
# ViaSat Proprietary
# The Proprietary Information provided herein is proprietary to ViaSat and
# must be protected from further distribution and use.  Disclosure to others,
# use or copying without express written authorization of ViaSat, is strictly
# prohibited.

# pylint: disable=invalid-name
# (Pylint doesn't like the camel case name)

"""
Scans a directory in Artifactory for old files (by age, or max number of files sorted by age).
Deletes files older than the limits specified on the command line, and logs the paths to the deleted
files. Standalone python script expecting Artifactory credentials to be available in its environment.
"""

import os
import sys
import argparse
from datetime import datetime
import pytz
from dateutil import parser
import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth
#from gettext import gettext as _

API = "https://artifactory.viasat.com/artifactory/api/storage"
FILE_BASE = "https://artifactory.viasat.com/artifactory"
LIST_SUFFIX = "?list"
AUTH = HTTPBasicAuth(os.getenv('ARTI_USER'), os.getenv('ARTI_TOKEN'))
HEADER = {}
_ = argparse._

class MyFileType(argparse.FileType):
    """
    Corrects an oversight in the argparse FileType module where append mode is not valid for "-"
    see: https://github.com/python/cpython/blob/2.7/Lib/argparse.py argparse.FileType.__call__()
    see also: https://docs.python.org/2/library/argparse.html#filetype-objects
    I tried to make as few changes as possible
    """
    def __call__(self, string):
        #_ = argparse._
        if string == '-':
            if 'r' in self._mode:
                return sys.stdin
            elif 'w' in self._mode or 'a' in self._mode:
                return sys.stdout
            else:
                msg = _('argument "-" with mode %r') % self._mode
                raise ValueError(msg)
        try:
            return open(string, self._mode, self._bufsize)
        except IOError as e:
            message = _("can't open '%s': %s")
            raise argparse.ArgumentTypeError(message % (string, e))

def compare_files(file_a, file_b):
    """
    Compares 2 artifactory files by age field,truncated to the second.
    Returns 0 if equal age, <0 of file_a is older, >0 if file_b is older,
    :param file_a: First element to compare
    :param file_b: Second element to compare
    :return: file_b's age minus file_a's age truncated to an integer
    """
    return int(file_b["age"] - file_a["age"])

def parse_command_args():
    """
    Parses command line arguments to script
    :return: parsed arguments
    """
    global HEADER

    argparser = argparse.ArgumentParser(description="Deletes old files from an Artifactory folder.")
    argparser.add_argument("path", help="Artifactory path to use")
    argparser.add_argument("-a", "--max-age", help="Max age of artifacts to keep", default=-1, type=int)
    argparser.add_argument("-c", "--max-count", help="Max number of artifacts to keep", default=-1, type=int)
    argparser.add_argument("-n", "--dry-run", action="store_true", help="Prints list of files to delete and exits")
    argparser.add_argument("-o", "--output", type=MyFileType('a'), default=None,
                           help="File to append list of deleted files to")
    argparser.add_argument("-w", "--whitelist", type=MyFileType('r'), default=None,
                           help="File listing artifact filenames to ignore, one per line, no slashes")

    args = argparser.parse_args()

    if not os.getenv('ARTI_USER') or not os.getenv('ARTI_TOKEN'):
        sys.stderr.write("ARTI_USER or ARTI_TOKEN environvent variable(s) not set. "\
                         "These are required for artifactory authentication.\n")
        sys.stderr.write("ARTI_USER should be set to artifactory username.\n")
        sys.stderr.write("ARTI_TOKEN should be set to artifactory API key.\n")
        sys.stderr.flush()
        exit(1)

    with open(os.path.expanduser("~/.curl_artifactory")) as f:
        for line in f.readlines():
            if line.startswith("header"):
                HEADER = {"Authorization": "Bearer " + line.rsplit(" ", 1)[1].replace('"', '').strip()}
                break;

    if not HEADER:
        sys.stderr.write("Could not find header in ~/.curl_artifactory\n")
        sys.stderr.flush()
        exit(1)

    return args

def get_artifact_list(path):
    """
    Gets list of files in artifactory folder by URI and modification date
    :param path: path within artifactory to scan
    :return: list of files with relative uri and modification date
    """
    resp = requests.get(API+path+LIST_SUFFIX+'&listFolders=1', headers=HEADER)
    resp.raise_for_status()
    raw_list = resp.json()["files"]
    # Extract uri and date from each element of artifacts list and return as list of objects
    # ignore any folders encountered
    # https://www.jfrog.com/confluence/display/RTF/Artifactory+REST+API#ArtifactoryRESTAPI-FileList
    return [{"uri":x["uri"], "date":x["lastModified"]} for x in raw_list]
    # return [{"uri":x["uri"], "date":x["lastModified"]} for x in raw_list if not x["folder"]]

def get_index(max_age_days, max_count, artifacts):
    """
    Calculates cutoff index for deleting files
    :param max_age_days: Max age of retained files in days
    :param max_count: Max number of artifacts to keep
    :param artifacts: List of artifacts, each with "age" parameter
    :return: Index of first element to keep in date-sorted list
    """
    max_age_seconds = max_age_days * 60 * 60 * 24
    age_index = -1
    # Sorts artifacts by age, oldest to newest
    artifacts.sort(compare_files)
    if max_age_days >= 0:
        for i in range(0, len(artifacts)):
            if artifacts[i]["age"] > max_age_seconds:
                age_index = i
        age_index += 1
    if max_count < 0:
        count_index = -1
    else:
        count_index = len(artifacts) - max_count
    return max(0, age_index, count_index)

def delete_artifacts(path, files, simulate, log=None):
    """
    Deletes artifacts from artifactory
    :param path: Folder path within artifactory
    :param files: List of filenames (with preceding forward slashes) to delete
    :param simulate: Whether to simulate deleting or actually delete files
    :param log: File-like object to write delete log to, or None
    """
    rc = 0
    if simulate:
        if not files:
            print "Nothing to delete"
        for filepath in files:
            print "DELETE " + path + filepath
    else:
        print "deleting " + str(len(files)) + " artifacts..."
        for filepath in files:
            try:
                resp = requests.delete(FILE_BASE+path+filepath, headers=HEADER)
                resp.raise_for_status()
                if log is not None:
                    log.write(path+filepath+'\n')
            except HTTPError as err:
                try:
                    sys.stderr.write("ERROR: {}; Retrying\n".format(str(err)))
                    resp = requests.delete(FILE_BASE+path+filepath, headers=HEADER)
                    resp.raise_for_status()
                    if log is not None:
                        log.write(path+filepath+'\n')
                except HTTPError as err:
                    sys.stderr.write("ERROR: {}\n Skipping file\n".format(str(err)))
                    rc = 1
            if log is not sys.stdout:
                sys.stdout.write('.')  # Sort of progress bar
                sys.stdout.flush()
        if log is not sys.stdout:
            sys.stdout.write('\n')
    return rc

def main():
    """
    Main function. Orchestrates file deletion from Artifactory
    """
    args = parse_command_args()
    artifacts = get_artifact_list(args.path)
    now = datetime.now(pytz.utc)

    for artifact in artifacts:
        artifact["date"] = parser.parse(artifact["date"])
        artifact["age"] = (now - artifact["date"]).total_seconds()

    index = get_index(args.max_age, args.max_count, artifacts)
    # Get list of URIs from list of artifacts before cutoff index
    obsolete = [x["uri"] for x in artifacts[0:index]]

    if args.whitelist is not None:
        for artifact in args.whitelist.readlines():
            try:
                obsolete.remove("/"+artifact.strip())
            except ValueError:  # If artifact not in list to delete
                pass

    result = delete_artifacts(args.path, obsolete, args.dry_run, args.output)
    return result

if __name__ == '__main__':
    main()

