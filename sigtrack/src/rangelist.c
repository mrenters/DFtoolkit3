#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "rangelist.h"

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
// Rangelist List Support Functions
//
// Author: Martin Renters, Oct, 2015
/////////////////////////////////////////////////////////////////////////

/////////////////////////////////////////////////////////////////////////
// rl_addtofront - Adds a new range to the front of a RangeList
/////////////////////////////////////////////////////////////////////////
RangeList *rl_addtofront(RangeList *l, long long min, long long max)
{
	RangeList *l0;

	l0 = malloc(sizeof(RangeList));
	if (min > max) {	// Swap min/max
		min ^= max;
		max ^= min;
		min ^= max;
	}
	l0->next = l;
	l0->min = min;
	l0->max = max;
	return l0;
}

/////////////////////////////////////////////////////////////////////////
// rl_dup - Duplicate a RangeList
/////////////////////////////////////////////////////////////////////////
RangeList *rl_dup(RangeList *l)
{
	RangeList *n, *n0;
	
	n = n0 = 0;

	for (; l; l=l->next) {
		if (!n) {
			n0 = malloc(sizeof(RangeList));
			n = n0;
		} else {
			n0->next = malloc(sizeof(RangeList));
			n0 = n0->next;
		}
		n0->next = 0;
		n0->min = l->min;
		n0->max = l->max;
	}
	return n;
}

/////////////////////////////////////////////////////////////////////////
// rl_free - Free a RangeList
/////////////////////////////////////////////////////////////////////////
void rl_free(RangeList *l)
{
	RangeList *l0;

	while (l) {
		l0 = l->next;
		free(l);
		l = l0;
	}
}

/////////////////////////////////////////////////////////////////////////
// rl_min - Find minimum value in rangelist
/////////////////////////////////////////////////////////////////////////
long long rl_min(RangeList *l)
{
	long long v = 0, first = 1;
	for (;l; l=l->next) {
		if (first || (v > l->min)) {
			v = l->min;
			first = 0;
		}
	}
	return v;
}

/////////////////////////////////////////////////////////////////////////
// rl_max - Find maximum value in rangelist
/////////////////////////////////////////////////////////////////////////
long long rl_max(RangeList *l)
{
	long long v = 0, first = 1;
	for (;l; l=l->next) {
		if (first || (v < l->max)) {
			v = l->max;
			first = 0;
		}
	}
	return v;
}

/////////////////////////////////////////////////////////////////////////
// rl_width - Find number of values covered in rangelist
/////////////////////////////////////////////////////////////////////////
long long rl_width(RangeList *l)
{
	long long v = 0;
	for (;l; l=l->next) {
		v = v + (l->max - l->min) + 1;
	}
	return v;
}

/////////////////////////////////////////////////////////////////////////
// rl_contains - Check whether a RangeList contains a value
/////////////////////////////////////////////////////////////////////////
bool rl_contains(RangeList *l, long long v)
{
	for (;l;l=l->next) {
		if ((v >= l->min) && (v <= l->max)) return true;
	}
	return false;
}

/////////////////////////////////////////////////////////////////////////
// rl_tostring - Convert a RangeList to a string
/////////////////////////////////////////////////////////////////////////
char *rl_tostring(RangeList *l)
{
	int n,len = 1;
	char *s;
	RangeList *l0;

	for (l0=l; l0; l0=l0->next) {
		len += snprintf(NULL, 0, "%lld", l0->min);
		if (l0->min != l0->max) {		// Dash + max
			len += snprintf(NULL, 0, "-%lld", l0->max);
		}
		if (l0->next) len+=1;		// For comma
	}

	s = malloc(len);
	n = 0;
	for (l0=l; l0; l0=l0->next) {
		n += snprintf(s+n, len-n, "%lld", l0->min);
		if (l0->min != l0->max) {		// Dash + max
			n += snprintf(s+n, len-n, "-%lld", l0->max);
		}
		if (l0->next) *(s+(n++)) = ','; 
	}
	*(s+n) = 0;

	return s;
}

typedef enum { NUMBER, COMMA, DASH, ERROR, EOL } Token;

/////////////////////////////////////////////////////////////////////////
// rl_fromstring - Convert a string to RangeList
/////////////////////////////////////////////////////////////////////////
int rl_fromstring(RangeList **rl, char *s)
{
	long long v;
	RangeList *l=0;
	Token token, last;

	if (!s || (*s==0)) {		// Empty string
		*rl = 0;
		return 0;		// No error
	}

	if (strcmp(s, "*")==0) {	// Wildcard
		l = malloc(sizeof(RangeList));
		l->next = 0;
		l->min = 0;
		l->max = 0x7FFFFFFF;
		*rl = l;
		return 0;		// No Error
	}

	last = NUMBER;
	for (;*s;s++) {
		if (isspace(*s)) continue;
		if (isdigit(*s)) {
			v = 0;
			for (;isdigit(*s);s++) {
				v = (v*10) + (*s-'0');
			}
			token=NUMBER;
			s--;		// Back up one
		} else if (*s==',') {
			token=COMMA;
		} else if (*s=='-') {
			token=DASH;
		} else if (*s==0) {
			token=EOL;
		} else {
			token=ERROR;
		}

		switch(token) {
		case NUMBER:
			if (last == DASH) {
				if (l) {
					l->max = v;
					if (l->min > l->max) {
						l->min ^= l->max;
						l->max ^= l->min;
						l->min ^= l->max;
					}
					l = 0;
				} else {
					return -1;	// Error, DASH no digit
				}
			} else {
				l = malloc(sizeof(RangeList));
				l->next = 0;
				l->min = l->max = v;
				*rl = l;
				rl = &l->next;
			}
			break;
		case ERROR:
			return -1;
		case COMMA:
			l = 0;
			break;
		case DASH:
		case EOL:
			break;
		}
		last = token;
	}

	if (last != NUMBER) return -1;

	return 0;
}

#ifdef DEBUG_MAIN
int main(int argc, char *argv[])
{
	char *s;
	RangeList *l = 0;

	l=rl_addtofront(l, 1, 10);
	l=rl_addtofront(l, 5, 5);
	l=rl_addtofront(l, 100, 200);
	s=rl_tostring(l);
	printf("%d=%s\n", strlen(s), s);
	printf("fromstring=%d\n", rl_fromstring(&l, argv[1]));
	s=rl_tostring(l);
	printf("%d=%s\n", strlen(s), s);
}
#endif
