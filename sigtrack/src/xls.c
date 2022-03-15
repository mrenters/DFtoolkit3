#include "esig.h"
#include "centers.h"
#include "xlsxwriter.h"

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

#define CELL_COLOR_WHITE	0
#define CELL_COLOR_LTRED	1
#define CELL_COLOR_LTGREEN	2
#define CELL_COLOR_LTPURPLE	3
#define CELL_COLOR_LTYELLOW	4
#define CELL_COLOR_RED		5
#define CELL_COLOR_LTORANGE	6
#define CELL_COLOR_MAX		7

#define COL_REGION		0
#define COL_COUNTRY		1
#define COL_CENTER		2
#define COL_PID			3
#define COL_VISIT		4
#define COL_SIGPLATE		5
#define COL_SIGDESC		6
#define COL_STATUS		7
#define COL_SIGNER		8
#define COL_SIGDATE		9
#define COL_PLATE		10
#define COL_FIELD		11
#define COL_DESC		12
#define COL_SIGVALUE		13
#define COL_CURVALUE		14
#define COL_CHANGER		15
#define COL_CHANGEDATE		16
#define COL_COMMENT		17

#define LEFT			0
#define RIGHT			1

////////////////////////////////////////////////////////////////////////////
// GET_COLOR - Gets the cell color for a given status
////////////////////////////////////////////////////////////////////////////
static int get_color(Status *status)
{
	switch(status->signatureStatus) {
	case SIG_NONE:
		switch(status->recStatus) {
		case RECORD_NORMAL:
			return CELL_COLOR_LTYELLOW;	//"NEVER SIGNED";
		case RECORD_ERROR:
			return CELL_COLOR_LTPURPLE;  //"UNSIGNED ERROR RECORD";
		case RECORD_LOST:
			return CELL_COLOR_WHITE;  //"UNSIGNED LOST RECORD";
		case RECORD_DELETED:
			return CELL_COLOR_RED;	//"UNSIGNED DELETED RECORD";
		}
		break;
	case SIG_INVALIDATED:
		switch(status->recStatus) {
		case RECORD_NORMAL:
			return CELL_COLOR_LTRED; //"SIGNATURE REMOVED";
		case RECORD_ERROR:
			return CELL_COLOR_LTPURPLE; //"SIG. REMOVED, ERROR RECORD";
		case RECORD_LOST:
			return CELL_COLOR_WHITE; //"SIG. REMOVED, LOST RECORD";
		case RECORD_DELETED:
			return CELL_COLOR_RED;	//"SIG. REMOVED, DELETED RECORD";
		}
		break;
	case SIG_COMPLETE:
		switch(status->recStatus) {
		case RECORD_NORMAL:
			switch(status->changeStatus) {
			case CHANGE_NONE:
				return CELL_COLOR_LTGREEN; //"SIGNATURE OK";
			case CHANGE_ACCEPTED:
				return CELL_COLOR_LTGREEN; //"DATA CHANGE BY SIGNER";
			case CHANGE_DECLINED_ATFINAL:
				return CELL_COLOR_LTORANGE; //"RE-SIGN REQD AT FINAL";
			case CHANGE_DECLINED:
				return CELL_COLOR_LTRED; //"RE-SIGN REQD";
			}
			break;
		case RECORD_ERROR:
			return CELL_COLOR_LTPURPLE; //"SIGNED IN ERROR";
		case RECORD_LOST:
			return CELL_COLOR_WHITE; //"SIGNED, LOST";
		case RECORD_DELETED:
			return CELL_COLOR_RED; //"DELETED SIGNED RECORDS";
		}
		break;
	}
	return CELL_COLOR_WHITE; //"STATE UNKNOWN";
}

////////////////////////////////////////////////////////////////////////////
// MAKE_DATE - Makes a formatted date
////////////////////////////////////////////////////////////////////////////
static char *make_date(char *date, char *time)
{
	static char result[32];

	sprintf(result, "%4.4s/%2.2s/%2.2s %2.2s:%2.2s:%2.2s",
		date, date+4, date+6, time, time+2, time+4);
	return result;
}

