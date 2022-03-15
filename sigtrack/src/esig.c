#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
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

/////////////////////////////////////////////////////////////////////////
// eSignature Support Functions
//
// Author: Martin Renters, Oct, 2015
/////////////////////////////////////////////////////////////////////////

/////////////////////////////////////////////////////////////////////////
// fc_compare - Compare two FieldChange structures
/////////////////////////////////////////////////////////////////////////
int fc_compare(FieldChange *a, FieldChange *b)
{
	if (a->field < b->field) return -1;
	if (a->field > b->field) return 1;
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// cp_compare - Compare two coveredplate structures
/////////////////////////////////////////////////////////////////////////
int cp_compare(CoveredPlate *a, CoveredPlate *b)
{
	if (a->plate < b->plate) return -1;
	if (a->plate > b->plate) return 1;
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// esn_compare - Compare two esignode structures
/////////////////////////////////////////////////////////////////////////
int esn_compare(eSigNode *a, eSigNode *b)
{
	int a_field_low, b_field_low;

	// Sort by ID
	if (a->id < b->id) return -1;
	if (a->id > b->id) return 1;

	// then Visit
	if (a->visit < b->visit) return -1;
	if (a->visit > b->visit) return 1;

	// then Plate
	if (a->config->sig_plate < b->config->sig_plate) return -1;
	if (a->config->sig_plate > b->config->sig_plate) return 1;

	// and then first signature field
	a_field_low = rl_min(a->config->sig_fields);
	b_field_low = rl_min(b->config->sig_fields);
	if (a_field_low < b_field_low) return -1;
	if (a_field_low > b_field_low) return 1;

	// Must be equal
	return 0;
}

RB_GENERATE(FieldChangeTree, fieldchange, link, fc_compare);
RB_GENERATE(CoveredPlateTree, coveredplate, link, cp_compare);
RB_GENERATE(eSigNodeTree, esignode, link, esn_compare);

/////////////////////////////////////////////////////////////////////////
// esc_alloc - Create a new eSignature config object
/////////////////////////////////////////////////////////////////////////
eSigConfig *esc_alloc()
{
	static int serial = 0;
	eSigConfig *l = calloc(1, sizeof(eSigConfig));

	l->serial = ++serial;
	return l;
}

/////////////////////////////////////////////////////////////////////////
// esc_free - Free an eSigConfig
/////////////////////////////////////////////////////////////////////////
void esc_free(eSigConfig *l)
{
	eSigConfig *l0;

	while (l) {
		l0 = l->next;
		rl_free(l->ignore_fields);
		rl_free(l->visits);
		rl_free(l->sig_fields);
		if (l->name) free(l->name);
		free(l);
		l = l0;
	}
}

/////////////////////////////////////////////////////////////////////////
// esc_priority_file - Dump a priority_file
/////////////////////////////////////////////////////////////////////////
void esc_priority_file(eSigConfig *l, char *path)
{
	FILE *fp;
	RangeList *fields;
	long long low, high;

	fp = fopen(path, "w");
	if (!fp) {
		fprintf(stderr, "Unable to open '%s' for writing.\n", path);
		return;
	}
	while (l) {
		fields = l->ignore_fields;
		while (fields) {
			low = fields->min;
			high = fields->max;
			while (low <= high) {
				fprintf(fp, "%d|%lld|1\n", l->plate, low);
				low++;
			}
			fields = fields->next;
		}
		if (l->sig_plate == l->plate) {
			fields = l->sig_fields;
			while (fields) {
				low = fields->min;
				high = fields->max;
				while (low <= high) {
					fprintf(fp, "%d|%lld|3\n", l->plate, low);
					low++;
				}
				fields = fields->next;
			}
		}

		l = l->next;
	}
	fclose(fp);
}


/////////////////////////////////////////////////////////////////////////
// esc_print - Print an eSigConfig
/////////////////////////////////////////////////////////////////////////
void esc_print(eSigConfig *l)
{
	char *s;
	while (l) {
		s = rl_tostring(l->visits);
		printf("eSig %s for plate %d, visits %s ", l->name, l->plate, s);
		free(s);
		s = rl_tostring(l->ignore_fields);
		if (*s) {
			printf("(ignore fields %s) ", s);
		}
		free(s);
		s = rl_tostring(l->sig_fields);
		printf("is on plate %d fields %s.\n", l->sig_plate, s);
		free(s);
		l = l->next;
	}
}

/////////////////////////////////////////////////////////////////////////
// fc_alloc - Create a new FieldChange node object
/////////////////////////////////////////////////////////////////////////
FieldChange *fc_alloc(Field field)
{
	FieldChange *n = calloc(1, sizeof(FieldChange));

	n->field = field;
	n->status.recStatus = RECORD_NORMAL;
	n->status.changeStatus = CHANGE_ACCEPTED;
	n->status.signatureStatus = SIG_NONE;
	return n;
}

/////////////////////////////////////////////////////////////////////////
// fc_free - Destroy an FieldChange node object
/////////////////////////////////////////////////////////////////////////
void fc_free(FieldChange *n)
{
	if (n->desc) free(n->desc);
	if (n->old_value) free(n->old_value);
	if (n->new_value) free(n->new_value);
	if (n->who) free(n->who);
	if (n->date) free(n->date);
	if (n->time) free(n->time);
	free(n);
}

/////////////////////////////////////////////////////////////////////////
// cp_alloc - Create a new CoveredPlate node object
/////////////////////////////////////////////////////////////////////////
CoveredPlate *cp_alloc(Plate plate)
{
	CoveredPlate *n = calloc(1, sizeof(CoveredPlate));

	n->plate = plate;
	n->status.recStatus = RECORD_NORMAL;
	n->status.changeStatus = CHANGE_NONE;
	n->status.signatureStatus = SIG_NONE;
	n->field_change_count = 0;
	n->is_final = 0;
	RB_INIT(&n->changes);
	return n;
}

/////////////////////////////////////////////////////////////////////////
// cp_free_changes - Release a CoveredPlates node's FieldChanges
/////////////////////////////////////////////////////////////////////////
void cp_free_changes(CoveredPlate *n)
{
	FieldChange *p, *p0;
	for (p = RB_MIN(FieldChangeTree, &n->changes); p; p = p0) {
		// Save next pointer
		p0 = RB_NEXT(FieldChangeTree, &n->changes, p);
		RB_REMOVE(FieldChangeTree, &n->changes, p);
		fc_free(p);
	}
}

/////////////////////////////////////////////////////////////////////////
// cp_free - Destroy an CoveredPlate node object
/////////////////////////////////////////////////////////////////////////
void cp_free(CoveredPlate *n)
{
	cp_free_changes(n);
	free(n);
}

/////////////////////////////////////////////////////////////////////////
// esn_alloc - Create a new eSignature node object
/////////////////////////////////////////////////////////////////////////
eSigNode *esn_alloc(Patient id, Visit visit, eSigConfig *config)
{
	eSigNode *n = calloc(1, sizeof(eSigNode));

	n->id = id;
	n->visit = visit;
	n->config = config;
	n->status.recStatus = RECORD_NORMAL;
	n->status.changeStatus = CHANGE_NONE;
	n->status.signatureStatus = SIG_NONE;
	n->signer = 0;
	n->date = 0;
	n->time = 0;
	n->flags = 0;
	RB_INIT(&n->plates);
	return n;
}

void esn_sig_rec_seen(eSigNode *n)
{
	n->flags |= NODE_FLAG_RECSEEN;
}

int esn_was_sig_rec_seen(eSigNode *n)
{
	return n->flags & NODE_FLAG_RECSEEN;
}

void esn_alloc_sigfields(eSigNode *n)
{
	int i = 0;
	int v;
	RangeList *rl;

	if (n->sig_fields) return;	// Already allocated
	n->sig_fields = calloc(n->config->n_sig_fields, sizeof(eSigField));

	for (rl = n->config->sig_fields; rl; rl = rl->next) {
		for (v = rl->min; v <= rl->max; v++) {
			n->sig_fields[i].field = v;
			n->sig_fields[i].completed = 0;
			n->sig_fields[i].desc = 0;
			n->sig_fields[i].value = 0;
			i++;
		}
	}
}

/////////////////////////////////////////////////////////////////////////
// esn_free_coveredplates - Release an eSignature node's CoverPlates
/////////////////////////////////////////////////////////////////////////
void esn_free_coveredplates(eSigNode *n)
{
	CoveredPlate *p, *p0;
	for (p = RB_MIN(CoveredPlateTree, &n->plates); p; p = p0) {
		// Save next pointer
		p0 = RB_NEXT(CoveredPlateTree, &n->plates, p);
		RB_REMOVE(CoveredPlateTree, &n->plates, p);
		cp_free(p);
	}
}

/////////////////////////////////////////////////////////////////////////
// esn_free - Destroy an eSignature node object
/////////////////////////////////////////////////////////////////////////
void esn_free(eSigNode *n)
{
	int i;
	if (n->signer) free(n->signer);
	if (n->date) free(n->date);
	if (n->time) free(n->time);
	if (n->sig_fields) {
		for (i=0; i<n->config->n_sig_fields; i++) {
			if (n->sig_fields[i].desc)
				free(n->sig_fields[i].desc);
			if (n->sig_fields[i].value)
				free(n->sig_fields[i].value);
		}
		free(n->sig_fields);
	}
	esn_free_coveredplates(n);
	free(n);
}

/////////////////////////////////////////////////////////////////////////
// esn_get_state - Get a string representation of the state
/////////////////////////////////////////////////////////////////////////
char *esn_get_state(eSigNode *n, int sdv_mode)
{
    if (sdv_mode) {
	switch(n->status.signatureStatus) {
	case SIG_NONE:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			return "NEVER VERIFIED";
		case RECORD_ERROR:
			return "NEVER VERIFIED (ERROR REC)";
		case RECORD_LOST:
			return "NEVER VERIFIED (LOST REC)";
		case RECORD_DELETED:
			return "NEVER VERIFIED (DELETED REC)";
		}
		break;
	case SIG_INVALIDATED:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			return "RE-VERIFICATION REQD";
		case RECORD_ERROR:
			return "RE-VERIFICATION REQD (ERROR REC)";
		case RECORD_LOST:
			return "RE-VERIFICATION REQD (LOST REC)";
		case RECORD_DELETED:
			return "RE-VERIFICATION REQD (DELETED REC)";
		}
		break;
	case SIG_COMPLETE:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			switch(n->status.changeStatus) {
			case CHANGE_NONE:
				return "SDV OK";
			case CHANGE_ACCEPTED:
				return "ADMIN EXEMPTED RE-VERIFICATION";
			case CHANGE_DECLINED_ATFINAL:
				return "RE-VERIFICATION REQD WHEN FINAL";
			case CHANGE_DECLINED:
				return "RE-VERIFICATION REQD";
			}
			break;
		case RECORD_ERROR:
			return "SDV OK (ERROR REC)";
		case RECORD_LOST:
			return "SDV OK (LOST REC)";
		case RECORD_DELETED:
			return "SDV OK (DELETED REC)";
		}
		break;
	}
	return "STATE UNKNOWN";
    } else {
	switch(n->status.signatureStatus) {
	case SIG_NONE:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			return "NEVER SIGNED";
		case RECORD_ERROR:
			return "UNSIGNED ERROR RECORD";
		case RECORD_LOST:
			return "UNSIGNED LOST RECORD";
		case RECORD_DELETED:
			return "UNSIGNED DELETED RECORD";
		}
		break;
	case SIG_INVALIDATED:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			return "SIGNATURE REMOVED";
		case RECORD_ERROR:
			return "SIG. REMOVED, ERROR RECORD";
		case RECORD_LOST:
			return "SIG. REMOVED, LOST RECORD";
		case RECORD_DELETED:
			return "SIG. REMOVED, DELETED RECORD";
		}
		break;
	case SIG_COMPLETE:
		switch(n->status.recStatus) {
		case RECORD_NORMAL:
			switch(n->status.changeStatus) {
			case CHANGE_NONE:
				return "SIGNATURE OK";
			case CHANGE_ACCEPTED:
				return "ADMIN EXEMPTED RE-SIGN";
			case CHANGE_DECLINED_ATFINAL:
				return "RE-SIGN REQD WHEN FINAL";
			case CHANGE_DECLINED:
				return "RE-SIGN REQD";
			}
			break;
		case RECORD_ERROR:
			return "SIGNED IN ERROR";
		case RECORD_LOST:
			return "SIGNED, MARKED LOST";
		case RECORD_DELETED:
			return "DELETED SIGNED RECORDS";
		}
		break;
	}
	return "STATE UNKNOWN";
    }
}
/////////////////////////////////////////////////////////////////////////
// decode_value - Decodes a value with, if applicable, its coding label
/////////////////////////////////////////////////////////////////////////
char *decode_value(StringList *sl, int valuepos, int decodepos)
{
	char *value, *decode, *s;
	value = sl_value(sl, valuepos);
	decode = sl_value(sl, decodepos);
	if (decode && *decode) {
		s = malloc(strlen(value) + strlen(decode) + 2);
		sprintf(s, "%s=%s", value, decode);
	} else {
		s = strdup(value);
	}
	return s;
}

