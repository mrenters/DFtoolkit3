#ifndef scan_h
#define scan_h
#include <stdio.h>

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
// String List Support Functions
//
// Author: Martin Renters, Oct, 2015
/////////////////////////////////////////////////////////////////////////

typedef struct {
	int	n;
	int	max;
	char	**v;
} StringList;

StringList *sl_alloc(int m);
int sl_read(StringList *sl, FILE *fp, char delimiter);
char *sl_value(StringList *sl, int n);
void sl_print(StringList *sl, char delimiter);
void sl_append(StringList *sl, char *p);
void sl_free(StringList *sl);
void sl_reset(StringList *sl);

#endif
