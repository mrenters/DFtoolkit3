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

'''Pagemap related code'''

from .rangelist import VisitList, PlateList
from .utils import decode_pagemap_label

#############################################################################
# PageMapEntry - An entry from the page map
#############################################################################
class PageMapEntry:
    '''Representation of an entry from DFpage_map'''
    def __init__(self):
        self.visits = VisitList()
        self.plates = PlateList()
        self.label = None

    @classmethod
    def from_pagemap(cls, line):
        '''Create a PageMapEntry from a DFpage_map line'''
        fields = line.split('|')
        if len(fields) < 3:
            raise ValueError('Incorrectly formatted DFpage_map entry: ' + line)
        entry = cls()
        entry.plates.from_string(fields[0])
        entry.visits.from_string(fields[1])
        entry.label = fields[2]
        return entry

#############################################################################
# PageMap - Page Map class
#############################################################################
class PageMap:
    '''Representation of DFpage_map'''
    def __init__(self):
        self.entries = []

    def load(self, pmap_string):
        '''Loads DFpage_map data'''
        lines = pmap_string.splitlines()
        self.entries = [PageMapEntry.from_pagemap(line) for line in lines \
                        if not line.startswith('S')]

    def label(self, visit, plate):
        '''Returns label for a given visit/plate combination'''
        for entry in self.entries:
            if visit in entry.visits and plate in entry.plates:
                return decode_pagemap_label(entry.label, visit, plate)
        return None
