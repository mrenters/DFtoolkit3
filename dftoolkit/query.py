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
'''Query related classes'''

from datetime import datetime, date

#############################################################################
# extract_user, extract_date - returns user or date from a query timestamp
#############################################################################
def extract_user(user_ts):
    '''extract the username from a query timestamp'''
    if not user_ts:
        return None
    fields = user_ts.split(' ')
    return fields[0]

def extract_date(user_ts):
    '''extract the datetime from a query timestamp'''
    if not user_ts:
        return None
    fields = user_ts.split(' ')
    if len(fields) != 3:
        return None

    try:
        (year, month, day) = map(int, fields[1].split('/'))
        (hour, minute, second) = map(int, fields[2].split(':'))
    except ValueError:
        return None

    if year > 90:
        year += 1900
    else:
        year += 2000

    return datetime(year, month, day, hour, minute, second)

#############################################################################
# QCStatusMap - Reason Status Map
#############################################################################
class QCStatus:
    '''QC Status representation'''
    def __init__(self, label, is_resolved):
        self.label = label
        self.is_resolved = is_resolved

class QCStatusMap(dict):
    '''QC Status Map'''
    def __init__(self):
        super().__init__({
            0: QCStatus('Pending Review', False),
            1: QCStatus('Outstanding(New)', False),
            2: QCStatus('Outstanding(In Unsent Report)', False),
            3: QCStatus('Resolved N/A', True),
            4: QCStatus('Resolved Irrelevant', True),
            5: QCStatus('Resolved Corrected', True),
            6: QCStatus('Outstanding(In Sent Report)', False),
            7: QCStatus('Deleted', True)
        })

    def is_resolved(self, value):
        '''Returns whether this status is resolved or not'''
        entry = self.get(value)
        return entry.is_resolved if entry else False

    def label(self, status, simplify=False):
        '''Returns QC status label or resolved/unresolved if simplify'''
        if simplify:
            return 'Resolved' if self.is_resolved(status) else 'Outstanding'

        entry = self.get(status)
        return entry.label if entry else 'unknown'

    def labels(self, simplify=False):
        '''Returns a list of labels'''
        if simplify:
            return ['Outstanding', 'Resolved']
        return [status.label for _, status in sorted(self.items())]

#############################################################################
# QCTypeMap - QC Type Map
#############################################################################
class QCType:
    '''A QC type construct'''
    def __init__(self, label, autoresolve, sortorder):
        self.label = label
        self.autoresolve = autoresolve == 1
        self.sortorder = sortorder

    def __repr__(self):
        return '<QCType %s, %s, %d>' % (self.label, self.autoresolve,
                                        self.sortorder)

class QCTypeMap(dict):
    '''The QC Type Map'''
    def __init__(self):
        super().__init__({
            1: QCType('Missing', True, 0),
            2: QCType('Illegal', True, 0),
            3: QCType('Inconsistent', True, 0),
            4: QCType('Illegible', True, 0),
            5: QCType('Fax Noise', True, 0),
            6: QCType('Other', True, 0),
            21: QCType('Missing Page', False, 0),
            22: QCType('Overdue Visit', False, 0),
            23: QCType('EC Missing Page', False, 0)
        })

    @property
    def sorted_types(self):
        '''Return a list of QC type codes, sorted by priority'''
        types = sorted(self.items(), key=lambda x: (x[1].sortorder, x[0]))
        return [code for code, _ in types]

    def label(self, qc_type_code, simplify=False):
        '''returns the label for a QC type code'''

        # Coalesce EC Missing page to Missing Page if simplify is True
        if simplify and qc_type_code == 23:
            qc_type_code = 21

        qc_type = self.get(qc_type_code)
        return qc_type.label if qc_type else 'unknown'

    def labels(self, simplify=False):
        '''Returns a list of labels'''
        qctypes = list(self.items())
        if simplify:
            qctypes = list(filter(lambda x: x[0] != 23, qctypes))

        qctypes.sort(key=lambda x: (x[1].sortorder, x[0]))
        return [qctype.label for _, qctype in qctypes]

    def load(self, qcproblem_string):
        '''Loads a DFqcproblem_map style file'''
        codelist = {}
        for line in qcproblem_string.splitlines():
            fields = line.split('|')
            if len(fields) < 4:
                raise ValueError('Incorrectly formatted DFproblem_map entry: ' \
                             + line)

            try:
                code = int(fields[0])
                autoresolve = int(fields[2])
                sortorder = int(fields[3])
            except ValueError:
                raise ValueError('Incorrectly formatted DFproblem_map entry: ' \
                             + line)

            codelist[code] = QCType(fields[1], autoresolve, sortorder)
        self.update(codelist)