/////////////////////////////////////////////////////////////////////////
// esn_free_signed_values - Free any fields that the signature covers
/////////////////////////////////////////////////////////////////////////
void esn_free_signed_values(eSigNode *n, TransactionID txn_id)
{
	CoveredPlate *cp;

	// Is this our signing ID?
	if (n->txn_id != txn_id)
		return;

	// All field changes are accepted by signature
	// so delete the change records and mark record as normal again
	RB_FOREACH(cp, CoveredPlateTree, &n->plates) {
		cp_free_changes(cp);
		cp->status.recStatus = RECORD_NORMAL;
		cp->status.changeStatus = CHANGE_NONE;
	}
}
/////////////////////////////////////////////////////////////////////////
// esn_sign - An e-signature was executed
/////////////////////////////////////////////////////////////////////////
void esn_sign(eSigNode *n, StringList *sl, Field field, TransactionID txn_id)
{
	int i;
	int completed;

	// Find the signature field, mark it completed and
	// count total completed fields
	completed = 0;
	for (i=0; i < n->config->n_sig_fields; i++) {
		if (n->sig_fields[i].field == field) {
			n->sig_fields[i].completed = 1;
			update_string(&(n->sig_fields[i].desc),
				sl_value(sl, AUDITREC_FIELDDESC));
			update_string(&(n->sig_fields[i].value),
				sl_value(sl, AUDITREC_NEWVALUE));
		}

		if (n->sig_fields[i].completed)
			completed++;
	}

	// Check whether all signature fields are now completed
	if (completed != n->config->n_sig_fields) return;

	// Mark signature as complete in this transaction
	n->status.signatureStatus = SIG_COMPLETE;
	n->txn_id = txn_id;

	// Update who, date, time from audit trail data
	update_string(&n->signer, sl_value(sl, AUDITREC_USER));
	update_string(&n->date, sl_value(sl, AUDITREC_DATE));
	update_string(&n->time, sl_value(sl, AUDITREC_TIME));
}

