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

'''Module related code'''

from requests.structures import CaseInsensitiveDict
from .fieldbase import Field, FieldRef

##############################################################################
# Module Class
##############################################################################
class Module:
    '''Module representation class'''
    def __init__(self, study, json):
        self._study = study
        self._fields = []
        self._unique_id = json.get('id')
        self.description = json.get('description')
        self.name = json.get('name')
        self.user_properties = CaseInsensitiveDict()

        for userprop in json.get('userProperties', []):
            alias = self._study.user_property_tags.get(userprop.get('name'))
            if alias:
                self.user_properties[alias] = userprop.get('value')

        for field_json in json.get('fields', []):
            Field(self, field_json)

        self._fields.sort(key=lambda x: x.name.lower())

        study.add_module(self)

    @property
    def study(self):
        '''Returns a pointer to the study'''
        return self._study

    @property
    def unique_id(self):
        '''Returns a module's unique ID'''
        return self._unique_id

    def add_field(self, field):
        '''Add a field to a module and study'''
        self._fields.append(field)
        self._study.add_field(field)

    def field_by_id(self, unique_id):
        '''Returns a field by its unique ID'''
        for field in self._fields:
            if field.unique_id == unique_id:
                return field
        return None


##############################################################################
# ModuleRef Class - ModuleRefs of a Plate
##############################################################################
class ModuleRef:
    '''ModuleRef representation class'''
    def __init__(self, plate, json):
        self._plate = plate
        self._unique_id = None
        self._field_refs = {}
        self.description = json.get('description')
        self._unique_id = json.get('id')
        self.instance = json.get('instance', 0)
        self.name = json.get('name')
        self.module_id = json.get('moduleId')
        self.user_properties = CaseInsensitiveDict()

        study = plate.study
        for userprop in json.get('userProperties', []):
            alias = study.user_property_tags.get(userprop.get('name'))
            if alias:
                self.user_properties[alias] = userprop.get('value')

        for fieldref_json in json.get('fieldRefs', []):
            FieldRef(self, fieldref_json)

        plate.add_moduleref(self)

    @property
    def study(self):
        '''Returns a pointer to the study'''
        return self._plate.study

    @property
    def plate(self):
        '''Returns a pointer to the plate this ModuleRef belongs to'''
        return self._plate

    @property
    def identifier(self):
        '''Returns the module name and id as a MODULE[ID] string'''
        return '{0} [{1}]'.format(self.name, self.instance)

    @property
    def unique_id(self):
        '''Returns a moduleRef's unique ID'''
        return self._unique_id

    @property
    def fieldrefs(self):
        '''return a list of all the fieldRefs'''
        return self._field_refs.values()

    def add_fieldref(self, fieldref):
        '''Add a FieldRef to this ModuleRef'''
        self._field_refs[fieldref.unique_id] = fieldref
