%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "esig.h"
#include "rangelist.h"

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

#define YYINCLUDED_STDLIB_H

int yylex (void);
int yyerror(char *s);

extern eSigConfig *     esc_config_head;

%}

%union {
	int	i;
	char	*s;
	struct rangelist *r;
	struct esigconf	*e;
}

%token TOK_SIGNATURE
%token TOK_IGNORE
%token TOK_PLATE
%token TOK_VISIT
%token TOK_FIELDS
%token <i> TOK_NUMBER
%token <s> TOK_ID
%token <s> TOK_STRING
%type <r> range range_element ignore_fields visit_range
%type <e> signature sig_config plate_config plate_defn config
%type <i> number

%start config
%%

config		: config signature
			{
				if ($1) {
					eSigConfig *c = $1;
					while (c->next) c = c->next;
					c->next = $2;
					$$ = $1;
				} else {
					$$ = $2;
				}
				esc_config_head = $$;
			}
		| /* nothing */
			{
				$$ = 0;
			}
		| error '}'
			{
				$$ = 0;
			}
		;

signature	: sig_config '{' plate_config '}'
			{
				eSigConfig *e;

				// Copy signature config info into each
				// plate info structure
				for (e=$3; e; e = e->next) {
					e->name = strdup($1->name);
					e->sig_plate = $1->sig_plate;
					e->visits = rl_dup($1->visits);
					e->sig_fields = rl_dup($1->sig_fields);
					e->n_sig_fields = $1->n_sig_fields;
				}

				// Free sig_config as we no longer need it
				esc_free($1);
				$$ = $3;
			}


sig_config	: TOK_SIGNATURE TOK_STRING TOK_PLATE number TOK_VISIT visit_range TOK_FIELDS range 
			{
				$$ = esc_alloc();
				$$->name = $2;
				$$->sig_plate = $4;
				$$->visits = $6;
				$$->sig_fields = $8;
				$$->n_sig_fields = rl_width($8);
			}
		;

plate_config	: plate_config plate_defn
			{
				$2->next = $$;
				$$ = $2;
			}
		| plate_defn
			{ $$ = $1; }
		;
	
plate_defn	: TOK_PLATE number ignore_fields ';'
			{
				$$ = esc_alloc();
				$$->plate = $2;
				$$->ignore_fields = $3;
			}
		;

ignore_fields	: TOK_IGNORE TOK_FIELDS range
			{ $$ = $3; }
		| /* nothing */
			{ $$ = 0; }
		;

number		: TOK_NUMBER
			{ $$ = $1; }
		;

visit_range	: '*'
			{ $$ = rl_addtofront(0, 0, 65535); }
		| range
			{ $$ = $1; }
		;

range		: range ',' range_element
			{
				$3->next = $1;
				$$ = $3;
			}
		| range_element
			{ $$ = $1; }

range_element	: number '-' number
			{ $$ = rl_addtofront(0, $1, $3); }
		| number
			{ $$ = rl_addtofront(0, $1, $1); }
		;

%%
