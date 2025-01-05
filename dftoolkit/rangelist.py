# vim:ts=4:sw=4:et:ai:sts=4
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

'''RangeList functions and support classes'''

import argparse
import re

class RangeList:
    '''
    RangeList provides a class for storing and manipulating range lists in the
    form of: number, number-number
    '''
    def __init__(self, min_value, max_value, default_all=False):
        '''Initialize a Rangelist'''
        self.min_value = min_value
        self.max_value = max_value
        self.default_all = default_all
        self.values = []

    @property
    def empty(self):
        '''returns whether the rangelist has entries'''
        return len(self.values) == 0

    def from_string(self, range_string):
        '''Convert a range list string to a rangelist item'''
        self.values = []

        # Check for ALL keyword
        if range_string.strip().upper() == 'ALL':
            self.append(self.min_value, self.max_value)
            return

        # Remove beginning and trailing spaces
        range_string = range_string.strip()
        range_string = range_string.replace('~', '-')
        range_string = re.sub(r'[ ]+-', '-', range_string)
        range_string = re.sub(r'-[ ]+', '-', range_string)
        range_string = re.sub(r'[ ]+', ',', range_string)
        range_string = re.sub(r',+', ',', range_string)
        range_items = range_string.split(',')
        for range_item in range_items:
            if range_item == '':
                continue
            if range_item == '*':
                self.append(self.min_value, self.max_value)
                continue

            range_item_list = range_item.split('-')
            if len(range_item_list) == 2:
                self.append(int(range_item_list[0]),
                            int(range_item_list[1]))
            elif len(range_item_list) == 1:
                self.append(int(range_item_list[0]),
                            int(range_item_list[0]))
            else:
                raise ValueError('Invalid range specification')

    def append(self, low, high):
        '''Appends a low, high value to a RangeList'''
        if low > high or low < self.min_value or low > self.max_value or \
                high < self.min_value or high > self.max_value:
            raise ValueError('Invalid range specification')

        self.values.append((low, high))

    def __contains__(self, value):
        '''Returns whether value appears in the list'''
        if not self.values:
            return self.default_all

        for range_value in self.values:
            if range_value[0] <= value <= range_value[1]:
                return True
        return False

    def position(self, value):
        '''Returns the position in the list where value is located'''
        pos = -1
        for pos, range_value in enumerate(self.values):
            if range_value[0] <= value <= range_value[1]:
                return pos
        return pos+1

    def to_string(self):
        '''Returns a string representation of a RangeList'''
        return ','.join(
            ['{0}'.format(r[0]) if r[0] == r[1] else \
             '{0}-{1}'.format(r[0], r[1]) for r in self.values])

    def __repr__(self):
        return self.to_string()

    def __str__(self):
        return self.to_string()

    def sql(self, field_name):
        '''Generate an SQL clause from the rangelist'''
        if not self.values:
            return None
        clause = ''
        for range_value in self.values:
            if clause:
                clause += ' or '
            if range_value[0] == range_value[1]:
                clause += field_name + '=' + str(range_value[0])
            else:
                clause += field_name + ' between ' + str(range_value[0]) + \
                            ' and ' + str(range_value[1])
        return '(' + clause + ')'


class SiteList(RangeList):
    '''A representation of a list of sites'''
    def __init__(self, **kwargs):
        super(SiteList, self).__init__(0, 21460, **kwargs)

class SubjectList(RangeList):
    '''A representation of a list of patients'''
    def __init__(self, **kwargs):
        super(SubjectList, self).__init__(1, 281474976710656, **kwargs)

class PlateList(RangeList):
    '''A representation of a list of plates'''
    def __init__(self, **kwargs):
        super(PlateList, self).__init__(1, 500, **kwargs)

class VisitList(RangeList):
    '''A representation of a list of visits'''
    def __init__(self, **kwargs):
        super(VisitList, self).__init__(0, 65535, **kwargs)

class LevelList(RangeList):
    '''A representation of a list of levels'''
    def __init__(self, **kwargs):
        super(LevelList, self).__init__(0, 7, **kwargs)

class RangeListAction(argparse.Action):
    '''
    An argparse action to create a RangeList. Example:
    parser.add_argument('--ids', default=SubjectList(default_all=True),
                        action=RangeListAction)
    '''
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(RangeListAction, self).__init__(option_strings, dest, **kwargs)
        if not isinstance(self.default, RangeList):
            raise ValueError('No default rangelist specified')

    def __call__(self, parser, namespace, values, option_string=None):
        range_list = getattr(namespace, self.dest)
        try:
            range_list.from_string(values)
        except:
            raise argparse.ArgumentError(self, 'invalid range: ' + values)
