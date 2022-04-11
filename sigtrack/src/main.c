#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <getopt.h>
#include <string.h>
#include "stringlist.h"
#include "rangelist.h"
#include "esig.h"

///////////////////////////////////////////////////////////////////////////////
//
// Copyright 2015-2022, Population Health Research Institute
// Copyright 2015-2022, Martin Renters
//
// This file is part of the DataFax Toolkit.
//
// The DataFax Toolkit is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// The DataFax Toolkit is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with The DataFax Toolkit.  If not, see <http://www.gnu.org/licenses/>.
//
///////////////////////////////////////////////////////////////////////////////

#define VERSION	"3.0.6"

int yyparse(void);
int get_config_error_cnt(void);

eSigConfig *esig_config_head = 0;

FILE *yyin;

/////////////////////////////////////////////////////////////////////////////
// PROCESS_INPUT - Process Audit trail input
/////////////////////////////////////////////////////////////////////////////
void process_input(eSigNodeTree *tree, sqlite3 *db)
{
	StringList *sl = sl_alloc(32);
	char txn[128], last_txn[128];
	char *nvalue;
	eSigConfig *esc;
	eSigNode *esn, *esn0;
	int rec_status;
	TransactionID txn_id = 0;

	Plate plate;
	Patient id;
	Visit visit;
	Field field;

	// Mark that we don't currently have a signing transaction in progress
	last_txn[0] = 0;
	while (!sl_read(sl, stdin, '|')) {
		// Skip QCs and Reasons if we find them;
		if (atoi(sl_value(sl, AUDITREC_FIELDREF))) continue;

		field = atoi(sl_value(sl, AUDITREC_FIELDPOS));

		// Skip raster, study and keys
		if ((field > 2) && (field <= 7)) continue;

		rec_status = atoi(sl_value(sl, AUDITREC_STATUS));
		id = atoll(sl_value(sl, AUDITREC_PID));
		visit = atoi(sl_value(sl, AUDITREC_VISIT));
		plate = atoi(sl_value(sl, AUDITREC_PLATE));

		// Create a transaction ID based on timestamp, user and keys
		snprintf(txn, sizeof(txn), "%s|%s|%s|%lld|%d|%d",
			sl_value(sl, AUDITREC_DATE),
			sl_value(sl, AUDITREC_TIME),
			sl_value(sl, AUDITREC_USER),
			id, visit, plate);

		if (strcmp(txn, last_txn) != 0) {
			txn_id++;
			strncpy(last_txn, txn, sizeof(txn));
		}

		// Look for the eSig configuration entries for this record
		esc = esc_config_head;
		for (esc = esc_config_head; esc; esc = esc->next) {
			// If this config doesn't apply, continue to next
			if ((esc->plate != plate) ||
				(!rl_contains(esc->visits, visit)) ||
				(rl_contains(esc->ignore_fields, field)))
				continue;

			// Allocate a potential new esignature node
			esn = esn_alloc(id, visit, esc);

			// Try to insert it into the tree
			esn0 = RB_INSERT(eSigNodeTree, tree, esn);

			// See whether it already existed
			if (esn0) {
				esn_free(esn);	// Free temporary node
				esn = esn0;	// Use node in tree
			} else {		// Fill in signature field slots
				esn_alloc_sigfields(esn);
			}

			// If this record contains signature fields,
			// mark it as now having been seen
			if ((plate == esc->sig_plate) && (rec_status != 0)) {
				esn_sig_rec_seen(esn);
			}

			// Now that we have the signature node, check
			// whether we are signing or changing data
			if (	(plate == esc->sig_plate) &&
				rl_contains(esc->sig_fields, field)) {

				// Is a signature field filled out?
				// If it is we signed, otherwise we unsigned.
				nvalue = sl_value(sl, AUDITREC_NEWVALUE);
				if (nvalue && *nvalue) {
					esn_sign(esn, sl, field, txn_id);
					db_write_signature(db, esn, txn_id);
					esn_free_signed_values(esn, txn_id);
				} else {
					esn_unsign(esn, field);
				}
			} else {
				// Save data changes
				esn_datachange(esn, sl, plate, field, txn_id);

				// If we have some data changes that belong
				// to this signing transaction, make sure
				// we update DB
				if (esn->txn_id == txn_id)
					db_update_signature_value(db, esn,
					     plate, field, sl);
			}

		}
	}
	sl_free(sl);
}