/////////////////////////////////////////////////////////////////////////
// esn_unsign - A signature was removed
/////////////////////////////////////////////////////////////////////////
void esn_unsign(eSigNode *n, Field field)
{
	int i;

	// Find the signature field and mark it cleared
	for (i=0; i < n->config->n_sig_fields; i++) {
		if (n->sig_fields[i].field == field) {
			n->sig_fields[i].completed = 0;
			update_string(&n->sig_fields[i].value, "");
		}
	}

	// Can only unsign if we were signed
	if (n->status.signatureStatus == SIG_COMPLETE) 
		n->status.signatureStatus = SIG_INVALIDATED;

	n->txn_id = 0;
}

/////////////////////////////////////////////////////////////////////////
// esn_datachange - A data change was made to a field
/////////////////////////////////////////////////////////////////////////
void esn_datachange(eSigNode *n, StringList *sl, Plate plate, Field field,
		TransactionID txn_id)
{
	CoveredPlate *cp, *cp0;
	FieldChange *fc, *fc0;
	char *s;
	int rec_status;
	int rec_level;

	cp = cp_alloc(plate);
	cp0 = RB_INSERT(CoveredPlateTree, &n->plates, cp);
	if (cp0) {		// Already existed
		cp_free(cp);
		cp = cp0;
	}

	// Has this change been saved in error state?
	rec_status = atoi(sl_value(sl, AUDITREC_STATUS));
	rec_level = atoi(sl_value(sl, AUDITREC_LEVEL));
	cp->status.recStatus = RECORD_NORMAL;

	// Record whether the record is final or not
	if ((rec_status == 0) || (rec_status == 1))
		cp->is_final = 1;
	else
		cp->is_final = 0;

	if ((rec_status == 3) && (rec_level == 7)) {	// Pending + level 7
		if (n->status.signatureStatus != SIG_NONE)
			cp->status.changeStatus = CHANGE_DECLINED;
		cp->status.recStatus = RECORD_ERROR;
	}
	if (rec_status == 7) {			// Error
		if (n->status.signatureStatus != SIG_NONE)
			cp->status.changeStatus = CHANGE_DECLINED;
		cp->status.recStatus = RECORD_DELETED;
		cp_free_changes(cp);
	}
	if (rec_status == 0) {			// Lost
		if (n->status.signatureStatus != SIG_NONE)
			cp->status.changeStatus = CHANGE_DECLINED;
		cp->status.recStatus = RECORD_LOST;
		cp_free_changes(cp);
	}

	// If this is a change in our signing transaction, it counts towards
	// the changes covered by this signing
	if (txn_id == n->txn_id) return;

	// We don't track changes to status, validation at field level
	if (field < 7) return;

	fc = fc_alloc(field);
	fc0 = RB_INSERT(FieldChangeTree, &cp->changes, fc);
	if (fc0) {
		fc_free(fc);
		fc = fc0;
	} else {
		// Keep track of first old value and description
		s = decode_value(sl, AUDITREC_OLDVALUE, AUDITREC_OLDDECODE);
		update_string(&fc->old_value, s);
		free(s);
	}

	// Update field values
	update_string(&fc->who, sl_value(sl, AUDITREC_USER));
	update_string(&fc->date, sl_value(sl, AUDITREC_DATE));
	update_string(&fc->time, sl_value(sl, AUDITREC_TIME));
	update_string(&fc->desc, sl_value(sl, AUDITREC_FIELDDESC));
	s = decode_value(sl, AUDITREC_NEWVALUE, AUDITREC_NEWDECODE);
	update_string(&fc->new_value, s);
	free(s);

	// If this is a new field, check exclusions file and see whether
	// this is an exempted change
	if (!fc0 && is_excluded(sl)) {
		// Mark as exempted change
		fc->comment = "Administratively exempted";
		fc->status.changeStatus = CHANGE_ACCEPTED;
	} else {
		// Mark as unaccepted change
		fc->comment = 0;
		fc->status.changeStatus = CHANGE_DECLINED;
	}
}

