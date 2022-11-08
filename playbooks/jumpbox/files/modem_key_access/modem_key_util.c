/*---------------------------------------------------------------
 *
 * Classification:  UNCLASSIFIED
 *
 * File:  modem_key_util.c
 *
 * Copyright (C) 2022 ViaSat, Inc.
 * All rights reserved.
 * The information in this software is subject to change without notice and
 * should not be construed as a commitment by ViaSat, Inc.
 *
 * Viasat Proprietary
 * The Proprietary Information provided herein is proprietary to ViaSat and
 * must be protected from further distribution and use.  Disclosure to others,
 * use or copying without express written authorization of ViaSat, is strictly
 * prohibited
 *
 * $ProjectHeader
 *-------------------------------------------------------------*/
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <pwd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <limits.h>
#include "modem_key_util.h"

/*
 * convert path to full path
 */
static bool fullpath(const char *path, char *fpath)
{
  char *res = realpath(path, fpath);
  if (res) {
    mkaDebug("Full path is at %s.\n", fpath);
    return true;
  } else {
    mkaDebug("Failed to find full path, Error: %s.\n", strerror(errno));
    return false;
  }
}

/*
 * Check the conditions
 * 1. the key is under /home/sshproxy/.ssh/ 
 * 2. the current caller is the owner of the key
 * 3. the key has access permission -r--------
 */
bool is_valid_key_path(const char *key_path)
{
  register struct passwd *pw;
  register uid_t uid;
  char full_key_path[PATH_MAX];

  struct stat st;
  mode_t owner, group, other;
  bool valid_key = false;
  
  if (( key_path == NULL ) ||
      !fullpath(key_path, full_key_path)) {
    mkaDebug("Error: invalid key path: %s\n",key_path);
    return false;
  }

  if (strstr(full_key_path, "/home/sshproxy/.ssh/") == NULL) {
    mkaDebug("Error: invalid full key path: %s\n",full_key_path);
    return false;
  }

  uid = geteuid();
  pw = getpwuid(uid);
  if ( pw ) {
    if (strncmp(pw->pw_name, "root", sizeof("root")) == 0) {
      mkaDebug("It's SU\n");
      return true;
    }
    mkaDebug("user name: %s and UID: %u\n",pw->pw_name, (unsigned)uid);
  }
  else {
    mkaDebug ("Error: cannot find username for UID %u\n", (unsigned)uid);
    return false;
  }

  if(lstat(full_key_path, &st) < 0)
  {
    mkaDebug("Error: Couldn't open file.\n");
    return false;
  }

  if (uid != st.st_uid) {
    mkaDebug("you are not owner of key file\n");
    return false;
  }

  owner = st.st_mode & S_IRWXU;
  group = st.st_mode & S_IRWXG;
  other = st.st_mode & S_IRWXO;

  valid_key = owner & S_IRUSR ? true : false;
  valid_key = owner & S_IWUSR ? false : valid_key;
  valid_key = owner & S_IXUSR ? false : valid_key;

  valid_key = group & S_IRGRP ? false : valid_key;
  valid_key = group & S_IWGRP ? false : valid_key;
  valid_key = group & S_IXGRP ? false : valid_key;

  valid_key = other & S_IROTH ? false : valid_key;
  valid_key = other & S_IWOTH ? false : valid_key;
  valid_key = other & S_IXOTH ? false : valid_key;

  mkaDebug("file %s access is %s\n", full_key_path, valid_key ? "valid" : "invalid");
  return valid_key;
}

/*
 * get file name
 * i.e. user@IP://tmp/test.txt
 *      user@IP://tmp/test?.txt
 *      user@IP://tmp/test*
 */
const char *get_file_name_from_path(const char *path)
{
  if ( path != NULL ) {
    for(size_t i = strlen(path);  i > 0; --i)
    {
      if ( path[i-1] == '/' ) {
	mkaDebug("%s: The file name is: %s with path %s \n",
	       __func__, &path[i], path);
	return &path[i];
      }
    }
  }
  return path;
}

/*
 * Check the conditions
 * 1. if it's local file, and
 * 2. can not be owned by sshproxy, and
 * 3. can not be in /home/sshproxy/.ssh/ if it's local file, and
 * 4. the local file uid can not be sshproxy user uid
 */
