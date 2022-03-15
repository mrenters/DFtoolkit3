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

/////////////////////////////////////////////////////////////////////////
// load_centers: Load Centers Database
/////////////////////////////////////////////////////////////////////////
int load_centers(char *path, struct centers *centers)
{
	StringList *sl = sl_alloc(32);
	struct center *center;
	int f;
	long long p_start, p_end;
	FILE *fp;

	STAILQ_INIT(centers);

	if (!path) return -1;

	if ((fp = fopen(path, "r")) == NULL) return -1;

	center = 0;
	while (sl_read(sl, fp, '|') == 0) {
		for (f=0; f < sl->n; f++) {
			switch(f) {
			case 0:
				center = calloc(1, sizeof(struct center));
				center->number = atoi(sl_value(sl, f));
				break;
			case 1:
				center->contact = strdup(sl_value(sl, f));
				break;
			case 2:
				center->affiliation = strdup(sl_value(sl, f));
				break;
			case 3:
				center->address = strdup(sl_value(sl, f));
				break;
			case 4:
				center->primary_fax = strdup(sl_value(sl, f));
				break;
			case 5:
				center->secondary_fax = strdup(sl_value(sl, f));
				break;
			case 6:
				center->phone = strdup(sl_value(sl, f));
				break;
			case 7:
				center->investigator = strdup(sl_value(sl, f));
				break;
			case 8:
				center->investigator_phone = strdup(sl_value(sl, f));
				break;
			case 9:
				center->reply_address = strdup(sl_value(sl, f));
				break;
			default:
				if (strcmp(sl_value(sl, f), "ERROR MONITOR") == 0) {
					center->is_error_monitor=1;
				} else {
					if (sscanf(sl_value(sl, f), "%lld %lld",
						&p_start, &p_end) != 2) {
						fprintf(stderr, "invalid patient range '%s' for center %d\n", sl_value(sl, f), center->number);
					} else {
						center->pids = rl_addtofront(
							center->pids,
							p_start, p_end);
					}
				}
			}
		}
		STAILQ_INSERT_TAIL(centers, center, link);
	}

	fclose(fp);
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// find_center: Find center number for Patient ID
/////////////////////////////////////////////////////////////////////////
int find_center(struct centers *centers, Patient id)
{
	struct center *cntr, *errmon;

	errmon = 0;
	STAILQ_FOREACH(cntr, centers, link) {
		if (rl_contains(cntr->pids, id))
			return cntr->number;
		if (cntr->is_error_monitor)
			errmon = cntr;
	}
	if (errmon)
		return errmon->number;
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// load_countries: Load Country Database
/////////////////////////////////////////////////////////////////////////
int load_countries(char *path, struct countries *countries)
{
	StringList *sl = sl_alloc(4);
	struct country *c;
	FILE *fp;

	STAILQ_INIT(countries);

	if (!path) return -1;

	if ((fp = fopen(path, "r")) == NULL) return -1;

	while (sl_read(sl, fp, '|') == 0) {
		c = calloc(1, sizeof(struct country));
		c->name = strdup(sl_value(sl, 0));
		c->region = strdup(sl_value(sl, 1));
		if (rl_fromstring(&c->centers, sl_value(sl, 2))) {
			fprintf(stderr, "Bad center list for '%s'\n", c->name);
		}
		STAILQ_INSERT_TAIL(countries, c, link);
	}
	fclose(fp);
	return 0;
}

/////////////////////////////////////////////////////////////////////////
// find_country: Find Country that Center belongs to
/////////////////////////////////////////////////////////////////////////
char *find_country(struct countries *countries, int centerid)
{
	struct country *cntry;

	STAILQ_FOREACH(cntry, countries, link) {
		if (rl_contains(cntry->centers, centerid))
			return cntry->name;
	}
	return "Unknown";
}

/////////////////////////////////////////////////////////////////////////
// find_region: Find Region that Center belongs to
/////////////////////////////////////////////////////////////////////////
char *find_region(struct countries *countries, int centerid)
{
	struct country *cntry;

	STAILQ_FOREACH(cntry, countries, link) {
		if (rl_contains(cntry->centers, centerid))
			return cntry->region;
	}
	return "Unknown";
}
