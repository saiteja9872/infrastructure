ssh_src = modem_key_ssh.c modem_key_util.c
ssh_obj = $(ssh_src:.c=.o)

scp_src = modem_key_scp.c modem_key_util.c
scp_obj = $(scp_src:.c=.o)

include = modem_key_util.h

CC := gcc
CFLAGS := -Wall -O2

all: modem_key_ssh modem_key_scp

modem_key_ssh: $(ssh_obj)
	       $(CC) -o $@ $^

modem_key_scp: $(scp_obj)
	       $(CC) -o $@ $^

clean:
	rm -f *.o modem_key_ssh modem_key_scp