/////////////////////////////////////////////////////////////////////////
// update_string - Update malloc'd or strdup'd string
/////////////////////////////////////////////////////////////////////////
void update_string(char **s, char *v)
{
	if (*s) free(*s);
	if (v)
		*s = strdup(v);
	else
		*s = 0;
}

//////////////////////////////////////////////////////////////////////////
// evaluate_tree - Evaluate nodes and mark changes
//////////////////////////////////////////////////////////////////////////
void evaluate_tree(eSigNodeTree * const tree, const int allow_signer_changes,
	const int resign_at_final)
{
	eSigNode *esn;
	CoveredPlate *cp;
	FieldChange *fc;

	RB_FOREACH(esn, eSigNodeTree, tree) {

		// Reset signature change status
		esn->status.changeStatus = CHANGE_NONE;

		RB_FOREACH(cp, CoveredPlateTree, &esn->plates) {
			// Push signature status down
			cp->status.signatureStatus =
				esn->status.signatureStatus;
			cp->field_change_count = 0;

			// Reset plate status
			//cp->status.changeStatus = CHANGE_NONE;

			RB_FOREACH(fc, FieldChangeTree, &cp->changes) {
				// Increment field count
				cp->field_change_count++;

				// Check if we want to defer signing until
				// record is final
				if (resign_at_final && !cp->is_final &&
					(fc->status.changeStatus ==
					  CHANGE_DECLINED))
					fc->status.changeStatus =
					  CHANGE_DECLINED_ATFINAL;

				// Push signature and record status down
				fc->status.recStatus = cp->status.recStatus;
				fc->status.signatureStatus =
					cp->status.signatureStatus;

				// Check if the signer changed the value
				if (allow_signer_changes && fc->who &&
					esn->signer &&
					strcmp(fc->who, esn->signer) == 0) {
					fc->comment = "Changed by Signer";
					fc->status.changeStatus =
						CHANGE_ACCEPTED;
				}

				// If field has higher priority change than
				// plate, propogate up to plate
				if (fc->status.changeStatus >
					cp->status.changeStatus)
					cp->status.changeStatus =
						fc->status.changeStatus;
			}

			// If this is the signature plate, propogate up
			// to signature itself
			if (esn->config->sig_plate == cp->plate) {
				esn->status.recStatus = cp->status.recStatus;
			}

			// If this plate's field changes have higher priority
			// than current signature, propogate up
			if (cp->status.changeStatus > esn->status.changeStatus)
				esn->status.changeStatus =
					cp->status.changeStatus;
		}
	}
}