////////////////////////////////////////////////////////////////////////////
// WRITE_XLS - Write XLS File
////////////////////////////////////////////////////////////////////////////
int write_xls(char *fn, eSigNodeTree *tree, int arrived_only, int sdv_mode,
	struct centers *centers, struct countries *countries)
{
	int i, j, row, addn_row, plate_rows;
	int sig_color, plate_color, field_color;
	int center;
	char *country;
	char *region;
	char *comment;
	eSigNode *esn;
	CoveredPlate *cp;
	FieldChange *fc;

	lxw_workbook	*workbook	= workbook_new(fn);
	lxw_worksheet	*worksheet;
	lxw_format	*header		= workbook_add_format(workbook);
	lxw_row_col_options hidden = {.hidden = 1, .level = 0, .collapsed = 0 };

	lxw_format	*format[CELL_COLOR_MAX][2];

	if (sdv_mode) {
		worksheet = workbook_add_worksheet(workbook, "SDV Report");
	} else {
		worksheet = workbook_add_worksheet(workbook, "e-Signatures");
	}

	// Printing format
	// Legal paper, landscape and fit all columns on a page
	worksheet_set_landscape(worksheet);
	worksheet_set_paper(worksheet, 5);	// 5 = Legal
	worksheet_fit_to_pages(worksheet, 1, 0);

	// Set header format
	format_set_bold(header);
	format_set_font_color(header, LXW_COLOR_WHITE);
	format_set_bg_color(header, LXW_COLOR_GRAY);
	format_set_align(header, LXW_ALIGN_CENTER);
	format_set_align(header, LXW_ALIGN_VERTICAL_CENTER);
	format_set_border(header, LXW_BORDER_THIN);

	// Set cell formats
	for (i=0; i<CELL_COLOR_MAX; i++) {
		for (j=LEFT; j<=RIGHT; j++) {
			format[i][j] = workbook_add_format(workbook);
			format_set_border(format[i][j], LXW_BORDER_THIN);
			format_set_text_wrap(format[i][j]);
			format_set_align(format[i][j], LXW_ALIGN_VERTICAL_CENTER);

			if (j == RIGHT) {
				format_set_align(format[i][j], LXW_ALIGN_RIGHT);
				format_set_num_format(format[i][j], "0");
			} else {
				format_set_num_format(format[i][j], "@");
			}

			switch(i) {
			case CELL_COLOR_WHITE:
				break;
			case CELL_COLOR_LTRED:
				format_set_font_color(format[i][j], 0x9c0006);
				format_set_bg_color(format[i][j], 0xffc7ce);
				break;
			case CELL_COLOR_LTYELLOW:
				format_set_font_color(format[i][j], 0x9c6500);
				format_set_bg_color(format[i][j], 0xffeb9c);
				break;
			case CELL_COLOR_LTGREEN:
				format_set_font_color(format[i][j], 0x006180);
				format_set_bg_color(format[i][j], 0xc6efce);
				break;
			case CELL_COLOR_LTPURPLE:
				format_set_font_color(format[i][j], 0x403151);
				format_set_bg_color(format[i][j], 0xccc0da);
				break;
			case CELL_COLOR_RED:
				format_set_font_color(format[i][j], 0x000000);
				format_set_bg_color(format[i][j], 0xff0000);
				break;
			case CELL_COLOR_LTORANGE:
				format_set_font_color(format[i][j], 0x9c0006);
				format_set_bg_color(format[i][j], 0xfce4c6);
				break;
			}
		}
	}

