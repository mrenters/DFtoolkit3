#!/bin/env python
#
# Copyright 2021-2023, Martin Renters
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
'''
A Database Export Program to export plate, module, query and reason data
'''

import re
from datetime import datetime, date
from os import makedirs
from os.path import join as path_join, dirname as path_dirname
from .rangelist import SiteList, SubjectList, PlateList

def timestamp_to_iso8601(value):
    '''Convert a DF style YY/MM/DD HH:MM:SS timestamp to a datetime'''
    if not value:
        return None
    fields = value.split(' ')
    if len(fields) != 2:
        return None

    try:
        (year, month, day) = map(int, fields[0].split('/'))
        (hour, minute, second) = map(int, fields[1].split(':'))
    except ValueError:
        return None

    year += 1900 if year > 90 else 2000

    return datetime(year, month, day, hour, minute, second)

def unicode_warning(identifier, text):
    '''Check for non-ASCII characters and issue a warning'''
    if not text:
        return
    location = ''
    warn = False
    for char in text:
        if ord(char) > 127:
            location += '^'
            warn = True
        else:
            location += ' '

    if warn:
        print('WARNING: Non-ASCII character(s) in ' + identifier)
        print('         ' + text)
        print('         ' + location.rstrip())

def sas_label_quote(text):
    '''Change single quotes to double single quotes for SAS label strings'''
    return text.replace("'", "''").replace('\n', ' ')

def sas_data_cleanup(text):
    '''Replace \n with a space and | with \\| in data strings'''
    return text.replace('\n', ' ').replace('|', '\\|')

class FieldProperties:
    '''A class to hold FieldRef properties that need to be accessible'''
    def __init__(self):
        self.max_len = 0
        self.is_coded = False
        self.allows_partial_date = False

    def set_length(self, length):
        '''set the fieldrefs maximum length'''
        self.max_len = max(self.max_len, length)

    def set_decodable(self, codes):
        '''Track whether this field has coding associated with it'''
        self.is_coded |= bool(codes)

    def set_partial_date(self, partial_date):
        '''Check whether this data format supports partial dates'''
        self.allows_partial_date |= partial_date

class DatasetColumn:
    '''The representation of a dataset column'''
    def __init__(self, name, attrib):
        self.name = name
        self.decode_type = 'none'
        self.data_type = attrib.get('data_type', 'String')
        self.is_coded = self.data_type in ('Choice', 'Check')
        self.allows_partial_date = attrib.get('allows_partial_date', False)
        self.data_format = attrib.get('data_format', '')
        self.data_len = attrib.get('data_len')
        self.description = attrib.get('description')

    @classmethod
    def from_field(cls, field_name, field, data_len):
        '''Generate a DatasetColumn from setup Field data'''
        entry = cls(field_name, {
            'data_type': field.data_type,
            'data_len': data_len,
            'data_format': field.data_format,
            'allows_partial_date': field.allows_partial_date,
            'description': field.description
        })
        return entry

    @property
    def sas_informat(self):
        '''Generate SAS informat statement'''
        informat = None
        if self.data_type == 'Date':
            # Remove special characters from format
            simple_format = re.sub('[^dmy]', '', self.data_format.lower())
            simple_format = re.sub('dd+', 'd', simple_format)
            simple_format = re.sub('mm+', 'm', simple_format)
            simple_format = re.sub('yy+', 'y', simple_format)
            if simple_format == 'dmy':
                informat = 'DDMMYY{}'.format(len(self.data_format))
            elif simple_format == 'mdy':
                informat = 'MMDDYY{}'.format(len(self.data_format))
            elif simple_format == 'ymd':
                informat = 'YYMMDD{}'.format(len(self.data_format))
            else:
                print('unable to compute DATE informat for', self.data_format)
        elif self.data_type == 'Time':
            informat = 'time{}'.format(len(self.data_format))
        elif self.data_type == 'String' and self.data_len:
            informat = '$CHAR{}'.format(self.data_len)
        elif self.data_type == 'ISO8601':
            informat = 'e8601dt19'

        return informat

    @property
    def sas_input_name(self):
        '''Generate name for SAS input line - add $ for string fields'''
        return self.name + (' $' if self.data_type == 'String' else '')

    def sas_export_value(self, field):
        '''Return the string value to be exported for this field'''
        # If we're already a string (constant), then just return that
        if isinstance(field, str):
            return sas_data_cleanup(field)
        if isinstance(field, (date, datetime)):
            return field.isoformat()

        # If we're missing, return a missing value code
        if not field or field.missing_value:
            value = "' '" if self.data_type in (
                'String', 'Date', 'Time', 'ISO8601') else '.'
        else:
            # Otherwise decode if necessary
            value = field.value
            if self.decode_type == 'label':
                value = field.label
            elif self.decode_type == 'submission':
                value = field.submission

        return sas_data_cleanup(value)

    def set_decode_type(self, decode_type):
        '''Set column to decoded mode'''
        self.decode_type = decode_type
        if decode_type != 'none' and self.is_coded:
            self.data_type = 'String'

    def set_partial_date_handling(self, partial_date_mode):
        '''Set how to handle partial dates for this column'''
        if self.data_type == 'Date' and self.allows_partial_date:
            if partial_date_mode == 'character':
                self.data_type = 'String'

