%option noyywrap
%option noinput
%option nounput

%{
#include <stdio.h>
#include <stdlib.h>
#include "grammar.tab.h"

///////////////////////////////////////////////////////////////////////////////
//
// Copyright 2015-2017, Population Health Research Institute
// Copyright 2015-2017, Martin Renters
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

int yyerror(char *s);

static int line_number = 1;
static int config_error = 0;

%}

%p 5000

WS	[ \t\f\r]+

%%

{WS}	{ /* skip */ }

#.*		{ /* skip */ }
"signature"	{ return TOK_SIGNATURE; }
"ignore"	{ return TOK_IGNORE; }
"plate"		{ return TOK_PLATE; }
"visit"		{ return TOK_VISIT; }
"fields"	{ return TOK_FIELDS; }

[0-9]+		{ yylval.i = atoi(yytext); return TOK_NUMBER; }
\"[^"]*\"	{
			yylval.s = strdup(yytext+1);	// Kill leading quote
			*(yylval.s + strlen(yylval.s)-1)=0; // Kill end quote
			return TOK_STRING;
		}
[A-Za-z][A-Za-z0-9]+	{ yylval.s = strdup(yytext); return TOK_ID; }
[;,-{}*]		{ return yytext[0]; }
\n		{ line_number++; }

.		{
			yyerror("unexpected character");
		}

%%
int yyerror(char *s)
{
        fprintf(stderr, "line %d: %s at or near '%s'\n", line_number, s, yytext);
	config_error++;
	return 0;		// Silence compiler
}

int get_config_error_cnt()
{
	return config_error;
}
