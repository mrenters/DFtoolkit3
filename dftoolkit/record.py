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
'''A module to handle DFdiscover records'''

missing_codes = {
    '1': 'Subject Missed Visit',
    '2': 'Exam or Test Not Performed',
    '3': 'Data Not Available',
    '4': 'Subject Refused',
    '5': 'Subject Moved Away',
    '6': 'Subject Lost to Follow-up',
    '7': 'Subject Died',
    '8': 'Subject Terminated due to Study Illness',
    '9': 'Subject Terminated due to Other Illness',
    '10': 'Other Reason'
}

class Attachment:
    '''A class that handles media attachments'''
    def __init__(self, raster, primary, timestamp):
        self.raster = raster
        self.primary = primary
        self.timestamp = timestamp
        self.data = None

    def load(self, api):
        '''Get the attachment from the server'''
        try:
            self.data = api.attachment(self.raster)
        except Exception:
            return False

        return True

    @property
    def is_pdf(self):
        '''Is this attachment a PDF?'''
        return self.data and self.data[0:4] == b'%PDF'

class FieldValue:
    '''A class for combining a field with its value'''
    def __init__(self, field, value):
        self.field = field
        self.value = value

    @property
    def name(self):
        'returns the field name'
        return self.field.name

    @property
    def missing_value(self):
        'returns True/False if value is a missing value code'
        missing, _ = self.field.missing_value(self.value)
        return missing

    @property
    def missing_label(self):
        'returns True/False if value is a missing value code'
        _, label = self.field.missing_value(self.value)
        return label

    @property
    def expanded_alias(self):
        'returns the field expanded alias'
        return self.field.expanded_alias

    @property
    def label(self):
        'returns the field label'
        _, label, _ = self.field.decode_with_submission(self.value)
        return label

    @property
    def submission(self):
        'returns the field submission label or codiding label if not available'
        _, label, submission = self.field.decode_with_submission(self.value)
        return submission or label

    def __repr__(self):
        return '<FieldValue %s=%s>' % (self.field.name, self.value)


class Record:
    '''A class to encapsulate a DFdiscover record'''

    def __init__(self, study, datarec):
        self.study = study
        self.fields = datarec.split('|')
        self._attachments = []

    @property
    def missing(self):
        '''Is this a lost/missing record'''
        return self.fields[0] == '0'

    @property
    def missing_reason(self):
        '''Returns the reason this record is missing'''
        reason = ''
        if self.missing:
            reason = missing_codes.get(self.fields[7], 'Other Reason')
            if self.fields[8]:
                reason = reason + ' [' + self.fields[8] + ']'

        return reason

    @property
    def final(self):
        '''does this record have final status?'''
        return self.fields[0] == '1'

    @property
    def deleted(self):
        '''Is this a deleted record'''
        return self.fields[0] == '7'

    @property
    def deleted_reason(self):
        '''Returns the reason this record was deleted'''
        return self.fields[7] if self.deleted else ''

    @property
    def status(self):
        '''Return the status for this record'''
        return int(self.fields[0])

    @property
    def pending(self):
        '''Is this a pending record'''
        return self.status == 3

    @property
    def secondary(self):
        '''Is this a secondary record'''
        return 4 <= self.status <= 6

    @property
    def level(self):
        '''Return the level for this record'''
        return int(self.fields[1])

    @property
    def raster(self):
        '''Return the raster ID for this record'''
        return self.fields[2]

    def has_attachment(self, include_secondaries=False):
        '''Does this record have an attachment'''
        if not include_secondaries:
            attachments = self.raster[4] == '/' and \
                self.raster != '0000/0000000'
        else:
            attachments = len(self._attachments)
        return attachments

    def attachments(self, include_secondaries=False):
        '''Get a list of attachments for this record'''
        attachments = self._attachments
        if not include_secondaries:
            attachments = filter(lambda x: x.primary, attachments)
        return sorted(attachments, key=lambda x: (not x.primary, x.raster))

    def add_attachment(self, raster, primary, timestamp):
        '''Add an attachment to the record'''
        self._attachments.append(Attachment(raster, primary, timestamp))

    @property
    def keys(self):
        '''The record keys in display format'''
        return '{}, {}, {}'.format(self.pid, self.visit_num, self.plate_num)

    @property
    def keys_bookmark(self):
        '''The record keys in bookmark format'''
        return '{}_{}_{}'.format(self.pid, self.visit_num, self.plate_num)

    @property
    def plate_num(self):
        '''Return the plate number for this record'''
        return int(self.fields[4])

    @property
    def plate(self):
        '''Return the plate definition for this record'''
        return self.study.plate(self.plate_num)

    @property
    def page_label(self):
        '''Return the expanded page label'''
        return self.study.page_label(self.visit_num, self.plate_num)

    @property
    def visit_num(self):
        '''Return the number for this record'''
        return int(self.fields[5])

    @property
    def visit(self):
        '''Return the visit definition for this record'''
        return self.study.visit(self.visit_num)

    @property
    def visit_label(self):
        '''Return the expanded visit label'''
        return self.study.visit_label(self.visit_num)

    @property
    def pid(self):
        '''Returns patient ID'''
        return int(self.fields[6])

    def field(self, num):
        '''Returns value of field num'''
        return self.fields[num-1] if 0 < num <= len(self.fields) else ''

    def field_missing_value(self, num):
        '''Does this field contain a missing value?'''
        return self.field(num) in self.study.missingmap

    def field_missing_value_label(self, num):
        '''What is the missing value label'''
        return self.study.missingmap.get(self.field(num))

    @property
    def field_values(self):
        '''return the field values as a list of FieldValue objects.'''
        plate_fields = self.plate.fields

        # Return missing (lost) record with just keys and creation/modification
        if self.missing:
            fields = [(field, field.number) \
                      for field in plate_fields[0:7]]
            # DFCREATE/DFMODIFY are in fields 10,11 in missing records
            fields.append((plate_fields[-2], 10))
            fields.append((plate_fields[-1], 11))
        else:
            fields = [(field, field.number) for field in plate_fields]

        return [FieldValue(field, self.field(fnum)) for field, fnum in fields]

    def __repr__(self):
        return '<Record %d, %d, %d>' % (self.pid, self.visit_num,
                                        self.plate_num)
