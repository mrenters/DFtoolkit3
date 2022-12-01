#
# Copyright 2022, Martin Renters
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
'''Mailmerge generation routines'''

import os
from xlsxwriter.workbook import Workbook

columns = [
    ('Site', 10),
    ('Country', 15),
    ('Site Name', 50),
    ('Contact', 40),
    ('Investigator', 40),
    ('Email', 60),
    ('Attachment', 40)
]

TABLE_START_ROW = 1

class MailMerge:
    '''Mailmerge file generation class'''
    def __init__(self, path):
        self.workbook = Workbook(path)
        vba = os.path.join(os.path.dirname(__file__), 'vba', 'mailmerge.vba')
        self.workbook.add_vba_project(vba)
        self.wrap_format = self.workbook.add_format({
            'text_wrap': True,
            'valign': 'vcenter'
        })
        self.header_format = self.workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#244062',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        self.sheet = self.workbook.add_worksheet('MailMerge')
        for col, (_, width) in enumerate(columns):
            self.sheet.set_column(col, col, width)
        self.sheet.set_row(0, 50)
        self.row = TABLE_START_ROW+1

    def add_row(self, site, path):
        '''adds an entry to the mailmerge file'''
        email = site.fax.replace('mailto:', '')
        email = email.replace('  ', ' ').replace(' ', '; ')
        if email:
            self.sheet.write(self.row, 0, site.number, self.wrap_format)
            self.sheet.write(self.row, 1, site.country, self.wrap_format)
            self.sheet.write(self.row, 2, site.name, self.wrap_format)
            self.sheet.write(self.row, 3, site.contact, self.wrap_format)
            self.sheet.write(self.row, 4, site.investigator, self.wrap_format)
            self.sheet.write(self.row, 5, email, self.wrap_format)
            self.sheet.write(self.row, 6, path, self.wrap_format)
            self.row += 1

    def close(self):
        '''add a table (or message) and close the workbook'''
        if self.row == TABLE_START_ROW+1:
            self.sheet.merge_range(0, 0, 0, len(columns)-1, 'Nothing to report')
        else:
            self.sheet.merge_range(
                0, 3, 0, len(columns)-1,
                'E-Mail Template Variables: {SITE}, {COUNTRY}, '
                '{SITENAME}, {CONTACT}, {INVESTIGATOR}, {DATE}',
                self.wrap_format)
            self.sheet.insert_button(0, 0, {
                'macro': '\'Create_Email "no"\'',
                'caption': 'Create Emails',
                'width': 120,
                'height': 45,
                'x_offset': 2,
                'y_offset': 2
            })
            self.sheet.insert_button(0, 0, {
                'macro': '\'Create_Email "yes"\'',
                'caption': 'Create/Send Emails',
                'width': 120,
                'height': 45,
                'x_offset': 150,
                'y_offset': 2
            })
            self.sheet.add_table(
                TABLE_START_ROW, 0,
                self.row-1, len(columns)-1, {
                    'autofilter': True, 'name': 'MailMerge',
                    'columns': [{
                        'header': colname,
                        'header_format': self.header_format
                    } for colname, _ in columns]})
            self.sheet.set_selection(TABLE_START_ROW, 0, TABLE_START_ROW, 0)
        self.sheet.hide_gridlines(2)
        self.workbook.close()
