#ifndef LCN_SCANNER_H_
#define LCN_SCANNER_H_

struct lcn_entry
{
	unsigned short int nid;
	unsigned short int tsid;
	unsigned short int sid;
	unsigned short int lcn;
	struct lcn_entry *next;
};

void demuxer_open ();
void demuxer_close ();
struct lcn_entry *get_lcn ();
void lcn_entry_clean (struct lcn_entry *value);

#endif /* LCN_SCANNER_H_ */
