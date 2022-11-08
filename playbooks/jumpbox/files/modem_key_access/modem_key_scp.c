/*---------------------------------------------------------------
 *
 * Classification:  UNCLASSIFIED
 *
 * File:  modem_key_ssh.c
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
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sysexits.h>
#include <ctype.h>
#include <sys/wait.h>
#include "modem_key_util.h"

void print_usage(void)
{
   printf("Usage: modem_key_scp -i <key file path> <source> <destination> \n");
}

int main(int argc, char *argv[])
{
   int opt;
   extern char *optarg;
   extern int optind;
   pid_t pid;

   char *key_path = NULL;
   char *caller_usrname = NULL;
   char *src;
   char *dst;

   char *newargv[] = { "scp", "-i", NULL, NULL, NULL, NULL };
   char *newenviron[] = { NULL };

   while ((opt = getopt(argc, argv, "c:hi:")) != EOF)
   {
      switch (opt)
      {
       case 'c':
          {
	     caller_usrname = optarg;
             break;
          }
       case 'i':
          {
             key_path = optarg;
             break;
          }
       case 'h':
       default:
	 print_usage();
	 exit(EXIT_FAILURE);
      }
   }

   if ((key_path == NULL) || (caller_usrname == NULL) || (argc - optind) < 2)
   {
      print_usage();
      exit(EXIT_FAILURE);
   }

   if ( !is_valid_key_path(key_path) )
   {
      printf("Invalid key file path\n");
      exit(EXIT_FAILURE);
   }

   src = argv[argc-2];
   if ( INVALID == is_valid_src(src) )
   {
      printf("Invalid src file path %s\n", src);
      exit(EXIT_FAILURE);
   }

   dst = argv[argc-1];

   if ( INVALID == is_valid_dst(dst) )
   {
      printf("Invalid dst file path\n");
      exit(EXIT_FAILURE);
   }

   newargv[2] = key_path;
   newargv[3] = src;
   newargv[4] = dst;

   pid = fork();

   if(pid < 0) {
     mkaDebug("Failed to fork child process \n");
     exit(EXIT_FAILURE);
   }
   else if(pid == 0) {
     printf("connecting to host ... \n");
     execve("/usr/bin/scp", newargv, newenviron);
     perror("execve");   /* execve() returns only on error */
     printf("Value of errno: %d\n ", errno);
     printf("The error message is : %s\n", strerror(errno));
     exit(EXIT_FAILURE);
   }
   else {
     int waitstatus, i;
     ftype ret;
     
     wait(&waitstatus);
     i = WEXITSTATUS(waitstatus);

     if (i == 0) {
       ret = is_valid_local(dst, false);
       if ( VALID == ret ) {
	 char *pnewargv[] = {"/usr/bin/sudo", "/bin/chown", "-R", NULL, NULL, NULL };
	 char *pnewenviron[] = { NULL };
	 char usr_grp[128];
	 char dst_fpath[256];

         if ( !get_dst_fullpath(src, dst, dst_fpath) ) {
           printf("Error: Invalid dst file name\n");
           exit(EXIT_FAILURE);
         }

	 sprintf(usr_grp,"%s:cloud_users",caller_usrname);
	 pnewargv[3] = usr_grp;
	 pnewargv[4] = dst_fpath;
	 mkaDebug("Parent: Changing file %s ownership to %s:cloud_users \n",dst_fpath,caller_usrname);
	 execve("/usr/bin/sudo", pnewargv, pnewenviron);
	 perror("execve");   /* execve() returns only on error */
	 printf("Value of errno: %d\n ", errno);
	 printf("The error message is : %s\n", strerror(errno));
	 exit(EXIT_FAILURE);
       }
       else {
	 if ( REMOTE != ret ) {
	   printf("Parent: Failed with invalid dst_fpath %s \n",dst);
	   exit(EXIT_FAILURE);
	 }
       }
     }
     else {
       mkaDebug("Parent: Failed and i=%d, waitstatus=%d. \n",i,waitstatus);
       exit(EXIT_FAILURE);
     }
   }
   exit(EXIT_SUCCESS);
}