#############################################################################
# Query - A Quality Control Note
#############################################################################
class Query:
    '''Query (Quality Control note) representation'''
    def __init__(self, study, fields):
        if isinstance(fields, str):
            fields = fields.split('|')

        if len(fields) < 22:
            raise ValueError('Incorrectly formatted Query: ' + '|'.join(fields))

        self.study = study
        self.status = int(fields[0])
        self.level = int(fields[1])
        self.plate_num = int(fields[4])
        self.visit_num = int(fields[5])
        self.pid = int(fields[6])
        self.field_num = int(fields[7])+3
        self.site = study.sites.pid_to_site(self.pid)
        self.report = fields[9]
        self.page_num = int(fields[10])
        self.reply = fields[11]
        self.qc_description = fields[12]
        self.value = fields[13]
        self.qctype = int(fields[14])
        self.refax = int(fields[15])
        self.query = fields[16]
        self.note = fields[17]
        self.creation = fields[18]
        self.modification = fields[19]
        self.resolution = fields[20]
        self.usage = int(fields[21])

    def __lt__(self, other):
        if self.site.number < other.site.number:
            return True
        if self.site.number > other.site.number:
            return False
        if self.pid < other.pid:
            return True
        if self.pid > other.pid:
            return False
        if self.visit_num < other.visit_num:
            return True
        if self.visit_num > other.visit_num:
            return False
        if self.plate_num < other.plate_num:
            return True
        if self.plate_num > other.plate_num:
            return False
        if self.field_num < other.field_num:
            return True
        return False

    def status_decoded(self, simplify=False):
        '''return a decoded status label'''
        return self.study.qc_statuses.label(self.status, simplify)

    @property
    def is_pending(self):
        '''is this QC in pending state?'''
        return self.status == 0

    @property
    def is_internal(self):
        '''is this an internal query?'''
        return self.usage == 2

    @property
    def is_resolved(self):
        '''return whether this Query is resolved'''
        return self.study.qc_statuses.is_resolved(self.status)

    @property
    def page_query(self):
        '''return whether this a page query (missing page, overdue visit)'''
        return 21 <= self.qctype <= 23

    def qctype_decoded(self, simplify=False):
        '''returns the Query type label'''
        return self.study.qc_types.label(self.qctype, simplify)

    @property
    def visit(self):
        '''returns visit object'''
        return self.study.visit(self.visit_num)

    @property
    def visit_label(self):
        '''returns decoded visit label'''
        return self.study.visit_label(self.visit_num)

    @property
    def plate(self):
        '''returns plate object'''
        return self.study.plate(self.plate_num)

    @property
    def plate_label(self):
        '''returns decoded plate label'''
        return self.study.page_label(self.visit_num, self.plate_num)

    @property
    def field(self):
        '''returns the field object for this QC'''
        plate = self.plate
        return plate.field(self.field_num) if plate else None

    @property
    def description(self):
        '''returns field description from field definition'''
        field = self.field
        return field.description if field else ''

    @property
    def priority(self):
        '''returns QC priority'''
        field = self.field
        return field.priority if field else 5

    @property
    def usage_decoded(self):
        '''decode the Query use field to external/internal'''
        return 'Internal' if self.usage == 2 else 'External'

    @property
    def refax_decoded(self):
        '''decode the refax field into yes/no'''
        return 'Yes' if self.refax == 2 else 'No'

    @property
    def creator(self):
        '''returns user who created query'''
        return extract_user(self.creation)

    @property
    def created(self):
        '''returns datetime of query creation'''
        return extract_date(self.creation)

    @property
    def age(self):
        '''returns age of query if unresolved'''
        created = self.created
        if not created or self.is_resolved:
            return None
        return (date.today() - created.date()).days

    @property
    def modifier(self):
        '''returns user who modified query'''
        return extract_user(self.modification)

    @property
    def modified(self):
        '''returns datetime of query modification'''
        return extract_date(self.modification)

    @property
    def resolver(self):
        '''returns user who resolved query'''
        return extract_user(self.resolution)

    @property
    def resolved(self):
        '''returns datetime of query resolution'''
        return extract_date(self.resolution)