class Dataset:
    '''An abstract dataset representation'''
    def __init__(self):
        self.sas_output = None
        self.columns = []

    @property
    def name(self):
        '''return the name of the dataset'''
        return None

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'generic'

    def sas_open(self, datapath):
        '''Open the SAS data file for writing'''
        path = path_join(datapath, self.name + '.dat')
        self.sas_output = open(path, 'w', encoding='utf-8')

    def sas_close(self):
        '''Close the SAS data file'''
        if self.sas_output:
            self.sas_output.close()
            self.sas_output = None

    def sas_export(self, datavalues):
        '''Export data record'''
        record = [
            column.sas_export_value(datavalues.get(column.name)) \
            for column in self.columns
        ]
        self.sas_output.write(('|'.join(record)) + '\n')

    def set_decode_type(self, decode_type):
        '''Set Choice/Check fields to decoded mode'''
        for column in self.columns:
            column.set_decode_type(decode_type)

    def set_partial_date_handling(self, partial_date_mode):
        '''Set how partial dates are handled'''
        for column in self.columns:
            column.set_partial_date_handling(partial_date_mode)

class PlateDataset(Dataset):
    '''A representation of a plate dataset, using field alias columns'''
    def __init__(self, plate):
        Dataset.__init__(self)
        self.plate = plate
        fields = plate.fields
        self.columns = [
            DatasetColumn.from_field('DFSTATUS', fields[0],
                                     fields[0].export_max_storage),
            DatasetColumn.from_field('DFVALID', fields[1],
                                     fields[1].export_max_storage),
            DatasetColumn.from_field('DFRASTER', fields[2], 12),
            DatasetColumn('DFCREATE', {'data_type': 'ISO8601'}),
            DatasetColumn('DFMODIFY', {'data_type': 'ISO8601'}),
            DatasetColumn('DFCOUNTRY',
                          {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('DFSITE', {'data_type': 'Number'}),
            DatasetColumn('SUBJID', {'data_type': 'Number'}),
            DatasetColumn('VISIT', {'data_type': 'Number'}),
            DatasetColumn('VISITNAM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('PLATE', {'data_type': 'Number'})
        ]
        self.columns.extend(
            [DatasetColumn.from_field(field.expanded_alias, field,
                                      field.export_max_storage) \
             for field in fields[7:-3]])

    @property
    def name(self):
        '''returns the name of the plate dataset'''
        return 'PLATE{0:03d}'.format(self.plate.number)

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'plate'

    @property
    def description(self):
        '''returns the description of the dataset'''
        return self.plate.description

class ModuleDataset(Dataset):
    '''A representation of a module dataset, using field names as columns'''
    def __init__(self, module, dfsystem_module):
        Dataset.__init__(self)
        self.module = module
        status = dfsystem_module.field_by_name('DFSTATUS')
        valid = dfsystem_module.field_by_name('DFVALID')
        self.columns = [
            DatasetColumn.from_field('DFSTATUS', status,
                                     status.export_max_storage),
            DatasetColumn.from_field('DFVALID', valid,
                                     valid.export_max_storage),
            DatasetColumn('DFCREATE', {'data_type': 'ISO8601'}),
            DatasetColumn('DFMODIFY', {'data_type': 'ISO8601'}),
            DatasetColumn('DFCOUNTRY',
                          {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('DFSITE', {'data_type': 'Number'}),
            DatasetColumn('SUBJID', {'data_type': 'Number'}),
            DatasetColumn('VISIT', {'data_type': 'Number'}),
            DatasetColumn('VISITNAM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('PLATE', {'data_type': 'Number'}),
            DatasetColumn('MODULEID', {'data_type': 'Number'})
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return self.module.name

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'module'

    @property
    def description(self):
        '''return the description of the dataset'''
        return self.module.description

    def add_field(self, field_name, field, properties):
        '''Add a field to the module dataset'''
        datacol = DatasetColumn.from_field(field_name, field,
                                           properties.max_len)
        datacol.is_coded |= properties.is_coded
        datacol.allows_partial_date |= properties.allows_partial_date
        self.columns.append(datacol)

class QueryDataset(Dataset):
    '''A representation of a queries dataset'''
    def __init__(self):
        Dataset.__init__(self)
        self.columns = [
            DatasetColumn('DFSTATUS', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('DFSTCODE', {'data_type': 'Number'}),
            DatasetColumn('DFVALID', {'data_type': 'Number'}),
            DatasetColumn('DFCOUNTRY',
                          {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('DFSITE', {'data_type': 'Number'}),
            DatasetColumn('SUBJID', {'data_type': 'Number'}),
            DatasetColumn('VISIT', {'data_type': 'Number'}),
            DatasetColumn('VISITNAM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('PLATE', {'data_type': 'Number'}),
            DatasetColumn('FIELD', {'data_type': 'Number'}),
            DatasetColumn('ALIAS', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('DESC', {'data_type': 'String', 'data_len': 64}),
            DatasetColumn('REPORT', {'data_type': 'Number'}),
            DatasetColumn('PAGE', {'data_type': 'Number'}),
            DatasetColumn('PROBLEM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('REFAX', {'data_type': 'String', 'data_len': 8}),
            DatasetColumn('USAGE', {'data_type': 'String', 'data_len': 16}),
            DatasetColumn('VALUE', {'data_type': 'String', 'data_len': 150}),
            DatasetColumn('QUERY', {'data_type': 'String', 'data_len': 500}),
            DatasetColumn('REPLY', {'data_type': 'String', 'data_len': 500}),
            DatasetColumn('NOTE', {'data_type': 'String', 'data_len': 500}),
            DatasetColumn('CREATOR', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('CREATED', {'data_type': 'ISO8601'}),
            DatasetColumn('MODIFIER', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('MODIFIED', {'data_type': 'ISO8601'}),
            DatasetColumn('RESOLVER', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('RESOLVED', {'data_type': 'ISO8601'})
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return 'DFQUERIES'

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'metadata'

    @property
    def description(self):
        '''return the description of the dataset'''
        return 'Queries'

class ReasonDataset(Dataset):
    '''A representation of a reasons dataset'''
    def __init__(self):
        Dataset.__init__(self)
        self.columns = [
            DatasetColumn('DFSTATUS', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('DFVALID', {'data_type': 'Number'}),
            DatasetColumn('DFCOUNTRY',
                          {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('DFSITE', {'data_type': 'Number'}),
            DatasetColumn('SUBJID', {'data_type': 'Number'}),
            DatasetColumn('VISIT', {'data_type': 'Number'}),
            DatasetColumn('VISITNAM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('PLATE', {'data_type': 'Number'}),
            DatasetColumn('FIELD', {'data_type': 'Number'}),
            DatasetColumn('ALIAS', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('DESC', {'data_type': 'String', 'data_len': 64}),
            DatasetColumn('RSNCODE', {'data_type': 'String', 'data_len': 64}),
            DatasetColumn('RSNTEXT', {'data_type': 'String', 'data_len': 500}),
            DatasetColumn('CREATOR', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('CREATED', {'data_type': 'ISO8601'}),
            DatasetColumn('MODIFIER', {'data_type': 'String', 'data_len': 32}),
            DatasetColumn('MODIFIED', {'data_type': 'ISO8601'})
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return 'DFREASONS'

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'metadata'

    @property
    def description(self):
        '''return the description of the dataset'''
        return 'Reasons'

class SitesDataset(Dataset):
    '''A representation of a sites database'''
    def __init__(self):
        Dataset.__init__(self)
        self.columns = [
            DatasetColumn('DFSITE', {'data_type': 'Number'}),
            DatasetColumn('DFCOUNTRY',
                          {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('REGION', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('NAME', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('ADDRESS', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('FAX', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('CONTACT', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('PHONE', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('INVESTNM', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('INVESTPN', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('REPLYTO', {'data_type': 'String', 'data_len': 100}),
            DatasetColumn('TESTSITE', {'data_type': 'Number'}),
            DatasetColumn('BEGINDAT', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('ENDDAT', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('ENROLL', {'data_type': 'Number'}),
            DatasetColumn('PROTO1', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('PROTODT1', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('PROTO2', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('PROTODT2', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('PROTO3', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('PROTODT3', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('PROTO4', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('PROTODT4', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
            DatasetColumn('PROTO5', {'data_type': 'String', 'data_len': 30}),
            DatasetColumn('PROTODT5', {
                'data_type': 'Date',
                'data_len': 10,
                'data_format': 'YYYY/MM/DD'
            }),
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return 'DFSITES'

    @property
    def dataset_type(self):
        '''returns the type of the dataset'''
        return 'metadata'

    @property
    def description(self):
        '''return the description of the dataset'''
        return 'Sites'

class SAScontrol:
    '''A representation of a SAS control file'''
    def __init__(self, paths):
        self.datapath = paths.get('datapath', '.')
        libpath_plate = paths.get('libpath_plates', '.')
        libpath_module = paths.get('libpath_modules', '.')
        libpath_metadata = paths.get('libpath_metadata', '.')
        self.sas_control = [
            f'libname plate \'{libpath_plate}\';',
            f'libname module \'{libpath_module}\';',
            f'libname metadata \'{libpath_metadata}\';',
        ]
        self.datasets = []

    def __del__(self):
        for dataset in self.datasets:
            dataset.sas_close()

    def add_dataset(self, dataset):
        '''add a dataset to the control file'''
        self.datasets.append(dataset)
        dataset.sas_open(self.datapath)
        self.sas_control.extend([
            f'data {dataset.dataset_type}.{dataset.name}(COMPRESS=BINARY '
            f'label="{dataset.description}");',
            f'  infile \'{self.datapath}/{dataset.name}.dat\'',
            '    ENCODING="UTF-8" LRECL=16384 dlm=\'|\' missover dsd;',
        ])
        for field in dataset.columns:
            informat = field.sas_informat
            if informat:
                self.sas_control.append(f'  informat {field.name}' \
                                        f' {informat}. ;')
                if field.data_type in ('Date', 'Time', 'ISO8601'):
                    self.sas_control.append(f'    format {field.name}' \
                                            f' {informat}. ;')
        self.sas_control.append('  input')
        for field in dataset.columns:
            self.sas_control.append(f'    {field.sas_input_name}')

        self.sas_control.append('  ;')

        labels = [f'     {col.name} = \'{sas_label_quote(col.description)}\'' \
                  for col in dataset.columns if col.description]
        if labels:
            self.sas_control.append('  label')
            self.sas_control.extend(labels)
            self.sas_control.append(';\n')

        self.sas_control.append('\n')

    def control_file(self):
        '''returns the control file data'''
        return '\n'.join(self.sas_control)

class Exporter:
    '''a data exporter'''
    def __init__(self, study, args):
        self.study = study
        self.sitelist = args.get('sites', SiteList(default_all=True))
        self.idlist = args.get('ids', SubjectList(default_all=True))
        self.platelist = args.get('plates', PlateList(default_all=True))
        self.include_pending = args.get('pending', False)
        self.include_missing = args.get('missingrecords', False)
        self.include_reasons = args.get('reasons', False)
        self.include_queries = args.get('queries', False)
        self.partial_date_mode = args.get('partialdatemode', 'asis')
        self.datasets = {}

    def unicode_check(self):
        '''Check to see if there are any non-ASCII characters in setup'''
        for visit in self.study.visit_map:
            if visit.visit_type == 'C':
                continue
            unicode_warning('visit map Visit '+str(visit.visits), visit.label)
        for plate in self.study.plates:
            if plate.number not in self.platelist or plate.number > 500:
                continue
            for moduleref in plate.modulerefs:
                for field, value in moduleref.virtual_fields.items():
                    unicode_warning(f'Plate {plate.number}:'
                                    f'{moduleref.identifier} '
                                    f'module property {field.name}',
                                    value)
            for field in plate.fields:
                unicode_warning(f'Plate {plate.number} '
                                f'Field {field.number} Description',
                                field.description)
                for code, label, submission in field.codes:
                    unicode_warning(f'Plate {plate.number} '
                                    f'Field {field.number} Code {code} label',
                                    label)
                    unicode_warning(f'Plate {plate.number} '
                                    f'Field {field.number} '
                                    f'Code {code} submission',
                                    submission)

    def setup(self):
        '''build a list of datasets required for this export'''
        ref_fields = {}

        # Build a list of module fields that are used either explicitly
        # or as a result of module property name substitutions
        # e.g. XXTERM -> AETERM
        for plate in self.study.plates:
            if plate.number not in self.platelist or plate.number > 500:
                continue
            self.datasets[plate] = PlateDataset(plate)
            for moduleref in plate.modulerefs:
                for field, value in moduleref.virtual_fields.items():
                    if value:
                        ref_field = ref_fields.setdefault(
                            field, FieldProperties())
                        ref_field.set_length(len(value))
            # Skip DFsystem related fields as they are captured in the
            # module header already
            for fieldref in plate.fields[7:]:
                ref_field = ref_fields.setdefault(
                    fieldref.field, FieldProperties())
                ref_field.set_length(fieldref.export_max_storage)
                ref_field.set_decodable(fieldref.codes)
                ref_field.set_partial_date(fieldref.allows_partial_date)

        # Build a set of modules that are used by these plates and only
        # include the fields within those modules that are referenced at
        # least once
        for module in {field.module for field in ref_fields}:
            # Don't export DFSYSTEM as all the data is already in the other
            # modules
            if module.name == 'DFSYSTEM':
                continue
            module_ds = ModuleDataset(module,
                                      self.study.module_by_name('DFSYSTEM'))
            for field in filter(lambda x: x in ref_fields, module.fields):
                module_ds.add_field(field.name, field, ref_fields.get(field))
            self.datasets[module] = module_ds

        for dataset in self.datasets.values():
            dataset.set_partial_date_handling(self.partial_date_mode)

        if self.include_reasons:
            reasons = ReasonDataset()
            self.datasets[reasons] = reasons
        if self.include_queries:
            queries = QueryDataset()
            self.datasets[queries] = queries

        sites = SitesDataset()
        self.datasets[sites] = sites

    def decode_output(self, plate_decode_type, module_decode_type):
        '''turn on decode check/choice fields'''
        for dataset in self.datasets.values():
            if isinstance(dataset, ModuleDataset):
                dataset.set_decode_type(module_decode_type)
            else:
                dataset.set_decode_type(plate_decode_type)

    def export_plate(self, export_type, plate_dataset):
        '''export a plate including its modules'''
        modulerefs = plate_dataset.plate.modulerefs

        # Evaluate virtual fields
        # Virtual fields can be a string, or =expn (TODO)
        virtual_fields = {moduleref:{} for moduleref in modulerefs}
        for moduleref in modulerefs:
            for field, value in moduleref.virtual_fields.items():
                if value:
                    virtual_fields[moduleref][field.name] = value

        # Process each record for that plate
        for record in self.study.data(plate_dataset.plate, self.idlist,
                                      missing_records=self.include_missing):
            # only include pending records if explictly requested
            if record.pending and not self.include_pending:
                continue
            # get the current site number and skip if filtered
            site = self.study.sites.pid_to_site(record.pid)
            if site.number not in self.sitelist:
                continue
            field_values = record.field_values
            plate_datavalues = {
                'DFSTATUS': field_values[0], # first field is status
                'DFVALID': str(record.level),
                'DFRASTER': field_values[2],
                'DFSITE': str(site.number),
                'DFCOUNTRY': site.decoded_country,
                'SUBJID': str(record.pid),
                'VISIT': str(record.visit_num),
                'VISITNAM': self.study.visit_label(record.visit_num),
                'PLATE': str(record.plate_num),
                'DFCREATE': timestamp_to_iso8601(field_values[-2].value),
                'DFMODIFY': timestamp_to_iso8601(field_values[-1].value)
            }
            moduleref_datavalues = {
                moduleref: {
                    'DFSTATUS': field_values[0], # first field is status
                    'DFVALID': str(record.level),
                    'DFCREATE': timestamp_to_iso8601(field_values[-2].value),
                    'DFMODIFY': timestamp_to_iso8601(field_values[-1].value),
                    'DFSITE': str(site.number),
                    'DFCOUNTRY': site.decoded_country,
                    'SUBJID': str(record.pid),
                    'VISIT': str(record.visit_num),
                    'VISITNAM': self.study.visit_label(record.visit_num),
                    'PLATE': str(record.plate_num),
                    'MODULEID': str(moduleref.instance)
                } for moduleref in modulerefs
            }

            # Add in virtual fields
            for moduleref, fields in virtual_fields.items():
                for name, value in fields.items():
                    if value:
                        moduleref_datavalues[moduleref][name] = value

            # Add in field values from data record
            for fieldvalue in field_values:
                plate_datavalues[fieldvalue.expanded_alias] = fieldvalue
                moduleref = fieldvalue.field.moduleref
                moduleref_datavalues[moduleref][fieldvalue.name] = fieldvalue

            # Now export
            # Get the export function name by looking for an attribute
            # called export_type + '_export' - e.g. sas_export
            export_function = getattr(plate_dataset, export_type + '_export')
            export_function(plate_datavalues)
            for moduleref, data_values in moduleref_datavalues.items():
                # We don't export DFSYSTEM
                if moduleref.module.name == 'DFSYSTEM':
                    continue
                # A plate may contain a module but not use any of it's
                # variables. The export setup detects this and
                # won't generate a ModuleDataset object, so don't
                # try and export data to it now.
                module_dataset = self.datasets.get(moduleref.module)
                if not module_dataset:
                    continue
                export_function = getattr(module_dataset,
                                          export_type + '_export')
                export_function(data_values)

    def export_queries(self, export_type, dataset):
        '''export queries'''
        for query in self.study.queries(self.idlist):
            site = self.study.sites.pid_to_site(query.pid)
            if site.number not in self.sitelist:
                continue
            field = query.field
            data_values = {
                'DFSTATUS': query.status_decoded(simplify=True),
                'DFSTCODE': str(query.status),
                'DFVALID': str(query.level),
                'DFSITE': str(site.number),
                'DFCOUNTRY': site.decoded_country,
                'SUBJID': str(query.pid),
                'VISIT': str(query.visit_num),
                'VISITNAM': query.visit_label,
                'PLATE': str(query.plate_num),
                'FIELD': str(query.field_num),
                'ALIAS': field.expanded_alias,
                'DESC': field.description,
                'REPORT': query.report,
                'PAGE': str(query.page_num),
                'PROBLEM': query.qctype_decoded(),
                'REFAX': query.refax_decoded,
                'USAGE': query.usage_decoded,
                'VALUE': query.value,
                'QUERY': query.query,
                'REPLY': query.reply,
                'NOTE': query.note,
                'CREATOR': query.creator,
                'CREATED': query.created,
                'MODIFIER': query.modifier,
                'MODIFIED': query.modified,
                'RESOLVER': query.resolver,
                'RESOLVED': query.resolved
            }
            export_function = getattr(dataset, export_type + '_export')
            export_function(data_values)

    def export_reasons(self, export_type, dataset):
        '''export reasons'''
        for reason in self.study.reasons(self.idlist):
            site = self.study.sites.pid_to_site(reason.pid)
            if site.number not in self.sitelist:
                continue
            field = reason.field
            data_values = {
                'DFSTATUS': reason.status_decoded(),
                'DFVALID': str(reason.level),
                'DFSITE': str(site.number),
                'DFCOUNTRY': site.decoded_country,
                'SUBJID': str(reason.pid),
                'VISIT': str(reason.visit_num),
                'VISITNAM': reason.visit_label,
                'PLATE': str(reason.plate_num),
                'FIELD': str(reason.field_num),
                'ALIAS': field.expanded_alias,
                'DESC': field.description,
                'RSNCODE': reason.reason_code,
                'RSNTEXT': reason.reason_text,
                'CREATOR': reason.creator,
                'CREATED': reason.created,
                'MODIFIER': reason.modifier,
                'MODIFIED': reason.modified
            }
            export_function = getattr(dataset, export_type + '_export')
            export_function(data_values)

    def export_sites(self, export_type, dataset):
        '''export sites'''
        for site in self.study.sites:
            if site.number not in self.sitelist:
                continue
            data_values = {
                'DFSITE': str(site.number),
                'DFCOUNTRY': site.decoded_country,
                'REGION': site.region,
                'NAME': site.name,
                'ADDRESS': site.address,
                'FAX': site.fax,
                'CONTACT': site.contact,
                'PHONE': site.contact,
                'INVESTNM': site.investigator,
                'INVESTPN': site.investigator_phone,
                'REPLYTO': site.reply_address,
                'BEGINDAT': site.begin_date,
                'ENDDAT': site.end_date,
                'TESTSITE': site.test_site,
                'ENROLL': site.enroll,
                'PROTO1': site.protocol1,
                'PROTODT1': site.protocol1_date,
                'PROTO2': site.protocol2,
                'PROTODT2': site.protocol2_date,
                'PROTO3': site.protocol3,
                'PROTODT3': site.protocol3_date,
                'PROTO4': site.protocol4,
                'PROTODT4': site.protocol4_date,
                'PROTO5': site.protocol5,
                'PROTODT5': site.protocol5_date,
            }
            export_function = getattr(dataset, export_type + '_export')
            export_function(data_values)

    def sas_export(self, paths):
        '''do an export to SAS format'''
        sas_control = SAScontrol(paths)
        scriptname = paths.get('script', 'import.sas')
        dirname = path_dirname(scriptname)
        if dirname:
            makedirs(dirname, exist_ok=True)
        makedirs(paths.get('datapath', '.'), exist_ok=True)
        for dataset in sorted(self.datasets.values(), key=lambda x: x.name):
            sas_control.add_dataset(dataset)
        for dataset in self.datasets.values():
            # Process only Plates, Modules are generated from those
            if isinstance(dataset, PlateDataset):
                self.export_plate('sas', dataset)
            elif isinstance(dataset, QueryDataset):
                self.export_queries('sas', dataset)
            elif isinstance(dataset, ReasonDataset):
                self.export_reasons('sas', dataset)
            elif isinstance(dataset, SitesDataset):
                self.export_sites('sas', dataset)

        with open(scriptname, 'w', encoding='utf-8') as output:
            output.write(sas_control.control_file())
