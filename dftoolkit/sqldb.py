#
# Copyright 2021-2022, Martin Renters
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
'''Class for dealing with intermediate SQL database for closeout'''

import logging
import re
import sqlite3

from typing import NamedTuple

from .rangelist import SubjectList
from .record import Record

logger = logging.getLogger(__name__)

KEY_CHANGE_REASON = 'Keys changed from ['

db_statements = [
    '''pragma page_size=4096''',
    '''pragma cache_size=40000''',
    '''pragma locking_mode=EXCLUSIVE''',
    '''drop table if exists data''',
    '''drop table if exists deleted''',
    '''drop table if exists secondaries''',
    '''drop table if exists attachments''',
    '''drop table if exists audit''',
    '''drop table if exists shared_strings''',
    '''create table data (
        pid int not null,
        visit int not null,
        plate int not null,
        level int not null,
        data text)''',
    '''create table deleted (
        pid int not null,
        visit int not null,
        plate int not null,
        level int not null,
        data text)''',
    '''create table attachments (
        pid int not null,
        visit int not null,
        plate int not null,
        raster text,
        isprimary int,
        ts int)''',
    '''create table audit (
        pid int not null,
        visit int not null,
        plate int not null,
        op text not null,
        tdate text not null,
        ttime text not null,
        who text not null,
        rectype text not null,
        status int not null,
        level int not null,
        code text,
        reason text,
        metafnum int not null,
        funiqueid int not null,
        fnum int not null,
        fdescid int not null,
        oldval text,
        newval text,
        oldvaldec text,
        newvaldec text
        )''',
    '''create table shared_strings (
        id int not null primary key,
        string text)'''
]

class AuditRec(NamedTuple):
    '''A raw audit record from the database'''
    who: str
    tdate: str
    ttime: str
    status: int
    op: str
    rectype: str
    funiqueid: int
    fnum: int
    metafnum: int
    code: str
    reason: str
    desc: str
    oldval: str
    newval: str
    oldval_decoded: str
    newval_decoded: str

SQL_AUDITRECS = '''
select a.who, a.tdate, a.ttime, a.status, a.op, a.rectype, a.funiqueid,
    a.fnum, a.metafnum, a.code, a.reason, s.string, a.oldval, a.newval,
    a.oldvaldec, a.newvaldec
from audit a
join shared_strings s on a.fdescid = s.id
where a.pid=? and a.visit=? and a.plate=?
order by a.tdate, a.ttime
'''

def parse_key_change(reason):
    '''Parse a Key changed from [n,n,n] to [n,n,n]: why string and return the
       new keys'''
    keys = re.findall(r'\[\d+,\d+,\d+]', reason)
    if len(keys) < 2:
        return None, None, None
    try:
        # Get second set of keys and strip [ and ]
        newkeys = keys[1][1:-1]
        return tuple(map(int, newkeys.split(',')))
    except ValueError:
        pass

    return None, None, None

