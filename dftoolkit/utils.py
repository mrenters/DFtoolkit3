#
# Copyright 2020-2025, Martin Renters
#
# This file is part of DFtoolkit
#
# DFtoolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DFtoolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DFtoolkit.  If not, see <http://www.gnu.org/licenses/>.
#
'''Utility Functions'''

import sys

def is_eval():
    '''Is this an evaluation version'''
    return getattr(sys, 'frozen', False)

def format_pid(pid_format, pid):
    '''Format a subject ID using a format string'''
    if pid_format is None:
        return str(pid)

    num = pid_format.count('#')
    pid_zero = str(pid).zfill(num)
    num = 0
    pid_str = ''
    for char in pid_format:
        if char == '#':
            pid_str += pid_zero[num]
            num += 1
        else:
            pid_str += char

    # If there are still digits left, tack them on the end.
    if len(pid_zero) > num:
        pid_str += pid_zero[num:]
    return pid_str

def valid_ident(char):
    '''Return if a character is valid in an edit check name'''
    return 'A' <= char <= 'Z' or 'a' <= char <= 'z' or '0' <= char <= '9' or \
        char == '_' or char == '@'

def parse_editchecks(ecs_str):
    '''Returns a list of list of editcheck names from an editcheck definition'''
    if not ecs_str:
        return []
    i = 0
    ecs_str_len = len(ecs_str)
    editchecks = []
    while i < ecs_str_len:
        # Skip whitespace and other garbage until we get to start of EC name
        while i < ecs_str_len and not valid_ident(ecs_str[i]):
            i += 1

        if i >= ecs_str_len:
            break

        start = i

        # Scan EC name
        while i < ecs_str_len and valid_ident(ecs_str[i]):
            i += 1

        # Only have EC name, no params
        if i >= ecs_str_len:
            editchecks.append(ecs_str[start:i])
            break

        # If no params, continue to next EC
        if ecs_str[i] != '(':
            editchecks.append(ecs_str[start:i])
            continue

        i += 1

        # Look for ending )
        in_quote = False
        in_backslash = False
        while i < ecs_str_len:
            if ecs_str[i] == '\\' and not in_backslash:
                in_backslash = True
                i += 1
                continue
            if ecs_str[i] == '"' and not in_backslash:
                in_quote ^= True
                i += 1
                continue

            if ecs_str[i] == ')' and not in_quote:
                i += 1
                break

            in_backslash = False
            i += 1

        editchecks.append(ecs_str[start:i])
    return editchecks


def decode_pagemap_label(string, visit, plate):
    '''Decodes a pagemap or visitmap label with substitutions'''
    visit_str = str(visit).zfill(5)
    plate_str = str(plate).zfill(3) if plate is not None else ''
    out = ''
    state = 0
    for char in string:
        if state == 0:      # Normal String
            if char == '%':
                state = 1
            else:
                out += char
        elif state == 1:    # Saw %
            if char == '{':
                sub_start = 0
                sub_end = 0
                state = 2
            elif char == 'S':
                out += str(visit)
                state = 0
            elif char == 'P':
                out += str(plate)
                state = 0
        elif state == 2:    # Saw %{
            if '0' <= char <= '9':
                sub_start = sub_start * 10 + int(char)
                state = 3
            elif char == 'S':
                sub_string = visit_str
                state = 4
            elif char == 'P':
                sub_string = plate_str
                state = 4
            else:
                state = 0
        elif state == 3:    # Saw %{n, possible n or .
            if '0' <= char <= '9':
                sub_start = sub_start * 10 + int(char)
            elif char == '.':
                state = 10
            else:
                state = 0
        elif state == 4:    # Saw %{S|P, possible .
            if char == '.':
                sub_start = 0
                state = 5
            else:
                state = 0
        elif state == 5:    # Saw %{S|P., possible n, ., }
            if '0' <= char <= '9':
                sub_start = sub_start * 10 + int(char)
            elif char == '}':
                out += sub_string[-sub_start:]
                state = 0
            elif char == '.':
                sub_end = 0
                state = 6
            else:
                state = 0
        elif state == 6:  # Saw {S|P.n., possible n, }
            if '0' <= char <= '9':
                sub_end = sub_end * 10 + int(char)
            elif char == '}':
                out += sub_string[sub_start:sub_start+sub_end]
                state = 0
            else:
                state = 0
        elif state == 10:   # Saw %{n., possible S, P
            if char == 'S':
                sub_string = visit_str
                state = 11
            elif char == 'P':
                sub_string = plate_str
                state = 11
            else:
                state = 0
        elif state == 11:   # Saw %{n.S|P, possible }
            if char == '}':
                out += sub_string[:sub_start]
            state = 0

    return out
