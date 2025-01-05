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
'''A module for tracking setup changes'''

from operator import ne

class ChangeRecord:
    '''A class for tracking a setup change'''
    def __init__(self, obj, description, old_value=None, new_value=None,
                 impact_level=0, impact_text=None):
        self.obj = obj
        self.description = description
        self.old_value = str(old_value) if old_value is not None else None
        self.new_value = str(new_value) if new_value is not None else None
        self.impact_level = impact_level
        self.impact_text = impact_text

    @property
    def impact_level_label(self):
        '''returns impact as a textual representation'''
        return 'High' if self.impact_level >= 10 else \
               'Med' if self.impact_level >= 5 else \
               'Low'

    def __repr__(self):
        return 'ChangeRecord<%s, %s, old=%s, new=%s, impact=%s, reason=%s>' % \
            (self.obj, self.description, self.old_value, self.new_value,
             self.impact_level_label, self.impact_text)

class ChangeTest:
    '''A test to see if a setup attribute has changed'''
    def __init__(self, description, compare_op=ne, impact_level=0,
                 impact_text=None):
        self.description = description
        self.compare_op = compare_op
        self.impact_level = impact_level
        self.impact_text = impact_text

class ChangeList(list):
    '''A class for constructing a list of setup changes'''
    def evaluate_attr(self, old_obj, new_obj, attrib, test):
        '''evaluate an attribute change and add it to list if changed'''
        old_value = getattr(old_obj, attrib)
        new_value = getattr(new_obj, attrib)
        self.evaluate_values(new_obj, old_value, new_value, test)

    def evaluate_values(self, obj, old_value, new_value, test):
        '''evaluate value change and add it to list if changed'''
        # If we're comparing for non-equality and one of the values is None,
        # the test is successful except when both values are None
        if not test.compare_op is ne and \
            (old_value is None or new_value is None):
            if old_value != new_value:
                self.append(ChangeRecord(obj, test.description,
                                         old_value, new_value,
                                         test.impact_level, test.impact_text))
        elif test.compare_op(old_value, new_value):
            self.append(ChangeRecord(obj, test.description,
                                     old_value, new_value,
                                     test.impact_level, test.impact_text))

    def evaluate_user_properties(self, prev, curr):
        '''evaluate changes to user properties of an object'''
        # Check changes to user properties
        for key, value in prev.user_properties.items():
            if key not in curr.user_properties:
                self.append(ChangeRecord(
                    prev, f'Property "{key}" Deleted',
                    value, None, impact_level=5,
                    impact_text='Potential Edit Check or Export effects'))
        for key, value in curr.user_properties.items():
            if key not in prev.user_properties:
                self.append(ChangeRecord(
                    curr, f'Property "{key}" Added',
                    None, value))
            else:
                self.evaluate_values(curr, prev.user_properties.get(key),
                                     value, ChangeTest(f'Property {key}'))