	// Write headers
	worksheet_write_string(worksheet, 0, COL_REGION, "Region", header);
	worksheet_write_string(worksheet, 0, COL_COUNTRY, "Country", header);
	worksheet_write_string(worksheet, 0, COL_CENTER, "Center", header);
	worksheet_write_string(worksheet, 0, COL_PID, "Patient ID", header);
	worksheet_write_string(worksheet, 0, COL_VISIT, "Visit", header);
	worksheet_write_string(worksheet, 0, COL_STATUS, "Status", header);
	worksheet_write_string(worksheet, 0, COL_PLATE, "Plate", header);
	worksheet_write_string(worksheet, 0, COL_FIELD, "Field", header);
	worksheet_write_string(worksheet, 0, COL_DESC, "Description", header);
	worksheet_write_string(worksheet, 0, COL_CURVALUE, "Current Value", header);
	worksheet_write_string(worksheet, 0, COL_CHANGER, "Last Changer", header);
	worksheet_write_string(worksheet, 0, COL_CHANGEDATE, "Last Changed", header);
	worksheet_write_string(worksheet, 0, COL_COMMENT, "Comment", header);
	if (sdv_mode) {
		worksheet_write_string(worksheet, 0, COL_SIGPLATE, "SDV Plate", header);
		worksheet_write_string(worksheet, 0, COL_SIGDESC, "SDV Desc", header);
		worksheet_write_string(worksheet, 0, COL_SIGNER, "SDV By", header);
		worksheet_write_string(worksheet, 0, COL_SIGDATE, "SDV Date", header);
		worksheet_write_string(worksheet, 0, COL_SIGVALUE, "SDV Value", header);
	} else {
		worksheet_write_string(worksheet, 0, COL_SIGPLATE, "Sig. Plate", header);
		worksheet_write_string(worksheet, 0, COL_SIGDESC, "Sig. Desc", header);
		worksheet_write_string(worksheet, 0, COL_SIGNER, "Signer", header);
		worksheet_write_string(worksheet, 0, COL_SIGDATE, "Signed", header);
		worksheet_write_string(worksheet, 0, COL_SIGVALUE, "Signed Value", header);
	}
	if (STAILQ_EMPTY(centers)) {
		worksheet_set_column_opt(worksheet, COL_REGION, COL_REGION,
		       	15, NULL, &hidden);
		worksheet_set_column_opt(worksheet, COL_COUNTRY, COL_COUNTRY,
		       	15, NULL, &hidden);
		worksheet_set_column_opt(worksheet, COL_CENTER, COL_CENTER,
			10, NULL, &hidden);
	} else {
		worksheet_set_column(worksheet, COL_REGION, COL_REGION,
		       	15, NULL);
		worksheet_set_column(worksheet, COL_COUNTRY, COL_COUNTRY,
		       	15, NULL);
		worksheet_set_column(worksheet, COL_CENTER, COL_CENTER,
		       	10, NULL);
	}
	worksheet_set_column(worksheet, COL_PID, COL_PID, 20, NULL);
	worksheet_set_column(worksheet, COL_VISIT, COL_VISIT, 10, NULL);
	worksheet_set_column(worksheet, COL_SIGPLATE, COL_SIGPLATE, 10, NULL);
	worksheet_set_column(worksheet, COL_SIGDESC, COL_SIGDESC, 15, NULL);
	worksheet_set_column(worksheet, COL_STATUS, COL_STATUS, 15, NULL);
	worksheet_set_column(worksheet, COL_SIGNER, COL_SIGNER, 15, NULL);
	worksheet_set_column(worksheet, COL_SIGDATE, COL_SIGDATE, 20, NULL);
	worksheet_set_column(worksheet, COL_PLATE, COL_PLATE, 10, NULL);
	worksheet_set_column(worksheet, COL_FIELD, COL_FIELD, 10, NULL);
	worksheet_set_column(worksheet, COL_DESC, COL_DESC, 30, NULL);
	worksheet_set_column(worksheet, COL_SIGVALUE, COL_SIGVALUE, 20, NULL);
	worksheet_set_column(worksheet, COL_CURVALUE, COL_CURVALUE, 20, NULL);
	worksheet_set_column(worksheet, COL_CHANGER, COL_CHANGER, 15, NULL);
	worksheet_set_column(worksheet, COL_CHANGEDATE, COL_CHANGEDATE, 20, NULL);
	worksheet_set_column(worksheet, COL_COMMENT, COL_COMMENT, 20, NULL);

	worksheet_set_row(worksheet, 0, 40, NULL);

	// Repeat header row on each page when printing
	worksheet_repeat_rows(worksheet, 0, 0);

	row = 1;