class SQLDB:
    '''Intermediate SQL database representation'''
    def __init__(self, dbname):
        '''Connect to the SQL database'''
        self.sql = sqlite3.connect(dbname)

    def initialize(self):
        '''Initialize the database'''
        for statement in db_statements:
            self.sql.execute(statement)

    def _potential_deleted(self, pid, visit_num, plate_num, level, reason,
                           force_update):
        '''Insert or update deleted record markers'''
        sql = self.sql
        # Does data record exist?
        data_cursor = sql.execute('select 1 from data where '
                                  'pid=? and visit=? and plate=?',
                                  (pid, visit_num, plate_num))
        if data_cursor.fetchone():
            return

        record = '7|{0}|0000/0000000|0|{1}|{2}|{3}|{4}'.format(level,
                                                               plate_num,
                                                               visit_num,
                                                               pid, reason)
        data_cursor = sql.execute('select 1 from deleted where '
                                  'pid=? and visit=? and plate=?',
                                  (pid, visit_num, plate_num))
        if data_cursor.fetchone():
            if force_update:
                data_cursor = sql.execute('update deleted set data=? where '
                                          'pid=? and visit=? and plate=?',
                                          (record, pid, visit_num, plate_num))
        else:
            data_cursor = sql.execute('insert into deleted values '
                                      '(?, ?, ?, ?, ?)',
                                      (pid, visit_num, plate_num,
                                       level, record))

    def populate(self, study, subjects=SubjectList(default_all=True)):
        '''Populate SQL database with study data and audit'''
        self.populate_data(study, subjects)
        self.populate_audit(study, subjects)

    def populate_data(self, study, subjects=SubjectList(default_all=True)):
        '''Populate SQL database with study data'''
        sql = self.sql
        for plate in study.plates:
            logger.info('Importing Plate %d...', plate.number)
            for record in study.api.data(plate, subjects, missing_records=True,
                                         secondary_records=True):
                fields = record.split('|')
                pid = int(fields[6])
                visit_num = int(fields[5])
                plate_num = int(fields[4])
                status = int(fields[0])
                level = int(fields[1])
                raster = fields[2]

                if status <= 3:
                    sql.execute('insert into data values(?, ?, ?, ?, ?)',
                                (pid, visit_num, plate_num, level, record))
                if raster[4] == '/' and raster != '0000/0000000':
                    timestamp = study.api.attachment_context(raster)
                    sql.execute('insert into attachments '
                                'values(?, ?, ?, ?, ?, ?)',
                                (pid, visit_num, plate_num, raster, status <= 3,
                                 timestamp))
        sql.commit()
        logger.info('Creating index on data files...')
        sql.execute('''create index data_keys on data(pid, visit, plate)''')
        logger.info('Creating index on attachments...')
        sql.execute('''create index attachment_keys on
                       attachments(pid, visit, plate)''')

    def populate_audit(self, study, subjects=SubjectList(default_all=True)):
        '''Populate SQL database with study data'''
        sql = self.sql
        sstrings = {}
        ssid_seq = 0
        logger.info('Importing audit trail...')
        for record in study.api.audit(subjects):
            (operation, date, time, who, pid, visit_num, plate_num, uniqueid,
             metafnum, status, level, _, codevalue, codetext,
             oldval, newval, fnum, fdesc, dec_oldval,
             dec_newval) = record.split('|')

            rec_type = 'd'
            uniqueid = int(uniqueid)
            if uniqueid > 0:
                rec_type = 'q'        # QC
            elif uniqueid < 0:
                uniqueid = -uniqueid
                rec_type = 'r'        # Reason

            if rec_type == 'd':     # Reset meta field number for data fields
                uniqueid = int(metafnum)
                metafnum = '0'

            # Used shared strings for field descriptions to reduce size of DB
            ssid = sstrings.get(fdesc)
            if ssid is None:
                sstrings[fdesc] = ssid_seq
                sql.execute('insert into shared_strings values(?, ?)',
                            (ssid_seq, fdesc))
                ssid = ssid_seq
                ssid_seq += 1

            # If this is a key change reason, treat it as a record wide
            # operation
            if rec_type == 'r' and codetext.startswith(KEY_CHANGE_REASON):
                # If we are deleting the reason, skip recording it
                if operation == 'D':
                    continue
                # Mark old keys as potentially deleted
                self._potential_deleted(pid, visit_num, plate_num, level,
                                        codetext, True)

                metafnum = 0

                # Get the destination keys and duplicate the reason there
                newpid, newvisit, newplate = parse_key_change(codetext)
                if newplate == int(plate_num):
                    sql.execute('insert into audit values(?, ?, ?, ?, ?, ?, ?, '
                                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                (newpid, newvisit, newplate, operation, date,
                                 time, who, rec_type, status, level, codevalue,
                                 codetext, metafnum, uniqueid, fnum, ssid,
                                 oldval, newval, dec_oldval, dec_newval))

            # Save the audit record
            sql.execute('insert into audit values(?, ?, ?, ?, ?, ?, ?, ?, ?, '
                        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (pid, visit_num, plate_num, operation, date, time, who,
                         rec_type, status, level, codevalue, codetext,
                         metafnum, uniqueid, fnum, ssid, oldval, newval,
                         dec_oldval, dec_newval))

            if rec_type == 'r' and uniqueid < 5100 and metafnum == '0':
                self._potential_deleted(pid, visit_num, plate_num, level,
                                        codetext, True)
            if rec_type == 'd' and fnum == '' and status == '7':
                self._potential_deleted(pid, visit_num, plate_num,
                                        level, '', False)

        sql.commit()
        sql.execute('pragma locking_mode=NORMAL')
        logger.info('Creating index on audit trail...')
        sql.execute('create index audit_keys on audit(pid, visit, plate)')

    def pidlist(self, context):
        '''Return a list of subjects'''
        sql = self.sql
        study = context.get('study')
        sites = context.get('sites')
        if sql and study:
            where_clause = ['substr(data, 1, 1) != \'0\'']
            pids = context.get('pids')
            if pids and not pids.empty:
                where_clause.append(pids.sql('pid'))

            visits = context.get('visits')
            if visits and not visits.empty:
                where_clause.append(visits.sql('visit'))

            plates = context.get('plates')
            if plates and not plates.empty:
                where_clause.append(plates.sql('plate'))

            levels = context.get('levels')
            if levels and not levels.empty:
                where_clause.append(levels.sql('level'))

            statement = 'select distinct pid from data where ' + \
                        ' and '.join(where_clause)

            cursor = sql.execute(statement)
            for record in cursor:
                pid = record[0]
                if sites and study.sites.pid_to_site_number(pid) in sites:
                    yield record[0]

    def attachments(self, rec):
        '''Loads secondary record information into a Record'''
        sql = self.sql
        cursor = sql.execute('select raster, isprimary, ts from attachments '
                             'where pid=? and visit=? and plate=?',
                             (rec.pid, rec.visit_num, rec.plate_num))
        for raster, primary, timestamp in cursor:
            rec.add_attachment(raster, primary, timestamp)

    def sorted_record_keys(self, pid, context):
        '''Returns a list of records for this subject, sorted by visitmap'''
        sql = self.sql
        study = context.get('study')
        where_clause = ['pid=:pid']
        if not context.get('missing'):
            where_clause.append('substr(data, 1, 1) != \'0\'')
        visits = context.get('visits')
        if visits and not visits.empty:
            where_clause.append(visits.sql('visit'))

        plates = context.get('plates')
        if plates and not plates.empty:
            where_clause.append(plates.sql('plate'))

        levels = context.get('levels')
        if levels and not levels.empty:
            where_clause.append(levels.sql('level'))

        statement = 'select visit, plate, data from data where ' + \
                    ' and '.join(where_clause)

        if context.get('deleted'):
            statement = statement + ' union select visit, plate, data ' \
                        'from deleted where ' + ' and '.join(where_clause)

        records = []
        cursor = sql.execute(statement, {'pid': pid})
        for record in cursor:
            datarec = record[2]
            sort_keys = study.visit_map.sort_order(record[0], record[1])
            records.append((sort_keys, datarec))
        cursor.close()

        for _, datarec in sorted(records, key=lambda x: x[0]):
            rec = Record(study, datarec)
            if rec.plate_num in context.get('attachments', []):
                self.attachments(rec)
            yield rec

    def audit_by_keys(self, pid_num, visit_num, plate_num):
        '''Returns a list of raw audit records for the specified keys'''
        sql = self.sql
        cursor = sql.execute(SQL_AUDITRECS, (pid_num, visit_num, plate_num))
        last_rec = None
        last_time = 0
        audit_recs = []

        # Fetch the raw audit records. Sometimes the data/reason/qc records
        # have times that are off by 1 second because of how the server
        # writes them to the audit file. Adjust the times on those records.
        for row in cursor:
            this_rec = AuditRec._make(row)
            this_time = \
                int(this_rec.ttime[0:2])*3600 + \
                int(this_rec.ttime[2:4])*60 + \
                int(this_rec.ttime[4:6])

            if last_rec is None or last_rec.who != this_rec.who or \
                last_rec.tdate != this_rec.tdate or \
                this_time not in (last_time, this_time-1):
                last_rec = this_rec
                last_time = this_time

            if this_rec.fnum is None or this_rec.fnum == '':
                this_rec = this_rec._replace(fnum=0)

            # For deleted records, get the reason from DFPLATE and mark it
            # for all fields (funique=0, fnum=0)
            if this_rec.rectype == 'r' and this_rec.funiqueid < 5100 and \
                this_rec.metafnum == 0:
                this_rec = this_rec._replace(funiqueid=0, fnum=0)

            # For key changes, mark this for all fields
            if this_rec.rectype == 'r' and this_rec.metafnum == 0 and \
                this_rec.op != 'D' and \
                this_rec.reason.startswith(KEY_CHANGE_REASON):
                this_rec = this_rec._replace(funiqueid=0, fnum=0, desc='')

            audit_recs.append(
                this_rec._replace(
                    tdate=\
                    this_rec.tdate[0:4] + '/' + \
                    this_rec.tdate[4:6] + '/' + \
                    this_rec.tdate[6:8],
                    ttime=\
                    this_rec.ttime[0:2] + ':' + \
                    this_rec.ttime[2:4] + ':' + \
                    this_rec.ttime[4:8]
                )
            )

        # Sort the raw records
        audit_recs.sort(key=lambda x: (x.tdate, x.ttime, abs(x.fnum),
                                       x.rectype, x.metafnum))

        return audit_recs
