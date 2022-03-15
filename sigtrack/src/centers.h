#ifndef centers_h
#define centers_h

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

#include "queue.h"

struct center {
	int		number;
	int		is_error_monitor;
	char		*contact;
	char		*affiliation;
	char		*address;
	char		*primary_fax;
	char		*secondary_fax;
	char		*phone;
	char		*investigator;
	char		*investigator_phone;
	char		*reply_address;
	RangeList	*pids;
	STAILQ_ENTRY	(center) link;
};
STAILQ_HEAD(centers, center);

struct country {
	char		*name;
	char		*region;
	RangeList	*centers;
	STAILQ_ENTRY	(country) link;
};
STAILQ_HEAD(countries, country);

int load_centers(char *path, struct centers *centers);
int find_center(struct centers *centers, Patient id);

int load_countries(char *path, struct countries *countries);
char *find_country(struct countries *countries, int center);
char *find_region(struct countries *countries, int center);

#endif
