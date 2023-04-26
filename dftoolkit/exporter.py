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
from datetime import datetime
from os.path import join as path_join
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

class FieldProperties:
    '''A class to hold FieldRef properties that need to be accessible'''
    def __init__(self):
        self.max_len = 0
        self.is_coded = False

    def set_length(self, length):
        '''set the fieldrefs maximum length'''
        self.max_len = max(self.max_len, length)

    def set_decodable(self, codes):
        '''Track whether this field has coding associated with it'''
        self.is_coded = self.is_coded | bool(codes)

class DatasetColumn:
    '''The representation of a dataset column'''
    def __init__(self, name, data_type='String', data_len=None):
        self.name = name
        self.decode_type = 'none'
        self.data_type = data_type
        self.is_coded = data_type in ('Choice', 'Check')
        self.data_format = ''
        self.data_len = data_len

    @classmethod
    def from_field(cls, field_name, field, data_len):
        '''Generate a DatasetColumn from setup Field data'''
        entry = cls(field_name, field.data_type)
        entry.data_len = data_len
        entry.data_format = field.data_format
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
            return field
        if isinstance(field, datetime):
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
        return value

    def set_decode_type(self, decode_type):
        '''Set column to decoded mode'''
        self.decode_type = decode_type
        if decode_type != 'none' and self.is_coded:
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

    def sas_open(self, datapath):
        '''Open the SAS data file for writing'''
        path = path_join(datapath, self.name + '.dat')
        self.sas_output = open(path, 'w')

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
            DatasetColumn('DFCREATE', 'ISO8601'),
            DatasetColumn('DFMODIFY', 'ISO8601'),
            DatasetColumn('DFCOUNTRY', 'String', 100),
            DatasetColumn('DFSITE', 'Number'),
            DatasetColumn('SUBJID', 'Number'),
            DatasetColumn('VISIT', 'Number'),
            DatasetColumn('VISITNAM', 'String', 100),
            DatasetColumn('PLATE', 'Number')
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
            DatasetColumn('DFCREATE', 'ISO8601'),
            DatasetColumn('DFMODIFY', 'ISO8601'),
            DatasetColumn('DFCOUNTRY', 'String', 100),
            DatasetColumn('DFSITE', 'Number'),
            DatasetColumn('SUBJID', 'Number'),
            DatasetColumn('VISIT', 'Number'),
            DatasetColumn('VISITNAM', 'String', 100),
            DatasetColumn('PLATE', 'Number'),
            DatasetColumn('MODULEID', 'Number')
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return self.module.name

    @property
    def description(self):
        '''return the description of the dataset'''
        return self.module.description

    def add_field(self, field_name, field, properties):
        '''Add a field to the module dataset'''
        datacol = DatasetColumn.from_field(field_name, field,
                                           properties.max_len)
        datacol.is_coded |= properties.is_coded
        self.columns.append(datacol)

