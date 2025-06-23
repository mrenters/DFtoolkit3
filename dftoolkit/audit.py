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
'''Classes to reformat audit information'''

from typing import NamedTuple

from .record import missing_codes
from .texttools import bold_font, regular_font, italic_font, htmlify

class AuditRecOps(NamedTuple):
    '''An audit transaction for a field with detailed operations'''
    who: str
    tdate: str
    ttime: str
    funiqueid: int
    fnum: int
    desc: str
    ops: list


class AuditOps:
    '''Assemble Audit Operations'''
    def __init__(self, study, sql):
        self.study = study
        self.sql = sql

    def decode_value(self, val, val_decoded):
        '''Decode a field value, possibly missing or code with label'''
        missing_label = self.study.missingmap.get(val)
        if missing_label is not None:
            return '[' + val + ', ' + missing_label + ']'

        if val and val_decoded:
            return val + ', ' + val_decoded

        if not val:
            return '[blank]'

        return val

    def audit_ops_data(self, this_rec, op_list):
        '''Handle generating data related audit operations'''
        oldval = self.decode_value(this_rec.oldval,
                                   this_rec.oldval_decoded)
        newval = self.decode_value(this_rec.newval,
                                   this_rec.newval_decoded)

        if this_rec.op == 'N':
            if this_rec.status == 0:
                reason = missing_codes.get(this_rec.code,
                                           'Other Reason')
                if this_rec.reason:
                    reason += ' [' + this_rec.reason + ']'
                op_list.append(('d', htmlify(reason, regular_font())))
            else:
                op_list.append(
                    ('d', htmlify('Initial Value: ', regular_font()) + \
                     htmlify(newval, bold_font()))
                )

        elif this_rec.op == 'C':
            if len(oldval) > 100 or len(newval) > 100:
                op_list.append(
                    ('d', htmlify('Changed Value: ', regular_font()) + \
                     htmlify(newval, bold_font()))
                )
            else:
                op_list.append(
                    ('d', htmlify('Changed Value: ', regular_font()) + \
                     htmlify(oldval + ' \u2192 ' + newval, bold_font()))
                )
        elif this_rec.op == 'D':
            op_list.append(
                ('d', htmlify('Data Record Deleted', regular_font()))
            )

    def audit_ops_query(self, this_rec, op_list):
        '''Handle generating query related audit operations'''
        if this_rec.metafnum not in (0, 1, 12, 17, 18):
            return
        qctype = self.study.qc_types.label(int(this_rec.code))
        label = ''
        value = this_rec.newval
        if this_rec.metafnum == 1:
            if this_rec.status in (2, 6):
                return
            label = 'Status'
            value = self.study.qc_statuses.label(int(this_rec.status))

        elif this_rec.metafnum == 12:
            if this_rec.op == 'N' and not value:
                return
            label = 'Reply'
        elif this_rec.metafnum == 17:
            label = 'Query'
        elif this_rec.metafnum == 18:
            if this_rec.op == 'N' and not value:
                return
            label = 'Note'

        if this_rec.op in ('N', 'C'):
            op_list.append(
                ('q', htmlify(f'QC {label} ({qctype}): ', regular_font()) + \
                 htmlify(value, italic_font()))
            )
        elif this_rec.op == 'D':
            op_list.append(('q', htmlify(f'QC Deleted ({qctype})',
                                         regular_font())))

    def audit_ops_reason(self, this_rec, op_list):
        '''Handle generating reason related audit operations'''
        if this_rec.metafnum not in (0, 1, 10):
            return
        if this_rec.op in ('N', 'C'):
            if this_rec.metafnum == 0:
                op_list.append(('r', htmlify(this_rec.reason, italic_font())))
            elif this_rec.metafnum == 1:
                op_list.append(
                    ('r', htmlify('Reason Status: ', regular_font()) + \
                     htmlify(self.study.reason_status(this_rec.status),
                             italic_font()))
                )
            elif this_rec.metafnum == 10:
                op_list.append(
                    ('r', htmlify('Reason Text: ', regular_font()) + \
                     htmlify(this_rec.reason, italic_font()))
                )
        elif this_rec.op == 'D':
            if this_rec.metafnum == 0 and this_rec.funiqueid == 0:
                op_list.append(('r', htmlify(this_rec.reason, italic_font())))
            else:
                op_list.append(('r', htmlify('Reason Deleted', regular_font())))

    def auditop_records(self, record, blinded):
        '''Returns a list of audit operations for the specified keys'''
        # Group the audit records into transactions
        audit_ops = []
        last_rec = None
        unique_ids = self.study.field_uniqueids

        for this_rec in self.sql.audit_by_keys(record.pid, record.visit_num,
                                               record.plate_num):
            if 0 < this_rec.funiqueid < 10000:
                continue

            # Get the field information and skip if the field has been deleted
            field = unique_ids.get(this_rec.funiqueid)
            if this_rec.funiqueid and not field:
                continue
            # Ignore records for blinded fields in blinded mode
            if field and blinded  and field.blinded:
                continue

            if last_rec != (this_rec.tdate, this_rec.ttime, this_rec.funiqueid):
                last_rec = (this_rec.tdate, this_rec.ttime, this_rec.funiqueid)
                audit_op = AuditRecOps(
                    this_rec.who, this_rec.tdate,
                    this_rec.ttime, this_rec.funiqueid,
                    this_rec.fnum, this_rec.desc, [])
                audit_ops.append(audit_op)

            if this_rec.rectype == 'd':
                self.audit_ops_data(this_rec, audit_op.ops)
            elif this_rec.rectype == 'q':
                self.audit_ops_query(this_rec, audit_op.ops)
            elif this_rec.rectype == 'r':
                self.audit_ops_reason(this_rec, audit_op.ops)

        return audit_ops
