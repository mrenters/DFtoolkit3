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

'''This file contains study setup and configuration related code'''

import json
import logging
from requests.structures import CaseInsensitiveDict
from .fieldbase import Style
from .plate import Plate
from .module import Module
from .visitmap import VisitMap
from .pagemap import PageMap
from .lookup import LevelMap, MissingMap, ReasonStatusMap
from .metadata import  QCStatusMap, QCTypeMap, Query, Reason
from .record import Record
from .sites import Sites
from .rangelist import PlateList, SubjectList
from .changerecord import ChangeList, ChangeTest, ChangeRecord

class Study:
    '''Study representation class'''
    def __init__(self, api):
        self.api = api
        self.add_pid_enabled = False
        self.auto_help = False
        self.auto_reason = None
        self.box_height = 25
        self.create_version = None
        self.created = None
        self.creator = None
        self.crf_guides = True
        self.date_rounding = None
        self.description_len = None
        self.file_version = None
        self.fill_color = '#ffffff'
        self.foreground_color = '#ffff00'
        self.modify_version = None
        self.multiple_qcs = False
        self.setup_name = None
        self.next_field_id = 0
        self.next_module_id = 0
        self.number = None
        self.pid_count = 5
        self.setup_version = None
        self.snap = True
        self.start_year = 1990
        self.unique_field_names = False
        self.var_guides = True
        self.variables_color = '#0064ff'
        self.viewmode_ec = False
        self.year_cutoff = 1920
        self._modules = {}
        self._module_ids = {}
        self._field_ids = {}
        self._styles = {}
        self._plates = {}
        self._visitmap = None
        self._pagemap = None
        self.levels = LevelMap()
        self.missingmap = MissingMap()
        self.reason_statuses = ReasonStatusMap()
        self.qc_statuses = QCStatusMap()
        self.qc_types = QCTypeMap()
        self._sites = Sites()
        self.user_property_tags = {}
        self.user_properties = CaseInsensitiveDict()
        self._config = {}

    ########################################################################
    # Style Related Functions
    ########################################################################
    def add_style(self, style):
        '''
        Add a style to the study if it doesn't already exist. Returns the
        Style object.
        '''
        if style.style_name in self._styles:
            raise ValueError(f'Style {style.style_name} already exists')
        self._styles[style.style_name] = style

    def style(self, name):
        '''return style information by name'''
        return self._styles.get(name)

    ########################################################################
    # Module Related Functions
    ########################################################################
    def add_module(self, module):
        '''
        Add a module to the study if it doesn't already exist. Returns the
        Module object.
        '''
        if module.name in self._modules:
            raise ValueError(f'Module name {module.name} already exists')
        if module.unique_id in self._module_ids:
            raise ValueError(f'Module ID {module.unique_id} already exists')

        self._modules[module.name] = module
        self._module_ids[module.unique_id] = module

    @property
    def modules(self):
        '''
        Returns a sorted list of Module objects for the study
        '''
        return sorted(self._modules.values(), key=lambda x: x.name.lower())

    def module_by_id(self, module_id):
        '''Returns a reference to the module object with ID module_id'''
        module = self._module_ids.get(module_id)
        if not module:
            raise ValueError(f'Module {module_id} is not defined')
        return module

    def module_by_name(self, module_name):
        '''Returns a reference to the module object with name module_name'''
        module = self._modules.get(module_name)
        if not module:
            raise ValueError(f'Module "{module_name}" is not defined')
        return module

    def add_field(self, field):
        '''add a field to the list of field objects'''
        self._field_ids[field.unique_id] = field

    def field(self, field_id):
        '''get a field by ID'''
        field = self._field_ids.get(field_id)
        if not field:
            raise ValueError(f'Field {field_id} is not defined')
        return field

    ########################################################################
    # Plate Related Functions
    ########################################################################
    def add_plate(self, plate):
        '''
        Add a plate to the study if it doesn't already exist. Returns the
        Plate object.
        '''
        if plate.number in self._plates:
            raise ValueError(f'Plate number {plate.number} already exists')
        self._plates[plate.number] = plate

    def plate(self, number):
        '''
        Returns the Plate object for requested plate number or None if it
        doesn't exist.
        '''
        return self._plates.get(number)

    @property
    def plates(self):
        '''
        Returns a sorted list of Plate objects for the study
        '''
        return sorted(self._plates.values(), key=lambda plate: plate.number)

    @property
    def user_plates(self):
        '''Returns a list of user defined plates'''
        return list(filter(lambda plate: 0 < plate.number <= 500, self.plates))

    @property
    def field_uniqueids(self):
        '''
        Returns a dictionary of field unique ids
        '''
        fields = {}
        for plate in self._plates.values():
            for field in plate.fields:
                fields[field.unique_id] = field

        return fields

    ########################################################################
    # Setup Related Functions
    ########################################################################
    def load_setup(self, json_data):
        '''load DFsetup data'''
        try:
            setup = json.loads(json_data)
        except ValueError:
            return False

        study = setup.get('study', {})
        self.add_pid_enabled = study.get('addPidEnabled')
        self.auto_help = study.get('autoHelp')
        self.auto_reason = study.get('autoReadon')
        self.box_height = study.get('boxHeight', 25)
        self.create_version = study.get('createVersion')
        self.created = study.get('created')
        self.creator = study.get('creator')
        self.crf_guides = study.get('crfGuides', True)
        self.date_rounding = study.get('dateRounding', 'Never')
        self.description_len = study.get('descriptionLen')
        self.file_version = study.get('fileVersion')
        self.fill_color = study.get('fillColor', '#ffffff')
        self.foreground_color = study.get('foregroundColor', '#ffff00')
        self.modify_version = study.get('modifyVersion')
        self.multiple_qcs = study.get('multipleQC', False)
        self.setup_name = study.get('name')
        self.next_field_id = study.get('nextFieldId', 0)
        self.next_module_id = study.get('nextModuleId', 0)
        self.number = study.get('number')
        self.pid_count = study.get('pidCount', 5)
        self.setup_version = study.get('setupVersion')
        self.snap = study.get('snap', True)
        self.start_year = study.get('startYear')
        self.unique_field_names = study.get('uniqueFieldNames', False)
        self.var_guides = study.get('varGuides', True)
        self.variables_color = study.get('variablesColor', '#0064ff')
        self.viewmode_ec = study.get('viewModeEc', False)
        self.year_cutoff = study.get('yearCutoff', 1920)

        # Load level names
        for level_json in study.get('levels', []):
            self.levels[level_json.get('level')] = level_json.get('label')

        # Load user property tags
        for userproptag_json in study.get('userPropTags', []):
            self.user_property_tags[userproptag_json.get('name')] = \
                userproptag_json.get('alias')

        for userprop in study.get('userProperties', []):
            alias = self.user_property_tags.get(userprop.get('name'))
            if alias:
                self.user_properties[alias] = userprop.get('value')


        ###################################################################
        # Load Styles
        ###################################################################
        for style_json in study.get('styles', []):
            Style(self, style_json)

        ###################################################################
        # Load Modules
        ###################################################################
        for module_json in study.get('modules', []):
            Module(self, module_json)

        ###################################################################
        # Load Plates
        ###################################################################
        for plate_json in study.get('plates', []):
            Plate(self, plate_json)

        return True

    ########################################################################
    # Visit Map Related Functions
    ########################################################################
    def load_visit_map(self, visitmap_string):
        '''load DFvisit_map data'''
        self._visitmap = VisitMap()
        return self._visitmap.load(visitmap_string)

    def visit_label(self, visit):
        '''map a visit number to a label'''
        return self._visitmap.label(visit) if self._visitmap else \
               f'Visit {visit}'

    def visit(self, visit_num):
        '''returns a visit map entry for this visit'''
        return self._visitmap.visit(visit_num)

    @property
    def visit_map(self):
        '''get visit map information'''
        return self._visitmap

    ########################################################################
    # Missing Map Related Functions
    ########################################################################
    def load_missing_map(self, missingmap_string):
        '''load DFmissing_map data'''
        return self.missingmap.load(missingmap_string)

    ########################################################################
    # Sites Database Related Functions
    ########################################################################
    def load_sites(self, centersdb_string):
        '''load DFcenters data'''
        return self._sites.load(centersdb_string)

    @property
    def sites(self):
        '''get a site information'''
        return self._sites

    ########################################################################
    # Domain Map Related Functions
    ########################################################################
    def load_domain_map(self, domainmap_string):
        '''load DFdomains (non-standard extension file)'''
        for line in domainmap_string.splitlines():
            fields = line.split('|')
            if len(fields) < 2:
                raise ValueError('Incorrectly formatted DFdomains entry: ' + \
                                 line)
            plates = PlateList()
            plates.from_string(fields[1])
            for plate in self.plates:
                if plate.number in plates:
                    plate.set_domain(fields[0])

    ########################################################################
    # Page Map Related Functions
    ########################################################################
    def load_page_map(self, pagemap_string):
        '''load DFpage_map data'''
        self._pagemap = PageMap()
        return self._pagemap.load(pagemap_string)

    def page_label(self, visit_num, plate_num):
        '''Get page label from DFpage_map data'''
        label = None
        if self._pagemap:
            label = self._pagemap.label(visit_num, plate_num)
        if not label:
            plate = self.plate(plate_num)
            label = plate.description if plate else \
                    f'Plate {plate_num}'
        return label

    ########################################################################
    # Data Export Related functions
    ########################################################################
    def data(self, plate, subjects=SubjectList(default_all=True),
             missing_records=False, secondary_records=False):
        '''Returns a Query structure based on raw data record'''
        for record in self.api.data(plate, subjects,
                                    missing_records=missing_records,
                                    secondary_records=secondary_records):
            yield Record(self, record)

    ########################################################################
    # Query Related functions
    ########################################################################
    def queries(self, subjects=SubjectList(default_all=True)):
        '''Returns a Query structure based on raw QC record'''
        for record in self.api.queries(subjects):
            yield Query(self, record)

    ########################################################################
    # Reason Related functions
    ########################################################################
    def reasons(self, subjects=SubjectList(default_all=True)):
        '''Returns a Reason structure based on raw reason record'''
        for record in self.api.reasons(subjects):
            yield Reason(self, record)

    def reason_status(self, value):
        '''Get reason status label'''
        if not isinstance(value, int):
            value = int(value)

        return self.reason_statuses.label(value)

    ########################################################################
    # Config Related Functions
    ########################################################################
    def load_server_config(self, config_string):
        '''Load server configuration information from DFserver.cf data'''
        self._config = {}
        server_config_lines = config_string.splitlines()
        for line in server_config_lines:
            config = line.split('=')
            if len(config) < 2:
                continue
            self._config[config[0]] = config[1]

    @property
    def study_name(self):
        '''get the study name, either from the config file, or the setup'''
        return self._config.get('STUDY_NAME', self.setup_name)

    def __repr__(self):
        return f'<Study {self.number} - {self.study_name}>'

    ########################################################################
    # Load Study Setup information
    ########################################################################
    def load(self):
        '''Load study information from files in STUDYDIR'''
        try:
            self.load_server_config(self.api.config())
        except IOError:
            pass

        # We need at least a setup file
        self.load_setup(self.api.setup())

        try:
            self.load_visit_map(self.api.visit_map())
        except IOError:
            pass

        try:
            self.load_page_map(self.api.page_map())
        except IOError:
            pass

        try:
            self.load_missing_map(self.api.missing_map())
        except IOError:
            pass

        try:
            self.load_sites(self.api.sites())
        except IOError:
            logging.warning('Unable to load site information')

        try:
            self.sites.merge_countries(self.api.countries())
        except IOError:
            pass

        try:
            self.load_domain_map(self.api.domain_map())
        except IOError:
            pass

        try:
            self.qc_types.load(self.api.qc_types())
        except IOError:
            pass

    ########################################################################
    # Load Priority File
    ########################################################################
    def load_priority_file(self, fname):
        '''Load a priority file of the format Plate|Field|Priority'''
        try:
            lines = self.api.priority_file(fname)
        except IOError:
            return

        for line in lines.splitlines():
            fields = line.split('|')
            if len(fields) < 3:
                raise ValueError('Incorrectly formatted priority entry: ' + \
                                 line)
            if fields[0] == 'Plate' and fields[1] == 'Field' and \
               fields[2] == 'Priority':
                continue

            try:
                plate_num = int(fields[0])
                field_num = int(fields[1])
                priority = int(fields[2])

                plate = self.plate(plate_num)
                field = plate.field(field_num)

                priority = min(max(priority, 1), 5)
                field.priority = priority
            except ValueError:
                pass

    ########################################################################
    # changes
    ########################################################################
    def changes(self, prev):
        '''build a list of differences between two setups'''
        changelist = ChangeList()
        for attrib, test in [
                ('create_version', ChangeTest('Creation Version')),
                ('created', ChangeTest('Creation Date')),
                ('creator', ChangeTest('Creator')),
                ('date_rounding',
                 ChangeTest('Date Rounding', impact_level=10,
                            impact_text='Potential Meaning Change')),
                ('description_len', ChangeTest('Description Length')),
                ('file_version', ChangeTest('File Version')),
                ('modify_version', ChangeTest('Modifing Software Version')),
                ('multiple_qcs', ChangeTest('Multiple QCs Enabled')),
                ('number', ChangeTest('Study Number')),
                ('setup_version', ChangeTest('Study Setup Version')),
                ('start_year',
                 ChangeTest('Study Start Year', impact_level=10,
                            impact_text='Potential Meaning Change')),
                ('unique_field_names', ChangeTest('Unique Field Names')),
                ('viewmode_ec', ChangeTest('Execute Edit Checks in View Mode')),
                ('year_cutoff',
                 ChangeTest('Two Digit Year Cutoff', impact_level=10,
                            impact_text='Potential Meaning Change')),
        ]:
            changelist.evaluate_attr(prev, self, attrib, test)

        changelist.evaluate_user_properties(prev, self)

        # Check changes to level labels
        for key in self.levels:
            changelist.evaluate_values(self, prev.levels.get(key),
                                       self.levels.get(key),
                                       ChangeTest(f'Level {key} label'))

        # Check Styles
        # pylint: disable=protected-access
        for key, value in prev._styles.items():
            if key not in self._styles:
                changelist.append(ChangeRecord(
                    value, 'Style Deleted',
                    None, None, impact_level=5,
                    impact_text='Potential meaning change'))
        for key, value in self._styles.items():
            if key not in prev._styles:
                changelist.append(ChangeRecord(
                    value, 'Style Added', None, None))
            else:
                changelist.extend(value.changes(prev._styles.get(key)))

        # Check Modules
        for key, value in prev._modules.items():
            if key not in self._modules:
                changelist.append(ChangeRecord(
                    value, 'Module Deleted',
                    None, None, impact_level=5,
                    impact_text='Potential loss of data'))
        for key, value in self._modules.items():
            if key not in prev._modules:
                changelist.append(ChangeRecord(
                    value, 'Module Added', None, None))
            else:
                changelist.extend(value.changes(prev._modules.get(key)))

        # Check Plates
        for key, value in prev._plates.items():
            if key not in self._plates:
                changelist.append(ChangeRecord(
                    value, 'Plate Deleted',
                    None, None, impact_level=10,
                    impact_text='Potential loss of data'))
        for key, value in self._plates.items():
            if key not in prev._plates:
                changelist.append(ChangeRecord(
                    value, 'Plate Added', None, None,
                    impact_text='Review exports'))
            else:
                changelist.extend(value.changes(prev._plates.get(key)))

        return changelist
