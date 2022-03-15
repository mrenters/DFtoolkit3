#
# Copyright 2020-2022, Martin Renters
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

'''Visit Map related structures'''

from .rangelist import VisitList, PlateList
from .utils import decode_pagemap_label

#############################################################################
# VisitMapEntry - An entry from the visit map
#############################################################################
class VisitMapEntry:
    '''An entry from the visit_map, can be a cycle or a visit'''
    def __init__(self):
        self.visits = VisitList()
        self.visit_type = None
        self.cycle_type = None
        self.cycle_visit = 0
        self.cycle_base = '0'
        self.label = None
        self.date_plate = None
        self.date_field = None
        self.due_date = 0
        self.overdue_allowance = 0
        self.missed_visit_notification = None
        self.termination_window = None
        self.required_plates = PlateList()
        self.optional_plates = PlateList()
        self.display_order = PlateList()

    @classmethod
    def from_dfvisitmap(cls, line):
        '''Create Visitmap entry from DFvisit_map entry'''
        fields = line.split('|')
        if len(fields) < 7:
            raise ValueError('Incorrectly formatted visit map entry: ' + line)
        entry = cls()
        entry.visits.from_string(fields[0])
        entry.visit_type = fields[1]
        entry.label = fields[2]
        if entry.visit_type == 'C':     # Cycle
            entry.cycle_type = fields[3]
            entry.due_date = int(fields[4]) if fields[4] else 0
            entry.overdue_allowance = int(fields[5]) if fields[5] else 0
            entry.cycle_base = fields[6]
        else:                           # Regular visit
            entry.required_plates.from_string(fields[7])
            if len(fields) > 8:
                entry.optional_plates.from_string(fields[8])
            if len(fields) > 11 and fields[11] != '':
                entry.display_order.from_string(fields[11])
            else:
                entry.display_order.from_string(fields[7]+" "+fields[8])
            entry.date_plate = fields[3]
            entry.date_field = fields[4]
            entry.due_date = int(fields[5]) if fields[5] else None
            entry.overdue_allowance = int(fields[6]) if fields[6] else 0
            if len(fields) > 9 and fields[9]:
                entry.missed_visit_notification = int(fields[9])
            if len(fields) > 10 and fields[10]:
                entry.termination_window = fields[10]

        return entry

    def plate_order(self, plate):
        '''Returns the plate sort order position'''
        return self.display_order.position(plate)

    def __repr__(self):
        return '<VisitMapEntry (%s)>' % (self.label)

#############################################################################
# VisitMap - Visit Map class
#############################################################################
class VisitMap:
    '''Visit Map representation'''
    def __init__(self):
        self.entries = []

    def load(self, vmap_string):
        '''Load a visit map string'''
        lines = vmap_string.splitlines()
        self.entries = [VisitMapEntry.from_dfvisitmap(line) for line in lines]

    def label(self, visit_number):
        '''Find the label for the visit'''
        entry = self.visit(visit_number)
        return decode_pagemap_label(entry.label, visit_number, None) \
            if entry is not None else "Visit {0}".format(visit_number)

    def visit_with_order(self, visit_number):
        '''Find the visit map entry for visit along with its position'''
        order = -1
        for order, entry in enumerate(self.entries):
            if entry.visit_type != 'C' and visit_number in entry.visits:
                return order, entry
        return order+1, None

    def sort_order(self, visit_number, plate_number):
        '''Returns a sort key for a visit, plate combination'''
        visit_order, entry = self.visit_with_order(visit_number)
        if entry:
            plate_order = entry.plate_order(plate_number)
        else:
            plate_order = 0

        return (visit_order, visit_number, plate_order, plate_number)

    def visit(self, visit_number):
        '''Find the visit map entry for visit'''
        _, entry = self.visit_with_order(visit_number)
        return entry

    def cycle(self, cycle_number):
        '''Find the visit map entry for visit'''
        for entry in self.entries:
            if entry.visit_type == 'C' and cycle_number in entry.visits:
                return entry
        return None
