/*---------------------------------------------------------------
 *
 * Classification:  UNCLASSIFIED
 *
 * File:  modem_key_util.h
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

#define MAX_LEN 128

#ifdef DEBUG
#define mkaDebug(fmt ...) printf(fmt)
#else
#define mkaDebug(fmt ...)
#endif

/*
 * REMOTE:  File name points to path at remote site. ( i.e. user@ip://tmp/file )
 * VALID:   File name points to an valid local path at the JB
 * INVALID: File name points to an invalid local path at the JB
 */
typedef enum
{
    REMOTE,
    VALID,
    INVALID
} ftype;

bool is_valid_key_path(const char *key_path);
ftype is_valid_src(const char *src);
ftype is_valid_dst(const char *dst);
ftype is_valid_local(const char *dst, const bool is_src);
bool get_dst_fullpath(const char *src, const char *dst, char *dst_fpath);