	RB_FOREACH(esn, eSigNodeTree, tree) {
		// If we are only interested in signature plates that
		// have arrived, skip those that haven't yet.
		if (arrived_only && !esn_was_sig_rec_seen(esn))
			continue;

		addn_row = 0;
		sig_color = get_color(&esn->status);

		RB_FOREACH(cp, CoveredPlateTree, &esn->plates) {
			plate_color = get_color(&cp->status);

			// If this record was signed, save space for
			// the field change rows.
			if (esn->status.signatureStatus != SIG_NONE)
				plate_rows = cp->field_change_count;
			else
				plate_rows = 0;

			// If this plate was marked pending or deleted
			// we'll have another output line
			if (RB_EMPTY(&cp->changes) &&
				(cp->status.recStatus != RECORD_NORMAL) &&
				(cp->status.changeStatus == CHANGE_DECLINED)) {
				plate_rows++;
			}

			// Merge plate entries together if there are multiple
			// fields that have changed on the same plate
			if (plate_rows > 1) {
				worksheet_merge_range(worksheet,
					row+addn_row, COL_PLATE,
						row+addn_row+plate_rows-1,
						COL_PLATE, "",
						format[plate_color][RIGHT]);
			}

			// If this plate was marked pending or deleted
			// write a status line out for it
			if (RB_EMPTY(&cp->changes) &&
				(cp->status.recStatus != RECORD_NORMAL) &&
				(cp->status.changeStatus == CHANGE_DECLINED)) {

				comment = 0;

				if (cp->status.recStatus == RECORD_LOST)
					comment = "Record marked Lost";
				if (cp->status.recStatus == RECORD_ERROR)
					comment = "Record marked in Error";
				if (cp->status.recStatus == RECORD_DELETED)
					comment = "Record Deleted";

				worksheet_write_number(worksheet,
					row + addn_row,
					COL_PLATE, (double)cp->plate,
					format[plate_color][RIGHT]);

				for (i=COL_FIELD; i<= COL_CHANGEDATE; i++) {
					worksheet_write_string(worksheet,
						row + addn_row, i, "",
						format[plate_color][LEFT]);
				}

				worksheet_write_string(worksheet,
					row + addn_row, COL_COMMENT,
					comment ? comment : "",
					format[plate_color][LEFT]);

				addn_row++;
			}

			// Show field changes, unless this record was never
			// signed.
			if (esn->status.signatureStatus != SIG_NONE)
			    RB_FOREACH(fc, FieldChangeTree, &cp->changes) {
				field_color = get_color(&fc->status);

				comment = fc->comment;
				if (cp->status.recStatus == RECORD_LOST)
					comment = "Record marked Lost";
				if (cp->status.recStatus == RECORD_ERROR)
					comment = "Record marked in Error";
				if (cp->status.recStatus == RECORD_DELETED)
					comment = "Record Deleted";

				worksheet_write_number(worksheet,
					row + addn_row,
					COL_PLATE, (double)cp->plate,
					format[plate_color][RIGHT]);
				worksheet_write_number(worksheet,
					row + addn_row,
					COL_FIELD, (double)fc->field,
					format[field_color][RIGHT]);
				worksheet_write_string(worksheet,
					row + addn_row,
					COL_DESC, fc->desc,
					format[field_color][LEFT]);
				worksheet_write_string(worksheet,
					row + addn_row,
					COL_SIGVALUE, fc->old_value,
					format[field_color][LEFT]);
				worksheet_write_string(worksheet,
					row + addn_row,
					COL_CURVALUE, fc->new_value,
					format[field_color][LEFT]);
				worksheet_write_string(worksheet,
					row + addn_row,
					COL_CHANGER, fc->who,
					format[field_color][LEFT]);
				worksheet_write_string(worksheet,
					row + addn_row, COL_CHANGEDATE,
					make_date(fc->date, fc->time),
					format[field_color][LEFT]);
				worksheet_write_string(worksheet,
					row + addn_row, COL_COMMENT,
					comment ? comment : "",
					format[field_color][LEFT]);
				addn_row++;
			}
		}

		// If there are no details, write blanks out for those cells
		if (addn_row == 0) {
			for (i=COL_PLATE; i<= COL_COMMENT; i++) {
				worksheet_write_string(worksheet,
					row, i, "", format[sig_color][LEFT]);
			}
			addn_row++;
		}

		if (addn_row > 1) {
			worksheet_merge_range(worksheet,
				row, COL_REGION, row+addn_row-1, COL_REGION, "",
				format[sig_color][LEFT]);
			worksheet_merge_range(worksheet,
				row, COL_COUNTRY, row+addn_row-1, COL_COUNTRY, "",
				format[sig_color][LEFT]);
			worksheet_merge_range(worksheet,
				row, COL_CENTER, row+addn_row-1, COL_CENTER, "",
				format[sig_color][RIGHT]);
			worksheet_merge_range(worksheet,
				row, COL_PID, row+addn_row-1, COL_PID, "",
				format[sig_color][RIGHT]);
			worksheet_merge_range(worksheet,
				row, COL_VISIT, row+addn_row-1, COL_VISIT, "",
				format[sig_color][RIGHT]);
			worksheet_merge_range(worksheet,
				row, COL_SIGPLATE, row+addn_row-1, COL_SIGPLATE, "",
				format[sig_color][RIGHT]);
			worksheet_merge_range(worksheet,
				row, COL_SIGDESC, row+addn_row-1, COL_SIGDESC, "",
				format[sig_color][LEFT]);
			worksheet_merge_range(worksheet,
				row, COL_STATUS, row+addn_row-1, COL_STATUS, "",
				format[sig_color][LEFT]);
			worksheet_merge_range(worksheet,
				row, COL_SIGNER, row+addn_row-1, COL_SIGNER, "",
				format[sig_color][LEFT]);
			worksheet_merge_range(worksheet,
				row, COL_SIGDATE, row+addn_row-1, COL_SIGDATE, "",
				format[sig_color][LEFT]);
		}
		center = find_center(centers, esn->id);
		country = find_country(countries, center);
		region = find_region(countries, center);

		for (i=0; i<addn_row; i++) {
			worksheet_write_string(worksheet, row+i, COL_REGION,
				region,
				format[sig_color][LEFT]);
			worksheet_write_string(worksheet, row+i, COL_COUNTRY,
				country,
				format[sig_color][LEFT]);
			worksheet_write_number(worksheet, row+i, COL_CENTER,
				(double)center,
				format[sig_color][RIGHT]);
			worksheet_write_number(worksheet, row+i, COL_PID,
				(double)esn->id,
				format[sig_color][RIGHT]);
			worksheet_write_number(worksheet, row+i, COL_VISIT,
				(double)esn->visit,
				format[sig_color][RIGHT]);
			worksheet_write_number(worksheet, row+i, COL_SIGPLATE,
				(double)esn->config->sig_plate,
				format[sig_color][RIGHT]);
			worksheet_write_string(worksheet, row+i, COL_SIGDESC,
				esn->config->name,
				format[sig_color][LEFT]);
			worksheet_write_string(worksheet, row+i, COL_STATUS,
				esn_get_state(esn, sdv_mode),
				format[sig_color][LEFT]);
			if (esn->signer) {
				worksheet_write_string(worksheet, row+i,
					COL_SIGNER,
					esn->signer,
				format[sig_color][LEFT]);
			} else {
				worksheet_write_string(worksheet, row+i,
					COL_SIGNER,
					"", format[sig_color][LEFT]);
			}
			if (esn->date && esn->time) {
				worksheet_write_string(worksheet, row+i,
					COL_SIGDATE,
					make_date(esn->date, esn->time),
					format[sig_color][LEFT]);
			} else {
				worksheet_write_string(worksheet, row+i,
					COL_SIGDATE,
					"", format[sig_color][LEFT]);
			}
		}
		row += addn_row;
	}

	worksheet_freeze_panes(worksheet, 1, 0);
	worksheet_autofilter(worksheet, 0, 0, row-1, COL_COMMENT);
	if (!STAILQ_EMPTY(centers))
		worksheet_set_zoom(worksheet, 90);

	return workbook_close(workbook);
}
