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
'''This file implements a the schemadiff report'''

from xlsxwriter import Workbook

from .study import Study
from .fieldbase import Style, Field, FieldRef
from .module import Module, ModuleRef
from .plate import Plate

class SchemaDiffXLSX:
    '''Generate an Excel schemadiff report'''
    def __init__(self, filename):
        self.workbook = Workbook(filename)
        self.formats = {
            'header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'bg_color': '#244062',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '@',
            }),
            'number-low':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0',
            }),
            'number-med':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#9c6500',
                'bg_color': '#ffeb9c',
                'text_wrap': True,
                'num_format': '0',
            }),
            'number-high':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#9c0006',
                'bg_color': '#ffc7ce',
                'text_wrap': True,
                'num_format': '0',
            }),
            'string-low': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0',
            }),
            'string-med': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#9c6500',
                'bg_color': '#ffeb9c',
                'text_wrap': True,
                'num_format': '0',
            }),
            'string-high': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#9c0006',
                'bg_color': '#ffc7ce',
                'text_wrap': True,
                'num_format': '0',
            }),
        }

    def list_changes(self, changelist, sheetname):
        '''List all the changes for a specific area'''
        sheet = self.workbook.add_worksheet(sheetname)
        row = 1
        columns = {
            'Globals': [],
            'Styles': [
                ('Style Name', 16)],
            'Modules': [
                ('Module Name', 16),
                ('Field Name', 16)],
            'Plates': [
                ('Plate Description', 35),
                ('Plate', 8),
                ('Module', 16),
                ('Field', 8),
                ('Field Name', 16)]
        }.get(sheetname, [])
        columns.extend([
            ('Operation', 30),
            ('Old Value', 50),
            ('New Value', 50),
            ('Impact', 16),
            ('Impact Reason', 50),
            ('nRecs', 16),
            ('Plan', 50),
        ])


        for changerecord in changelist:
            col = 0
            string_style = self.formats.get(
                f'string-{changerecord.impact_level_label.lower()}')
            number_style = self.formats.get(
                f'number-{changerecord.impact_level_label.lower()}')
            obj = changerecord.obj
            if isinstance(obj, Study):
                pass
            elif isinstance(obj, Style):
                sheet.write(row, 0, obj.style_name, string_style)
                col = 1
            elif isinstance(obj, Module):
                sheet.write(row, 0, obj.name, string_style)
                sheet.write(row, 1, '', string_style)
                col = 2
            elif isinstance(obj, Field):
                sheet.write(row, 0, obj.module.name, string_style)
                sheet.write(row, 1, obj.name, string_style)
                col = 2
            elif isinstance(obj, Plate):
                sheet.write(row, 0, obj.description, string_style)
                sheet.write(row, 1, obj.number, number_style)
                sheet.write(row, 2, '', string_style)
                sheet.write(row, 3, '', string_style)
                sheet.write(row, 4, '', string_style)
                col = 5
            elif isinstance(obj, ModuleRef):
                sheet.write(row, 0, obj.plate.description, string_style)
                sheet.write(row, 1, obj.plate.number, number_style)
                sheet.write(row, 2, obj.identifier, string_style)
                sheet.write(row, 3, '', string_style)
                sheet.write(row, 4, '', string_style)
                col = 5
            elif isinstance(obj, FieldRef):
                sheet.write(row, 0, obj.plate.description, string_style)
                sheet.write(row, 1, obj.plate.number, number_style)
                sheet.write(row, 2, obj.moduleref.identifier, string_style)
                sheet.write(row, 3, obj.number, number_style)
                sheet.write(row, 4, obj.name, string_style)
                col = 5
            else:
                raise ValueError(f'list_changes: {obj} unknown object type')

            sheet.write(row, col, changerecord.description, string_style)
            sheet.write(row, col+1, changerecord.old_value, string_style)
            sheet.write(row, col+2, changerecord.new_value, string_style)
            sheet.write(row, col+3, changerecord.impact_level_label,
                        string_style)
            sheet.write(row, col+4, changerecord.impact_text, string_style)
            sheet.write(row, col+5, '', string_style)
            sheet.write(row, col+6, '', string_style)
            row += 1

        self.add_table(sheet, row, columns)

    def generate(self, changelist):
        '''Generate an Excel report of study changes'''
        self.list_changes(filter(lambda x: isinstance(x.obj, (Study)),
                                 changelist), 'Globals')
        self.list_changes(filter(lambda x: isinstance(x.obj, (Style)),
                                 changelist), 'Styles')
        self.list_changes(filter(lambda x: isinstance(x.obj, (Module, Field)),
                                 changelist), 'Modules')
        self.list_changes(filter(lambda x: isinstance(x.obj, (Plate, ModuleRef,
                                                              FieldRef)),
                                 changelist), 'Plates')

        self.workbook.close()

    def add_table(self, sheet, row, columns):
        '''add the table to the workbook'''

        # If no data, don't add the table
        if row == 1:
            sheet.merge_range(0, 0, 0, len(columns)-1, 'No changes to report')
            return

        # Set column widths, coloring and totaling
        for colno, (_, colwidth) in enumerate(columns):
            sheet.set_column(colno, colno, colwidth)

        headers = [
            {'header': colname, 'header_format': self.formats['header']} \
            for colname, _ in columns]
        sheet.add_table(0, 0, row-1, len(columns)-1, {
            'autofilter': True, 'name': sheet.name, 'columns': headers})
