#ifndef esig_h
#define esig_h

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

#include <sqlite3.h>
#include "tree.h"
#include "rangelist.h"
#include "stringlist.h"

///////////////////////////////////////////////////////////////////////////
// DataFax Keys
///////////////////////////////////////////////////////////////////////////
typedef unsigned long long	Patient;
typedef unsigned int		Plate;
typedef unsigned int		Visit;
typedef int			Field;

typedef unsigned long long	TransactionID;

#include "centers.h" 
#include "exclusions.h"

///////////////////////////////////////////////////////////////////////////
// DFaudittrace field numbers (offset by 1 as array is zero based)
///////////////////////////////////////////////////////////////////////////
#define AUDITREC_RECTYPE	0
#define AUDITREC_DATE		1
#define AUDITREC_TIME		2
#define AUDITREC_USER		3
#define AUDITREC_PID		4
#define AUDITREC_VISIT		5
#define AUDITREC_PLATE		6
#define AUDITREC_FIELDREF	7
#define AUDITREC_UNIQUEID	8
#define AUDITREC_STATUS		9
#define AUDITREC_LEVEL		10
#define AUDITREC_MAXLEVEL	11
#define AUDITREC_OLDVALUE	14
#define AUDITREC_NEWVALUE	15
#define AUDITREC_FIELDPOS	16
#define AUDITREC_FIELDDESC	17
#define AUDITREC_OLDDECODE	18
#define AUDITREC_NEWDECODE	19

// Signature statuses
typedef enum {
	SIG_NONE		=0,		// Never had a signature
	SIG_COMPLETE		=1,		// Signature complete
	SIG_INVALIDATED		=2		// Signature cleared or deleted
} signatureStatus;

// Record statuses
typedef enum {
	RECORD_NORMAL		=0,		// Normal record
	RECORD_ERROR		=1,		// Error record
	RECORD_LOST		=2,		// Lost record
	RECORD_DELETED		=3		// Deleted record
} recStatus;

// Field change statuses
typedef enum {
	CHANGE_NONE		=0,		// No data changes
	CHANGE_ACCEPTED		=1,		// Changes deemed OK
	CHANGE_DECLINED		=2,		// Changes not deemed OK
	CHANGE_DECLINED_ATFINAL	=3		// Changes not OK when final
} changeStatus;

typedef struct {
	signatureStatus		signatureStatus;
	recStatus		recStatus;
	changeStatus		changeStatus;
} Status;

///////////////////////////////////////////////////////////////////////////
// Esignature Configuration
///////////////////////////////////////////////////////////////////////////
typedef struct esigconf {
	struct esigconf	*next;
	Plate		plate;
	RangeList	*ignore_fields;
	RangeList	*visits;
	Plate		sig_plate;
	int		n_sig_fields;
	RangeList	*sig_fields;
	char		*name;
	int		serial;
} eSigConfig;

eSigConfig *	esc_config_head;

eSigConfig *	esc_alloc();
void		esc_free(eSigConfig *e);
void		esc_print(eSigConfig *e);
void		esc_priority_file(eSigConfig *e, char *path);

///////////////////////////////////////////////////////////////////////////
// Esignature Change node
// 	Tracks field changes
///////////////////////////////////////////////////////////////////////////
typedef struct fieldchange {
	RB_ENTRY(fieldchange)	link;
	Field			field;
	Status			status;
	char			*desc;
	char			*old_value;
	char			*new_value;
	char			*who;
	char			*date;
	char			*time;
	char			*comment;
} FieldChange;

FieldChange *	fc_alloc(Field field);
void		fc_free(FieldChange *n);
int		fc_compare(FieldChange *a, FieldChange *b);
typedef RB_HEAD(FieldChangeTree, fieldchange) FieldChangeTree;
RB_PROTOTYPE(FieldChangeTree, fieldchange, link, fc_compare);

///////////////////////////////////////////////////////////////////////////
// Esignature Covered Plate
// 	Tracks covered plate state and changes to fields on the plates
///////////////////////////////////////////////////////////////////////////

typedef struct coveredplate {
	RB_ENTRY(coveredplate)	link;
	Plate			plate;
	Status			status;
	int			is_final;
	int			field_change_count;
	FieldChangeTree		changes;
} CoveredPlate;

CoveredPlate *	cp_alloc(Plate plate);
void		cp_free(CoveredPlate *n);
int		cp_compare(CoveredPlate *a, CoveredPlate *b);
void		cp_free_changes(CoveredPlate *n);

typedef RB_HEAD(CoveredPlateTree, coveredplate) CoveredPlateTree;
RB_PROTOTYPE(CoveredPlateTree, coveredplate, link, cp_compare);

///////////////////////////////////////////////////////////////////////////
// Signature field tracking
///////////////////////////////////////////////////////////////////////////
typedef struct esigfield {
	Field			field;
	int			completed;
	char			*desc;
	char			*value;
} eSigField;

///////////////////////////////////////////////////////////////////////////
// Esignature Tracking node
// 	Tracks plates covered by this signature node as well as
// 	signature details
///////////////////////////////////////////////////////////////////////////

#define NODE_FLAG_RECSEEN	1

typedef struct esignode {
	RB_ENTRY(esignode)	link;
	Patient			id;
	Visit			visit;
	eSigConfig		*config;
	Status			status;
	char			*signer;
	char			*date;
	char			*time;
	CoveredPlateTree	plates;
	eSigField		*sig_fields;
	int			flags;
	TransactionID		txn_id;
} eSigNode;

typedef RB_HEAD(eSigNodeTree, esignode) eSigNodeTree;

eSigNode *	esn_alloc(Patient id, Visit visit, eSigConfig *config);
void		esn_alloc_sigfields(eSigNode *n);
void		esn_free(eSigNode *n);
void		esn_sig_rec_seen(eSigNode *n);
int		esn_was_sig_rec_seen(eSigNode *n);
int		esn_compare(eSigNode *a, eSigNode *b);
char *		esn_get_state(eSigNode *esn, int sdv_mode);
void		esn_sign(eSigNode *n, StringList *sl, Field field,
	       		TransactionID txn_id);
void		esn_free_signed_values(eSigNode *n, TransactionID txn_id);
void		esn_unsign(eSigNode *n, Field field);
void		esn_datachange(eSigNode *n, StringList *sl, Plate plate,
	       		Field field, TransactionID txn_id);
char		*decode_value(StringList *sl, int valuepos, int decodepos);

RB_PROTOTYPE(eSigNodeTree, esignode, link, esignode_compare);

void		update_string(char **s, char *v);

int		write_xls(char *fn, eSigNodeTree *tree, int arrived_only,
			int sdv_mode, struct centers *centers,
			struct countries *countries);

void		evaluate_tree(eSigNodeTree *tree, int allow_signer_changes,
			int resign_at_final);

sqlite3		*db_open(char *path);
void		db_close(sqlite3 *db);
void		db_write_signature(sqlite3 *db, eSigNode *n,
			TransactionID txn_id);
void		db_update_signature_value(sqlite3 *db, eSigNode *n, Plate plate,
			Field field, StringList *sl);

#endif
