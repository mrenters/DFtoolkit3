#ifndef rangelist_h
#define rangelist_h

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

#include <stdbool.h>

/////////////////////////////////////////////////////////////////////////
// Rangelist List Support Functions
//
// Author: Martin Renters, Oct, 2015
/////////////////////////////////////////////////////////////////////////

typedef struct rangelist {
	struct rangelist *next;
	long long	min,max;
} RangeList;

RangeList *rl_addtofront(RangeList *l, long long min, long long max);
RangeList *rl_dup(RangeList *l);
void rl_free(RangeList *l);
int rl_fromstring(RangeList **rl, char *s);
char *rl_tostring(RangeList *l);
bool rl_contains(RangeList *l, long long v);
long long rl_min(RangeList *l);
long long rl_max(RangeList *l);
long long rl_width(RangeList *l);

#endif
