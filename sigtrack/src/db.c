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
//// eSignature Database Support Functions
////
//// Author: Martin Renters, Oct, 2015
///////////////////////////////////////////////////////////////////////////

static char *setup_db = "\
drop table if exists signings;\
drop table if exists signature_values;\
drop table if exists data_values;\
create table signings (	\
  txnid  int not null,\
  sigid  int not null,\
  pid    int not null,\
  visit  int not null,\
  plate  int not null,\
  sdesc  text,\
  signer text,\
  sdate  text,\
  stime  text,\
  primary key (txnid, sigid));\
create table signature_values (\
  txnid  int not null,\
  sigid  int not null,\
  plate  int not null,\
  field  int not null,\
  fdesc  text,\
  fvalue text,\
  primary key(txnid, sigid, plate, field));\
create table data_values (\
  txnid  int not null,\
  sigid  int not null,\
  plate  int not null,\
  field  int not null,\
  fdesc  text,\
  fvalue text,\
  primary key(txnid, sigid, plate, field));\
create index signings_idx on signings(pid, visit, plate); \
";

//////////////////////////////////////////////////////////////////////////
// db_open - Open a database and set up tables
//////////////////////////////////////////////////////////////////////////
sqlite3 *db_open(char *path)
{
	sqlite3 *db;

	if (sqlite3_open(path, &db)) {
		fprintf(stderr, "unable to create/open %s -> %s\n",
			path, sqlite3_errmsg(db));
		return 0;
	}
	if (sqlite3_exec(db, setup_db, NULL, NULL, NULL)) {
		fprintf(stderr, "unable to initialize %s -> %s\n",
			path, sqlite3_errmsg(db));
		db_close(db);
		return 0;
	}
	if (sqlite3_exec(db, "BEGIN TRANSACTION", NULL, NULL, NULL)) {
		fprintf(stderr, "unable to begin transaction on %s -> %s\n",
			path, sqlite3_errmsg(db));
		db_close(db);
		return 0;
	}
	return db;
}

//////////////////////////////////////////////////////////////////////////
// db_close - Close a database
//////////////////////////////////////////////////////////////////////////
void db_close(sqlite3 *db)
{
	if (!db) return;
	sqlite3_exec(db, "COMMIT", NULL, NULL, NULL);

	sqlite3_close(db);
}

//////////////////////////////////////////////////////////////////////////
// db_write_signature - Write an entry in the DB showing record was signed
//////////////////////////////////////////////////////////////////////////
int db_write_signing_values(sqlite3_stmt *stmt, TransactionID txn_id,
	int serial, Plate plate, Field field, char *desc, char *value)
{
	//printf("   %lld %d %d %d %s %s\n", txn_id, serial, plate, field, desc, value);
	if (	(sqlite3_bind_int64(stmt, 1, txn_id) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 2, serial) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 3, plate) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 4, field) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 5, desc, -1,
			SQLITE_TRANSIENT) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 6, value, -1,
			SQLITE_TRANSIENT) != SQLITE_OK)) {
		fprintf(stderr, "unable to bind signing_values statment -> %s\n",
			sqlite3_errmsg(sqlite3_db_handle(stmt)));
		return -1;
	}
	if (sqlite3_step(stmt) != SQLITE_DONE) {
		fprintf(stderr, "unable to step signing_values statment -> %s\n",
			sqlite3_errmsg(sqlite3_db_handle(stmt)));
		return -1;
	}
	sqlite3_reset(stmt);
	return 0;
}

