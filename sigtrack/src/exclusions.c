#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
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

static struct exclusions exclusions = STAILQ_HEAD_INITIALIZER(exclusions);

/////////////////////////////////////////////////////////////////////////
// load_exclusions: Load exclusions
/////////////////////////////////////////////////////////////////////////
int load_exclusions(char *path)
{
	StringList *sl = sl_alloc(32);
	struct exclusion *exclusion;
	int line=0;
	Plate plate;
	Field field;
	char *user, *date;
	char *p, *q;
	FILE *fp;

	if (!path) return -1;

	if ((fp = fopen(path, "r")) == NULL) return -1;

	while (sl_read(sl, fp, '|') == 0) {
		line++;
		// Check for correct number of columns and
	        // valid plate and field numbers
		if (sl->n < 4) continue;
		plate = atoi(sl_value(sl, 0));
		field = atoi(sl_value(sl, 1));
		user = sl_value(sl, 2);
		date = sl_value(sl, 3);
		if (!(plate && field && *user && *date)) continue;

		// Remove slashes from dates
		for (p=q=date; *p; p++) {
			if ((*p == '/') || (*p == '\r')) continue;
			*q = *p;
			q++;
		}
		*q = *p;
		// Make sure date is
		if ((strlen(date) != 8) || (strncmp(date, "20", 2) != 0)) {
			fprintf(stderr, "Exclusions File, bad date on line %d.\n", line);
			continue;
		}
		exclusion = calloc(1, sizeof(struct exclusion));
		exclusion->plate = plate;
		exclusion->field = field;
		exclusion->user = strdup(user);
		exclusion->date = strdup(date);
		STAILQ_INSERT_TAIL(&exclusions, exclusion, link);
	}
	fclose(fp);
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// is_excluded - Check whether this record is excluded
/////////////////////////////////////////////////////////////////////////
int is_excluded(StringList *sl)
{
	struct exclusion *e;
	char *user = sl_value(sl, AUDITREC_USER);
	char *date = sl_value(sl, AUDITREC_DATE);
	char *orig_value = sl_value(sl, AUDITREC_OLDVALUE);
	Plate plate = atoi(sl_value(sl, AUDITREC_PLATE));
	Field field = atoi(sl_value(sl, AUDITREC_FIELDPOS));

	STAILQ_FOREACH(e, &exclusions, link) {
		if (e->plate == plate && e->field == field &&
			strcmp(e->user, user)==0 &&
			strcmp(e->date, date)==0 &&
			strcmp(orig_value, "") == 0) {
				return 1;
		}
	}
	return 0;
}
