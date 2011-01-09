#include <stdio.h>
#include <string.h>
#include <linux/dvb/dmx.h>
#include <sys/ioctl.h>
#include <sys/poll.h>
#include <fcntl.h>
#include <stdlib.h>

#include "lcn_scanner.h"

struct lcn_entry *parse_lcn (unsigned char *data, unsigned int length)
{
	struct lcn_entry *ret = NULL;
	struct lcn_entry *cur = NULL;
	unsigned char section_length = data[2];
	unsigned char network_description_length = data[9];
	unsigned short int tsid = (data[network_description_length+12] << 8) | data[network_description_length + 13];
	unsigned short int nid = (data[network_description_length+14] << 8) | data[network_description_length + 15];
	unsigned char offset = network_description_length + 18;

	while (offset < length-3)
	{
		unsigned char descriptor_tag = data[offset];
		unsigned char descriptor_length = data[offset+1];
		if ((int)descriptor_length + (int)offset > length)	// we are reading over the table?
			break;

		offset += 2;
		//printf ("lcn_scanner: offset %d\n", offset);
		//printf ("lcn_scanner: descriptor_tag 0x%x\n", descriptor_tag);
		//printf ("lcn_scanner: descriptor_length %d\n", descriptor_length);
		if (descriptor_tag == 0x83)
		{
			int offset2;
			for (offset2=offset; offset2 < offset+descriptor_length; offset2+=4)
			{
				if (ret == NULL)
				{
					ret = malloc (sizeof(struct lcn_entry));
					ret->next = NULL;
					cur = ret;
				}
				else
				{
					cur->next = malloc (sizeof (struct lcn_entry));
					cur->next->next = NULL;
					cur = cur->next;
				}
				cur->nid = nid;
				cur->tsid = tsid;
				cur->sid = (data[offset2] << 8) | data[offset2 + 1];
				cur->lcn = ((data[offset2+2] & 0x3) << 8) | data[offset2 + 3];
				printf ("lcn_scanner: NID 0x%x - TSID 0x%x - SID 0x%x - LCN %d\n", cur->nid, cur->tsid, cur->sid, cur->lcn);
			}
		}
		offset += descriptor_length;
	}

	return ret;
}

struct pollfd PFD[256];
struct dmx_sct_filter_params params;

void demuxer_open ()
{
	PFD[0].fd = open ("/dev/dvb/adapter0/demux0", O_RDWR|O_NONBLOCK);
	PFD[0].events = POLLIN;
	PFD[0].revents = 0;

	memset (&params, 0, sizeof (params));
	params.pid = 0x10;
	params.timeout = 10000;
	params.flags = DMX_CHECK_CRC;

	if (ioctl (PFD[0].fd, DMX_SET_FILTER, &params) < 0)
		printf ("lcn_scanner: error setting filter\n");

	printf ("lcn_scanner: demuxer opened\n");
}

void demuxer_close ()
{
	close (PFD[0].fd);
	printf ("lcn_scanner: demuxer closed\n");
}

struct lcn_entry *get_lcn ()
{
	struct lcn_entry *ret = NULL;
	unsigned char buf[4096];	// 4K buffer size
	int size = 0;

	if (ioctl (PFD[0].fd, DMX_START) < 0)
	{
		printf ("lcn_scanner: error starting demuxer\n");
		goto error;
	}

	printf ("lcn_scanner: polling...\n");
	if (poll (PFD, 1, 10000) > 0)
	{
		printf ("lcn_scanner: poll ok\n");
		if (PFD[0].revents & POLLIN)
			size = read (PFD[0].fd, buf, sizeof (buf));

		printf ("lcn_scanner: read %d bytes\n", size);
		if (size > 0 && buf[0] == 0x40)
			ret = parse_lcn(buf, size);
	}
	else
		printf ("lcn_scanner: poll error\n");

	if (ioctl (PFD[0].fd, DMX_STOP) < 0)
		printf ("lcn_scanner: error stopping demuxer\n");

error:
	return ret;
}

void lcn_entry_clean (struct lcn_entry *value)
{
	while (value != NULL)
	{
		struct lcn_entry *tmp = value;
		value = value->next;
		free (tmp);
	}
}

/*
int main (int argc, char **argv)
{
	demuxer_open ();
	struct lcn_entry *test = get_lcn ();
	while (test != NULL)
	{
		printf ("OK NID: 0x%x TSID: 0x%x SID: 0x%x - %d\n", test->nid, test->tsid, test->sid, test->lcn);
		test = test->next;
	}
	lcn_entry_clean (test);
	demuxer_close ();
	return 0;
}
*/
