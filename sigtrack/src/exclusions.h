#ifndef exclusion_h
#define exclusion_h

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

#include "stringlist.h"
#include "queue.h"

struct exclusion {
	Plate		plate;
	Field		field;
	char		*user;
	char		*date;
	STAILQ_ENTRY	(exclusion) link;
};
STAILQ_HEAD(exclusions, exclusion);

int load_exclusions(char *path);
int is_excluded(StringList *sl);

#endif