/////////////////////////////////////////////////////////////////////////////
// WRITE_DRF - Write a DRF of signatures that need re-signing
/////////////////////////////////////////////////////////////////////////////
int write_drf(char *fn, eSigNodeTree *tree)
{
	FILE *fp;
	eSigNode *esn;

	if ((fp = fopen(fn, "w")) == NULL) {
		fprintf(stderr, "unable to create/open DRF output file %s\n", fn);
		return -1;
	}

	// Dump the tree
	RB_FOREACH(esn, eSigNodeTree, tree) {
		if ((esn->status.signatureStatus == SIG_INVALIDATED) ||
		    (	(esn->status.signatureStatus == SIG_COMPLETE) &&
			(esn->status.recStatus == RECORD_NORMAL) &&
			(esn->status.changeStatus == CHANGE_DECLINED))) {
			fprintf(fp, "%lld|%d|%d\n",
				esn->id, esn->visit, esn->config->sig_plate);
		}
	}
	fclose(fp);
	return 0;
}

/////////////////////////////////////////////////////////////////////////////
// MAIN
/////////////////////////////////////////////////////////////////////////////
int main(int argc, char *argv[])
{
	int opt;
	int option_index;
	int allow_signer_changes = 0;
	int resign_at_final = 0;
	int arrived_only = 0;
	int sdv_mode = 0;
	char *config, *drf, *xls;
	char *studydir = 0;
	char *path;
	char *exclusion_file=0;
	char *priority_file = 0;
	struct centers centers;
	struct countries countries;
	sqlite3 *db = 0;
	eSigNodeTree esig_tree = RB_INITIALIZER(&esig_tree);

	static struct option long_options[] = {
		{"config", 1, 0, 'c'},
		{"drf", 1, 0, 'd'},
		{"xls", 1, 0, 'x'},
		{"allow-signer-changes", 0, 0, 'a'},
		{"arrived-only", 0, 0, 'A'},
		{"resign-when-final", 0, 0, 'F'},
		{"sdv", 0, 0, 'S'},
		{"studydir", 1, 0, 's'},
		{"db", 1, 0, 'D'},
		{"exclusion", 1, 0, 'E'},
		{"priority-file", 1, 0, 'P'},
		{"version", 0, 0, 'v'}
	};

	STAILQ_INIT(&centers);
	STAILQ_INIT(&countries);

	config = drf = xls = 0;
	while ((opt = getopt_long(argc, argv, "Aac:d:FSx:v", long_options,
		&option_index)) != -1) {
		switch(opt) {
		case 'A':
			arrived_only = 1;
			break;
		case 'a':
			allow_signer_changes = 1;
			break;
		case 'c':
			config = optarg;
			if (!(yyin = fopen(config, "r"))) {
				fprintf(stderr, "unable to open configuration fle '%s'\n", config);
				exit(2);
			}
			break;
		case 's':
			studydir = optarg;
			break;
		case 'd':
			drf = optarg;
			break;
		case 'D':
			db = db_open(optarg);
			break;
		case 'F':
			resign_at_final = 1;
			break;
		case 'S':
			sdv_mode = 1;
			break;
		case 'x':
			xls = optarg;
			break;
		case 'E':
			exclusion_file = optarg;
			break;
		case 'P':
			priority_file = optarg;
			break;
		case 'v':
			printf("Signature Tracking Tool, Version: %s\n", VERSION);
			exit(0);
		default:
			fprintf(stderr, "usage: %s [-c config] [-d drf]\n",
				argv[0]);
			break;
		}
	}

	// Make sure we have a configuration file to read.
	if (!config) {
		fprintf(stderr, "%s: no configuration file specified.\n",
			argv[0]);
		exit(2);
	}

	// Load exclusion file if specified
	if (exclusion_file) {
		load_exclusions(exclusion_file);
	}

	yyparse();
	if (get_config_error_cnt()) {
		fprintf(stderr, "Program terminating due to errors in configuration file\n");
		exit(2);
	}

	if (priority_file) {
		esc_priority_file(esc_config_head, priority_file);
		exit(0);
	}


	//esc_print(esc_config_head);

	process_input(&esig_tree, db);

	//////////////////////////////////////////////////////////////////
	// If allow_signer_changes is enabled, allow a signer to make
	// changes to their data without requiring re-signing
	//////////////////////////////////////////////////////////////////
	evaluate_tree(&esig_tree, allow_signer_changes, resign_at_final);

	//////////////////////////////////////////////////////////////////
	// If drf file requested, write it out now
	//////////////////////////////////////////////////////////////////
	if (drf) {
		write_drf(drf, &esig_tree);
	}

	if (studydir) {
		// Load centers
		path = malloc(strlen(studydir)+strlen("/lib/DFcenters")+1);
		sprintf(path, "%s/lib/DFcenters", studydir);
		load_centers(path, &centers);
		free(path);

		// Load countries
		path = malloc(strlen(studydir)+strlen("/lib/DFcountries")+1);
		sprintf(path, "%s/lib/DFcountries", studydir);
		load_countries(path, &countries);
		free(path);
	}

	//////////////////////////////////////////////////////////////////
	// If xls file requested, write it out now
	//////////////////////////////////////////////////////////////////
	if (xls) {
		write_xls(xls, &esig_tree, arrived_only, sdv_mode,
			&centers, &countries);
	}

	db_close(db);

	exit(0);
}