ftype is_valid_local(const char *fpath, const bool is_src)
{
  register struct passwd *pw;
  register uid_t uid;
  struct stat st;
  bool is_sshproxy_user = false;
  
  char full_file_path[PATH_MAX];
  const char *file_path = fpath;

  char userName[16], remain[256];
  int ip1, ip2, ip3, ip4;

  if ( fpath == NULL ) {
    mkaDebug("Error: invalid fpath path: %s\n",fpath);
    return INVALID;
  }

  /* Check for local fpath */
  if ( sscanf(fpath, "%[^@]@%d.%d.%d.%d%[^\n]\n",
	      userName, &ip1, &ip2, &ip3, &ip4, remain) == 6) {

    /* check for local interface */
    if ((ip1 != 127) && (ip2 != 0) && (ip3 != 0) && (ip4 != 1)) {
      const char *remote_file_name = NULL;
      mkaDebug("Remote Source: %s@%d.%d.%d.%d%s\n",
	       userName, ip1, ip2, ip3, ip4, remain);

      /* No support remote multiple files (i.e. *, or ?)
       * for now due to ownership change limitation */
      remote_file_name = get_file_name_from_path(fpath);
      if ( (strstr(remote_file_name, "?") != NULL) ||
	   (strstr(remote_file_name, "*") != NULL) ) {
	return INVALID;
      }
      return REMOTE;
    }
    /* point to the file path after 127.0.0.1:/ */
    file_path = strstr(fpath, ":/");
    if (file_path == NULL) {
      mkaDebug("Invalid fpath: %s\n", fpath);
      return INVALID;
    }
    file_path = file_path + 1;
  }

  if (is_src) {
    /* convert to full path */
    if (!fullpath(file_path, full_file_path)) {
      mkaDebug("Error: invalid file_path path: %s\n",file_path);
      return INVALID;
    }
  }

  /* validate user */
  uid = geteuid();
  pw = getpwuid(uid);
  if ( pw ) {
    if (strncmp(pw->pw_name, "root", sizeof("root")) == 0) {
      mkaDebug("It's SU\n");
      return VALID;
    }
    if (strncmp(pw->pw_name, "sshproxy", sizeof("sshproxy")) == 0) {
      is_sshproxy_user = true;
      mkaDebug("It's sshproxy user\n");
    }
    mkaDebug("user name: %s and UID: %u\n",pw->pw_name, (unsigned)uid);
  }
  else {
    mkaDebug("Error: Can't find user name with UID %u",(unsigned)uid);
    return INVALID;
  }

  /* get file attributes */
  if (is_src) {
    if (lstat(full_file_path, &st) < 0)
      {
	mkaDebug("Error: open fpath file %s.\n",fpath);
	return INVALID;
      }
  }

  /* do not allow user sshproxy file(s) be copied */
  if (is_sshproxy_user && (uid == st.st_uid)) {
    mkaDebug("Error: fpath file %s access permission deny \n",fpath);
    return INVALID;
  }

  /* It's not sshproxy user, check for wrong doing */ 
  if (( strstr(fpath, "/home/sshproxy/.ssh") != NULL ) ||
      ( strstr(fpath, "/home/root/.ssh") != NULL )) {
    mkaDebug("Error: Suspicious fpath path %s\n", fpath);
    return INVALID;
  }
  return VALID;
}

/*
 * Check if the src is a valid local file path
 */
ftype is_valid_src(const char *src)
{
  return(is_valid_local(src, true));
}

/*
 * Check if the dst is a valid local file path
 */
ftype is_valid_dst(const char *dst)
{
  return(is_valid_local(dst, false));
}

static int is_directory(const char *path) {
   struct stat statbuf;
   if (stat(path, &statbuf) != 0)
       return 0;
   return S_ISDIR(statbuf.st_mode);
}

/*
 * Check and form local dst file, which is used in the file ownership change.
 *
 * It has already verified the dst is local filr before coming to here. 
 * 1. checking if it's a valid combination of src and dst, and
 * 2. form a valid local path for "sudo chown -R user:cloud_users dst_fpath"
 *    i.e. src=test.txt and dst=.  ==> /home/username/test.txt
 *         src=test.txt and dst=~/  ==> /home/username/test.txt
 *         src=test.txt and dst=~/tmp  ==> /home/username/tmp/test.txt
 */
bool get_dst_fullpath(const char *src, const char *dst, char *dst_fpath)
{
  const char *psrc_file_name;

  if ( (dst == NULL) || (src == NULL) ||
       (dst_fpath == NULL) ) {
    mkaDebug("Error: Invalid parameters \n");
    return false;
  }

  if ( !fullpath(dst, dst_fpath) ) {
    mkaDebug("Error: Failed to get dst (%s) fullpath\n",dst);
    return false;
  }

  psrc_file_name = get_file_name_from_path(src);
  if ( is_directory(dst_fpath) ) {
    strcat(dst_fpath, "/");
    strcat(dst_fpath, psrc_file_name);
    mkaDebug("%s: dst_fpath = %s is a DIR\n",__func__,dst_fpath);
  }
  else {
    mkaDebug("%s: dst_fpath = %s is a FILE\n",__func__,dst_fpath);
  }
  return true;
}
