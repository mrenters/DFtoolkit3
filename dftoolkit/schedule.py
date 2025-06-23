#
# Copyright 2021-2025, Martin Renters
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
'''DFX_schedule handling class'''
from datetime import date

def to_int(value):
    '''Try to convert a value to an integer or None'''
    try:
        value = int(value)
    except ValueError:
        value = None
    return value

def to_date(value):
    '''Try to convert a value to a date object or None'''
    try:
        value = date.fromordinal(693595+int(value))
    except ValueError:
        value = None
    return value

#########################################################################
# ScheduleEntry
#########################################################################
class ScheduleEntry:
    '''An entry from the DFX_schedule file'''
    need_map = {
        '0': 'unknown',
        '1': 'required',
        '2': 'next',
        '3': 'optional',
        '4': 'excluded'
    }
    status_map = {
        '0': 'not done',
        '1': 'overdue',
        '2': 'missed',
        '7': 'done',
        '8': 'done/terminate',
        '9': 'done/abort'
    }
    condition_map = {
        '0': 'optional',
        '1': 'required',
        '-1': 'excluded'
    }
    def __init__(self):
        self.pid = None
        self.site = None
        self.cycle_number = None
        self.items = {}

    @classmethod
    def from_xschedule(cls, line):
        '''unpack a DFX_schedule entry'''
        fields = line.rstrip().split('|')
        entry = cls()
        entry.pid = int(fields[0])
        entry.site = int(fields[1])
        entry.cycle_number = int(fields[2])
        if fields[3] == 'C':
            entry.items['cycle_type'] = fields[4]
            entry.items['cycle_need'] = ScheduleEntry.need_map.get(fields[5])
            entry.items['cycle_status'] = \
                    ScheduleEntry.status_map.get(fields[6])
            entry.items['condition_need'] = \
                    ScheduleEntry.condition_map.get(fields[7])
            entry.items['condition_num'] = to_int(fields[8])
            entry.items['condition_seq'] = to_int(fields[9])
            entry.items['start'] = to_date(fields[11])
            entry.items['baseline'] = to_date(fields[13])
            entry.items['termination'] = to_date(fields[15])
        else:
            entry.items['visit_number'] = to_int(fields[3])
            entry.items['visit_type'] = fields[4]
            entry.items['visit_need'] = ScheduleEntry.need_map.get(fields[5])
            # Work around a DFdiscover bug that sometimes calls visits
            # not done but includes a data when they were done
            if fields[15] and fields[6] == '0':
                fields[6] = '7'
            entry.items['visit_status'] = \
                    ScheduleEntry.status_map.get(fields[6])
            entry.items['condition_need'] = \
                    ScheduleEntry.condition_map.get(fields[7])
            entry.items['condition_num'] = to_int(fields[8])
            entry.items['condition_seq'] = to_int(fields[9])
            entry.items['missed_visit_plate'] = to_int(fields[10])
            entry.items['early_termination_plate'] = to_int(fields[11])
            entry.items['condition_termination'] = to_int(fields[12])
            entry.items['start'] = to_date(fields[14])
            entry.items['visit'] = to_date(fields[16])
            entry.items['post_termination'] = to_int(fields[17])

        return entry

    def __repr__(self):
        return f'PID {self.pid} VISIT {self.visit_number}: ' \
                f'{self.visit_status} {self.visit_date}'

    @property
    def is_cycle(self):
        '''is this entry a cycle'''
        return 'cycle_type' in self.items

    @property
    def visit_number(self):
        '''return the visit number'''
        return self.items.get('visit_number')

    @property
    def visit_type(self):
        '''return the visit type'''
        return self.items.get('visit_type')

    @property
    def visit_status(self):
        '''return the visit status'''
        return self.items.get('visit_status')

    @property
    def visit_date(self):
        '''return the visit date'''
        return self.items.get('visit')

    @property
    def condition_need(self):
        '''visit need set by a condition in the conditional visit map;
           one of: optional, required, excluded or None'''
        return self.items.get('visit_status', None)
