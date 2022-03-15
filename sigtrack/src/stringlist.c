#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stringlist.h"

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

/////////////////////////////////////////////////////////////////////////
// sl_alloc - Allocate a string list with default m items
/////////////////////////////////////////////////////////////////////////
StringList *sl_alloc(int m)
{
	StringList *sl = malloc(sizeof(StringList));

	sl->n = 0;
	sl->v = calloc(m, sizeof(char *));
	sl->max = m;
	return sl;
}

/////////////////////////////////////////////////////////////////////////
// sl_reset - Free all strings in the stringlist
/////////////////////////////////////////////////////////////////////////
void sl_reset(StringList *sl)
{
	int i;

	for (i=0; i<sl->n; i++) {
		if (sl->v[i]) free(sl->v[i]);
		sl->v[i] = 0;
	}
	sl->n=0;
}

/////////////////////////////////////////////////////////////////////////
// sl_free - Destroy the stringlist
/////////////////////////////////////////////////////////////////////////
void sl_free(StringList *sl)
{
	sl_reset(sl);
	free(sl->v);
	free(sl);
}

/////////////////////////////////////////////////////////////////////////
// sl_value - Return the nth string in stringlist or "" if nonexistent
/////////////////////////////////////////////////////////////////////////
char *sl_value(StringList *sl, int n)
{
	char *ret;
	if ((n < 0) || (n >= sl->n) || (!sl->v[n])) {
		ret="";
	} else {
		ret = sl->v[n];
	}
	return ret;
}

/////////////////////////////////////////////////////////////////////////
// sl_print - Print the stringlist
/////////////////////////////////////////////////////////////////////////
void sl_print(StringList *sl, char delimiter)
{
	int i;

	for (i=0; i<sl->n; i++) {
		printf("%s%c", sl_value(sl, i), delimiter);
	}
	printf("\n");
}


/////////////////////////////////////////////////////////////////////////
// sl_append - Append a string to the end of stringlist
/////////////////////////////////////////////////////////////////////////
void sl_append(StringList *sl, char *p)
{
	if (sl->n >= sl->max) {
		int i, newmax = sl->max + 32;
		sl->v = realloc(sl->v, sizeof(char *) * newmax);
		for (i=sl->max; i<newmax; i++) {
			sl->v[i] = 0;
		}
		sl->max = newmax;
		
	}
	sl->v[sl->n++] = p;
}

/////////////////////////////////////////////////////////////////////////
// sl_read - Read a stringlist from a delimited file
/////////////////////////////////////////////////////////////////////////
int sl_read(StringList *sl, FILE *fp, char delimiter)
{
	int c;
	int p_len;
	int p_bsize;
	char *p;
	char *b;
	char buffer[1024];

	sl_reset(sl);

	p_len = p_bsize = 0;
	b = buffer;
	buffer[0] = 0;
	p = 0;
	while (1) {
		if (! *b) {
			b = fgets(buffer, sizeof(buffer), fp);
			if (!b) {
				return -1;
			}
		}
		c = *(b++);
		if (c == '\n') {
			sl_append(sl, p);
			return 0;
		} else if (c == delimiter) {
			sl_append(sl, p);
			p_len = p_bsize = 0;
			p = 0;
		} else {
			if (p_len >= (p_bsize-1)) {
				p_bsize += 64;
				p = realloc(p, p_bsize);
			}
			*(p+(p_len++)) = c;
			*(p+(p_len)) = 0;
		}
	}
	return 0;
}

#ifdef DEBUG_MAIN
int main(int argc, char *argv[])
{
	StringList *sl = sl_alloc(32);
	while (sl_read(sl, stdin, '|')==0) {
		sl_print(sl, '*');
	}
	printf("sl->max=%d\n", sl->max);
}
#endif
