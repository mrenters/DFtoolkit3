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

'''Lookup Table type classes'''

#############################################################################
# LUTBase - Base Lookup Table
#############################################################################
class LUTBase(dict):
    '''Basic Lookup table class'''
    def label(self, code):
        '''Returns the label for a code'''
        return self.get(code, 'unknown')

#############################################################################
# LevelMap - Level class
#############################################################################
class LevelMap(LUTBase):
    '''Validation levels Map'''
    def __init__(self):
        super().__init__({
            0: 'Level 0',
            1: 'Level 1',
            2: 'Level 2',
            3: 'Level 3',
            4: 'Level 4',
            5: 'Level 5',
            6: 'Level 6',
            7: 'Level 7',
        })

#############################################################################
# MissingMap - Missing Map class
#############################################################################
class MissingMap(LUTBase):
    '''The Missing Map'''
    def __init__(self):
        super().__init__({'*': 'Missing Value'})

    def load(self, mmap_string):
        '''Loads a DFmissing_map style file'''
        codelist = {}
        for line in mmap_string.splitlines():
            fields = line.split('|')
            if len(fields) < 2:
                raise ValueError('Incorrectly formatted DFmissing_map entry: ' \
                             + line)
            codelist[fields[0]] = fields[1]
        self.clear()
        self.update(codelist)

#############################################################################
# ReasonStatusMap - Reason Status Map
#############################################################################
class ReasonStatusMap(LUTBase):
    '''Reason Status Map'''
    def __init__(self):
        super().__init__({
            1: 'approved',
            2: 'rejected',
            3: 'pending',
        })
