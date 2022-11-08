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
#include "modem_key_util.h"

void print_usage(void)
{
   printf("Usage: modem_key_ssh -i <key file path> <user>@<ip> \n");
}

int main(int argc, char *argv[])
{
   int opt;
   extern char *optarg;
   extern int optind;
   
   char *key_path=NULL;
   char *user_and_ip;

   char *newargv[] = { "ssh", "-i", NULL, NULL, NULL, NULL };
   char *newenviron[] = { NULL };

   while ((opt = getopt(argc, argv, "hi:")) != EOF)
   {
      switch (opt)
      {
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

   if ((key_path == NULL) || (argc - optind) < 1)
   {
      print_usage();
      exit(EXIT_FAILURE);
   }
   
   if ( !is_valid_key_path(key_path) )
   {
      printf("Invalid key file path\n");
      exit(EXIT_FAILURE);
   }

   user_and_ip = argv[argc-1];
   newargv[2] = key_path;
   newargv[3] = user_and_ip;

   printf("connecting ... %s \n", user_and_ip);
   execve("/usr/bin/ssh", newargv, newenviron);
   perror("execve");   /* execve() returns only on error */
   printf("Value of errno: %d\n ", errno);
   printf("The error message is : %s\n", strerror(errno));
   exit(EXIT_FAILURE);
}