//////////////////////////////////////////////////////////////////////////
// db_write_signature - Write an entry in the DB showing record was signed
//////////////////////////////////////////////////////////////////////////
void db_write_signature(sqlite3 *db, eSigNode *n, TransactionID txn_id)
{
	int i;
	CoveredPlate *cp;
	FieldChange *fc;
	sqlite3_stmt *stmt;

	// If no DB, return
	if (!db) return;

	// Is this our signing transaction?
	if (n->txn_id != txn_id)
		return;

#ifdef DEBUG
	printf("(%lld %d) -> %lld, %d, %d %s %s %s (%s)\n",
		txn_id, n->config->serial,
		n->id, n->visit, n->config->sig_plate,
		n->signer, n->date, n->time, n->config->name);
#endif

	// Insert the signing event into the signings table
	if (sqlite3_prepare_v2(db, "insert or replace into signings values (?, ?, ?, ?, ?, ?, ?, ?, ?)", -1, &stmt, 0) != SQLITE_OK) {
		fprintf(stderr, "unable to prepare signing statment -> %s\n",
			sqlite3_errmsg(db));
		return;
	}
	if (	(sqlite3_bind_int64(stmt, 1, txn_id) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 2, n->config->serial) != SQLITE_OK) ||
		(sqlite3_bind_int64(stmt, 3, n->id) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 4, n->visit) != SQLITE_OK) ||
		(sqlite3_bind_int(stmt, 5, n->config->sig_plate) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 6, n->config->name, -1,
			SQLITE_TRANSIENT) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 7, n->signer, -1,
			SQLITE_TRANSIENT) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 8, n->date, -1,
			SQLITE_TRANSIENT) != SQLITE_OK) ||
		(sqlite3_bind_text(stmt, 9, n->time, -1,
			SQLITE_TRANSIENT) != SQLITE_OK)) {
		fprintf(stderr, "unable to bind signing statment -> %s\n",
			sqlite3_errmsg(db));
		sqlite3_finalize(stmt);
		return;
	}
	if (sqlite3_step(stmt) != SQLITE_DONE) {
		fprintf(stderr, "unable to step signing statment -> %s\n",
			sqlite3_errmsg(db));
		sqlite3_finalize(stmt);
		return;
	}
	sqlite3_finalize(stmt);

	// Now insert each of the field values
	if (sqlite3_prepare_v2(db, "insert or replace into signature_values values (?, ?, ?, ?, ?, ?)", -1, &stmt, 0) != SQLITE_OK) {
		fprintf(stderr, "unable to prepare signature_values statment -> %s\n",
			sqlite3_errmsg(db));
		return;
	}

	// Write out signature values
	for (i=0; i<n->config->n_sig_fields; i++) {
		if (db_write_signing_values(stmt, txn_id, n->config->serial,
			n->config->sig_plate, n->sig_fields[i].field,
			n->sig_fields[i].desc, n->sig_fields[i].value))
				break;
	}

	// Now insert each of the field values
	if (sqlite3_prepare_v2(db, "insert or replace into data_values values (?, ?, ?, ?, ?, ?)", -1, &stmt, 0) != SQLITE_OK) {
		fprintf(stderr, "unable to prepare data_values statment -> %s\n",
			sqlite3_errmsg(db));
		return;
	}

	// Write out rest of field values
	RB_FOREACH(cp, CoveredPlateTree, &n->plates) {
		RB_FOREACH(fc, FieldChangeTree, &cp->changes) {
			if (db_write_signing_values(stmt, txn_id,
				n->config->serial, cp->plate, fc->field,
			       	fc->desc, fc->new_value)) break;

			//printf("   %3d %3d %-40s %s\n", cp->plate, fc->field,
			//	fc->desc, fc->new_value);
		}
	}
	sqlite3_finalize(stmt);
}

//////////////////////////////////////////////////////////////////////////
// db_update_signature_value - Update DB when a field changes during
// 	a signing transaction
//////////////////////////////////////////////////////////////////////////
void db_update_signature_value(sqlite3 *db, eSigNode *n, Plate plate,
	Field field, StringList *sl)
{
	sqlite3_stmt *stmt;
	char *s;

	// If no DB, return
	if (!db) return;

        s = decode_value(sl, AUDITREC_NEWVALUE, AUDITREC_NEWDECODE);

	// Insert or update the field value
	if (sqlite3_prepare_v2(db, "insert or replace into data_values values (?, ?, ?, ?, ?, ?)", -1, &stmt, 0) != SQLITE_OK) {
		fprintf(stderr, "unable to prepare data_values statment -> %s\n",
			sqlite3_errmsg(db));
		return;
	}

	db_write_signing_values(stmt, n->txn_id, n->config->serial, plate,
		field, sl_value(sl, AUDITREC_FIELDDESC), s);

	//printf(" U %3d %3d %-40s %s\n", plate, field, sl_value(sl, AUDITREC_FIELDDESC), s);
	free(s);
	sqlite3_finalize(stmt);
}