class QueryDataset(Dataset):
    '''A representation of a queries dataset'''
    def __init__(self):
        Dataset.__init__(self)
        self.columns = [
            DatasetColumn('DFSTATUS', 'String', 30),
            DatasetColumn('DFSTCODE', 'Number'),
            DatasetColumn('DFVALID', 'Number'),
            DatasetColumn('DFCOUNTRY', 'String', 100),
            DatasetColumn('DFSITE', 'Number'),
            DatasetColumn('SUBJID', 'Number'),
            DatasetColumn('VISIT', 'Number'),
            DatasetColumn('VISITNAM', 'String', 100),
            DatasetColumn('PLATE', 'Number'),
            DatasetColumn('FIELD', 'Number'),
            DatasetColumn('ALIAS', 'String', 32),
            DatasetColumn('DESC', 'String', 64),
            DatasetColumn('REPORT', 'Number'),
            DatasetColumn('PAGE', 'Number'),
            DatasetColumn('PROBLEM', 'String', 100),
            DatasetColumn('REFAX', 'String', 8),
            DatasetColumn('USAGE', 'String', 16),
            DatasetColumn('VALUE', 'String', 150),
            DatasetColumn('QUERY', 'String', 500),
            DatasetColumn('REPLY', 'String', 500),
            DatasetColumn('NOTE', 'String', 500),
            DatasetColumn('CREATOR', 'String', 32),
            DatasetColumn('CREATED', 'ISO8601'),
            DatasetColumn('MODIFIER', 'String', 32),
            DatasetColumn('MODIFIED', 'ISO8601'),
            DatasetColumn('RESOLVER', 'String', 32),
            DatasetColumn('RESOLVED', 'ISO8601')
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return 'DFQUERIES'

    @property
    def description(self):
        '''return the description of the dataset'''
        return 'Queries'

class ReasonDataset(Dataset):
    '''A representation of a reasons dataset'''
    def __init__(self):
        Dataset.__init__(self)
        self.columns = [
            DatasetColumn('DFSTATUS', 'String', 30),
            DatasetColumn('DFVALID', 'Number'),
            DatasetColumn('DFCOUNTRY', 'String', 100),
            DatasetColumn('DFSITE', 'Number'),
            DatasetColumn('SUBJID', 'Number'),
            DatasetColumn('VISIT', 'Number'),
            DatasetColumn('VISITNAM', 'String', 100),
            DatasetColumn('PLATE', 'Number'),
            DatasetColumn('FIELD', 'Number'),
            DatasetColumn('ALIAS', 'String', 32),
            DatasetColumn('DESC', 'String', 64),
            DatasetColumn('RSNCODE', 'String', 64),
            DatasetColumn('RSNTEXT', 'String', 500),
            DatasetColumn('CREATOR', 'String', 32),
            DatasetColumn('CREATED', 'ISO8601'),
            DatasetColumn('MODIFIER', 'String', 32),
            DatasetColumn('MODIFIED', 'ISO8601')
        ]

    @property
    def name(self):
        '''return the name of the dataset'''
        return 'DFREASONS'

    @property
    def description(self):
        '''return the description of the dataset'''
        return 'Reasons'


class SAScontrol:
    '''A representation of a SAS control file'''
    def __init__(self, libname, libpath, datapath):
        self.libname = libname
        self.datapath = datapath
        self.sas_control = [f'libname {libname} \'{libpath}\';']
        self.datasets = []

    def __del__(self):
        for dataset in self.datasets:
            dataset.sas_close()

    def add_dataset(self, dataset):
        '''add a dataset to the control file'''
        self.datasets.append(dataset)
        dataset.sas_open(self.datapath)
        self.sas_control.extend([
            f'data {self.libname}.{dataset.name}(label="{dataset.description}");',
            f'  infile \'{self.datapath}/{dataset.name}.dat\'',
            '    LRECL=16384 dlm=\'|\' missover dsd;',
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

        self.sas_control.append(';\n')

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
        self.datasets = {}

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

        if self.include_reasons:
            reasons = ReasonDataset()
            self.datasets[reasons] = reasons
        if self.include_queries:
            queries = QueryDataset()
            self.datasets[queries] = queries

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
                'DFCOUNTRY': site.country,
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
                    'DFCOUNTRY': site.country,
                    'SUBJID': str(record.pid),
                    'VISIT': str(record.visit_num),
                    'VISITNAM': self.study.visit_label(record.visit_num),
                    'PLATE': str(record.plate_num),
                    'MODULEID': str(moduleref.instance)
                } for moduleref in modulerefs
            }

            # Add in virtual fields
            for moduleref in modulerefs:
                for field, value in moduleref.virtual_fields.items():
                    if value:
                        moduleref_datavalues[moduleref][field.name] = value

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
                'DFCOUNTRY': site.country,
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
                'DFCOUNTRY': site.country,
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

    def sas_export(self, scriptname, libname, libpath, datapath):
        '''do an export to SAS format'''
        sas_control = SAScontrol(libname, libpath, datapath)
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

        with open(scriptname, 'w') as output:
            output.write(sas_control.control_file())
