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
'''QC2Excel generation routines'''

import os
import logging
from collections import Counter
from datetime import date
from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet
from xlsxwriter.utility import xl_rowcol_to_cell

from .mailmerge import MailMerge
from .rangelist import SiteList, SubjectList, VisitList, PlateList

CHART_ROW = 2
START_TABLE_ROW = 3

SITE_LABEL = 'Site'
STATUS_LABEL = 'Status'
PROBLEM_LABEL = 'Problem'
AGE_LABEL = 'Age'
PRIORITY_LABEL = 'Priority'

def build_qc2excel(study, context):
    '''Build one or more QC2Excel output files'''
    study = context.get('study')
    if not study:
        raise ValueError('no study information in context')

    queries = sorted(study.queries())
    basepath = context.get('destdir', os.getcwd())

    os.makedirs(basepath, exist_ok=True)

    # Do we want one output file per site, or one for all sites?
    if context.get('bysite'):
        site_filter = context.get('sites', SiteList(default_all=True))
        mailmerge = MailMerge(os.path.join(basepath, 'mailmerge.xlsm'))
        for site in study.sites:
            if not site.number in site_filter:
                continue

            # Limit QCs to only the site we're interested in
            current_site_filter = SiteList()
            current_site_filter.from_string(str(site.number))
            context['sites'] = current_site_filter

            name = 'Queries-{}.xlsx'.format(site.number)
            path = os.path.join(basepath, name)
            book = QC2ExcelWorkbook(path, context)
            nqueries = book.add_qc2excel('QCs', queries)
            book.close()
            if nqueries or context.get('mailmerge_allsites'):
                mailmerge.add_row(site, name)
        mailmerge.close()
    else:
        path = os.path.join(basepath, 'qc2excel.xlsx')
        book = QC2ExcelWorkbook(path, context)
        book.add_qc2excel('QCs', queries)
        book.close()

class QC2ExcelWorkbook(Workbook):
    '''A class for generating a QC2Excel file'''
    def __init__(self, fname, context):
        super().__init__(fname)
        self.context = context

        self.qcformats = {}
        self.qcformats['title'] = self.add_format({
            'font_color': 'white',
            'bg_color': '#4f81bd',
            'font_size': 36,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
        self.qcformats['header'] = self.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#244062',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        self.qcformats['category'] = self.add_format({
            'font_color': 'white',
            'bg_color': '#4f81bd',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
        self.qcformats['percent'] = self.add_format({
            'font_color': 'black',
            'bg_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0.0%',
            'border': 1
        })
        self.qcformats['str'] = [self.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        }) for n in range(6)]
        self.qcformats['num'] = [self.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        }) for n in range(6)]
        self.qcformats['date'] = [self.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd hh:mm:ss',
            'border': 1
        }) for n in range(6)]

        priority_colors = (
            ('#9c0006', '#ffc7ce'),     # red
            ('#3f3f76', '#ffcc99'),     # orange
            ('#9c6500', '#ffeb9c'),     # yellow
            ('#006100', '#c6efce'),     # green
            ('#000000', '#b8cce4'),     # blue
        )
        for fmtname in ['str', 'num', 'date']:
            fmt = self.qcformats[fmtname]
            for i, (text, bkgd) in enumerate(priority_colors, 1):
                fmt[i].set_font_color(text)
                fmt[i].set_bg_color(bkgd)

    def add_qc2excel(self, name=None, queries=None):
        '''add a QC2Excel worksheet and populate'''
        worksheet = super().add_worksheet(name, QC2ExcelWorksheet)
        worksheet.setup_sheet(self.qcformats, self.context)
        nqueries = worksheet.add_queries(queries)
        if nqueries:
            worksheet.add_charts(self)

        if worksheet.row >= 1048567:
            logging.error('workbook %s, worksheet %s has more than the '
                          'maximum number of rows', self.filename, name)
        return nqueries

class QC2ExcelWorksheet(Worksheet):
    '''an Excel worksheet that contains a query listing and charts'''

    agebin_labels = [
        '0-30 days', '31-60 days', '61-90 days', '91-120 days',
        '121-150 days', '151-180 days', '>180 days'
    ]

    def __init__(self):
        super().__init__()
        # Counters
        self.priorities = Counter()
        self.statuses = Counter()
        self.qctypes = Counter()
        self.agebins = Counter()
        self.row = 0
        self.sheet_width = 0
        self.colnames = []
        self.context = {}
        self.formats = {}

    def setup_sheet(self, formats, context):
        '''setup a QC2Excel sheet'''
        self.formats = formats
        self.context = context

        self.setup_page()
        self.setup_columns()
        self.setup_header()


    def setup_columns(self):
        '''setup column names'''
        context = self.context
        cols = []
        extra_distribute = 0
        if context.get('include_region'):
            cols.append(('Region', 10, 0))
        else:
            extra_distribute += 12

        if context.get('include_country'):
            cols.append(('Country', 10, 0))
        else:
            extra_distribute += 12

        cols.append((SITE_LABEL, 10, 0))
        cols.append(('Subject', 15, 0))
        cols.append(('Assessment', 25, 10))

        if not context.get('sitemode'):
            cols.append(('Visit', 10, 0))
            cols.append(('Plate', 10, 0))
        else:
            extra_distribute += 50

        cols.append(('Page', 25, 10))
        cols.append(('Field', 25, 10))

        if not context.get('sitemode'):
            cols.append(('Fld #', 10, 0))

        if context.get('include_priority'):
            cols.append((PRIORITY_LABEL, 10, 0))
        else:
            extra_distribute += 12

        if not context.get('sitemode'):
            cols.append(('Days', 10, 0))

        cols.append((AGE_LABEL, 10, 0))
        cols.append((STATUS_LABEL, 20, 0))
        cols.append((PROBLEM_LABEL, 20, 0))
        cols.append(('Value', 20, 20))
        cols.append(('Query', 20, 20))
        cols.append(('Reply', 20, 20))

        if context.get('timestamps'):
            cols.append(('Creator', 12, 0))
            cols.append(('Created', 20, 0))
            cols.append(('Modifier', 12, 0))
            cols.append(('Modified', 20, 0))
            cols.append(('Resolver', 12, 0))
            cols.append(('Resolved', 20, 0))


        # Set column widths
        sheet_width = 0
        for colnum, (_, width, expand) in enumerate(cols):
            width += extra_distribute * (expand/100)
            self.set_column(colnum, colnum, width)
            sheet_width += width

        self.sheet_width = sheet_width * 7.14
        self.colnames = [name for name, _, _ in cols]

    def setup_header(self):
        '''setup worksheet header'''
        study = self.context.get('study')
        if not study:
            raise ValueError('no study information in context')

        self.set_row(0, 75)

        # Setup headers
        study_name = study.study_name
        self.merge_range(0, 0, 0, len(self.colnames)-1,
                         'QC Report for {}'.format(study_name),
                         self.fmt('title'))
        self.merge_range(1, 0, 1, len(self.colnames)-1,
                         date.today().isoformat(), self.fmt('header'))
        study_name = study_name.replace("&", "&&")
        self.set_header('&LQC Report&C{0}&R&P of &N'.format(study_name))

        self.row = START_TABLE_ROW + 1

    def setup_page(self):
        '''setup worksheet page settings'''
        self.set_landscape()
        self.set_paper(5)
        self.fit_to_pages(1, 0)
        self.repeat_rows(START_TABLE_ROW)
        self.hide_gridlines(2)
        if not self.context.get('noprotect'):
            self.protect('', {
                'autofilter': True,
                'sort': True,
                'select_locked_cells': True,
                'select_unlocked_cells': True
            })
        self.set_zoom(90)

    def fmt(self, name, priority=0):
        '''get a format object'''
        fmt_obj = self.formats.get(name)
        if isinstance(fmt_obj, list):
            fmt_obj = fmt_obj[priority]
        return fmt_obj

    @property
    def site_column(self):
        '''returns which column has the Site information'''
        return self.colnames.index(SITE_LABEL)

    @property
    def chart_details(self):
        '''returns a list of charts to include given the context'''
        study = self.context.get('study')
        charts = [
            {
                'name': 'Status', 'column': STATUS_LABEL,
                'counts': self.statuses, 'trim': True,
                'labels': study.qc_statuses.labels(self.context.get('simplify'))
            },
            {
                'name': 'Problems', 'column': PROBLEM_LABEL,
                'counts': self.qctypes, 'trim': True,
                'labels': study.qc_types.labels(self.context.get('simplify'))
            },
            {
                'name': 'Age', 'column': AGE_LABEL,
                'counts': self.agebins, 'trim': False,
                'labels': self.agebin_labels
            }
        ]

        if self.context.get('include_priority'):
            charts.append(
                {
                    'name': 'Priority', 'column': PRIORITY_LABEL,
                    'counts': list(range(6)), 'trim': False,
                    'labels': list(range(1, 6))
                })

        return charts

    def add_charts(self, workbook):
        '''add charts to worksheet'''
        row = self.row + 1

        sitecol = self.site_column

        # Totals
        self.merge_range(row, sitecol, row, sitecol+2,
                         'Total', self.fmt('header'))
        row += 1
        self.write_formula(row, sitecol+1,
                           '=SUBTOTAL(103, {sht}_Details[[Site]])'.format(
                               sht=self.get_name()), self.fmt('num'))
        total_cell = xl_rowcol_to_cell(row, sitecol+1)
        self.write(row, sitecol+2, 'Selected Records', self.fmt('category'))
        row += 2

        charts = self.chart_details
        chart_width = self.sheet_width / len(charts)
        chart_xoffset = 5
        for chart in charts:
            self.merge_range(row, sitecol, row, sitecol+2,
                             chart['name'], self.fmt('header'))
            row += 1
            chart_start_row = row
            for label in chart['labels']:
                if chart['trim'] and chart['counts'][label] == 0:
                    continue

                if not isinstance(label, int):
                    lb_str = '"' + label + '"'
                else:
                    lb_str = label

                cell = xl_rowcol_to_cell(row, sitecol+1)
                formula = '=IFERROR({0}/{1}, 0)'.format(cell, total_cell)
                self.write_formula(row, sitecol, formula, self.fmt('percent'))
                formula = '=SUMPRODUCT(SUBTOTAL(3,' \
                    'OFFSET({sht}_Details[{col}],' \
                    'ROW({sht}_Details[{col}])-' \
                    'MIN(ROW({sht}_Details[{col}])),,1)),' \
                    '--({sht}_Details[{col}]={lbl}))'.format(
                        sht=self.get_name(), col=chart['column'], lbl=lb_str)
                self.write_formula(row, sitecol+1, formula, self.fmt('num'))
                self.write(row, sitecol+2, label, self.fmt('category'))
                row += 1

            if self.context.get('percent'):
                data_column = sitecol
            else:
                data_column = sitecol+1

            chart_obj = workbook.add_chart({'type': 'bar'})
            chart_obj.add_series({
                'values': '=QCs!{0}:{1}'.format(
                    xl_rowcol_to_cell(chart_start_row, data_column, True, True),
                    xl_rowcol_to_cell(row-1, data_column, True, True)),
                'categories': '=QCs!{0}:{1}'.format(
                    xl_rowcol_to_cell(chart_start_row, sitecol+2, True, True),
                    xl_rowcol_to_cell(row-1, sitecol+2, True, True)),
                'data_labels': {'value': True},
                'gap': 500//max(1, row-chart_start_row)
            })

            chart_obj.set_title({'name': chart['name']})
            chart_obj.set_legend({'none': True})
            chart_obj.set_size({
                'width': chart_width,
                'x_offset': chart_xoffset,
                'y_offset': 5
            })
            chart_xoffset += chart_width

            chart_obj.set_chartarea({'border': {'none': True}})
            self.insert_chart(CHART_ROW, 0, chart_obj)

            row += 1

        self.merge_range(CHART_ROW, 0, CHART_ROW, len(self.colnames)-1,
                         None, self.fmt('str'))
        self.set_row(CHART_ROW, 230)
        self.row = row

    def add_queries(self, queries):
        '''Add QCs to the spreadsheet'''
        site_filter = self.context.get('sites', SiteList(default_all=True))
        pid_filter = self.context.get('pids', SubjectList(default_all=True))
        visit_filter = self.context.get('visits', VisitList(default_all=True))
        plate_filter = self.context.get('plates', PlateList(default_all=True))
        for query in queries:
            if  query.site.number not in site_filter or \
                query.pid not in pid_filter or \
                query.visit_num not in visit_filter or \
                query.plate_num not in plate_filter:
                continue

            if self.context.get('external') and query.is_internal:
                continue
            if self.context.get('outstanding') and query.is_resolved:
                continue
            if self.context.get('outstanding') and \
                self.context.get('sitemode') and query.is_pending:
                continue

            self.add_query(query)

        nqueries = self.row - (START_TABLE_ROW+1)

        # Make a table if we have data, otherwise just put out message
        if not nqueries:
            # Output message where charts normally go
            self.merge_range(START_TABLE_ROW-1, 0,
                             START_TABLE_ROW-1, len(self.colnames)-1,
                             'No matching Queries found',
                             self.fmt('str'))
        else:
            self.add_table(START_TABLE_ROW, 0,
                           self.row-1, len(self.colnames)-1, {
                               'autofilter': True, 'first_column': True,
                               'name': '{sht}_Details'.format(
                                   sht=self.get_name()),
                               'columns': [{
                                   'header': colname,
                                   'header_format': self.fmt('header')
                               } for colname in self.colnames]})

        return nqueries

    def add_query(self, query):
        '''Add a single QC to the spreadsheet'''
        context = self.context
        simplify = context.get('simplify')
        cols = []

        color_index = query.priority \
            if context.get('color_priority') and not query.is_resolved else 0

        if context.get('include_region'):
            cols.append((query.site.region, self.fmt('str', color_index)))
        if context.get('include_country'):
            cols.append((query.site.decoded_country,
                         self.fmt('str', color_index)))

        cols.append((query.site.number, self.fmt('num', color_index)))
        cols.append((query.pid, self.fmt('num', color_index)))
        cols.append((query.visit_label, self.fmt('str', color_index)))

        if not context.get('sitemode'):
            cols.append((query.visit_num, self.fmt('num', color_index)))
            cols.append((query.plate_num, self.fmt('num', color_index)))

        cols.append((query.plate_label, self.fmt('str', color_index)))
        cols.append((query.description if not query.page_query else None,
                     self.fmt('str', color_index)))

        if not context.get('sitemode'):
            cols.append((query.field_num if not query.page_query else None,
                         self.fmt('num', color_index)))

        if context.get('include_priority'):
            cols.append((query.priority, self.fmt('num', color_index)))

        self.priorities[query.priority] += 1

        # age and agebin
        age = query.age

        if age is not None and age >= 0:
            label = self.agebin_labels[min(int(age/30),
                                           len(self.agebin_labels)-1)]
            self.agebins[label] += 1
        else:
            label = None

        if not context.get('sitemode'):
            cols.append((age, self.fmt('num', color_index)))
        cols.append((label, self.fmt('str', color_index)))

        label = query.status_decoded(simplify)
        self.statuses[label] += 1
        cols.append((label, self.fmt('str', color_index)))

        label = query.qctype_decoded(simplify)
        self.qctypes[label] += 1
        cols.append((label, self.fmt('str', color_index)))

        cols.append((query.value if not query.page_query else None,
                     self.fmt('str', color_index)))

        cols.append((query.query, self.fmt('str', color_index)))
        cols.append((query.reply, self.fmt('str', color_index)))

        if context.get('timestamps'):
            cols.append((query.creator, self.fmt('str', color_index)))
            cols.append((query.created, self.fmt('date', color_index)))
            cols.append((query.modifier, self.fmt('str', color_index)))
            cols.append((query.modified, self.fmt('date', color_index)))
            cols.append((query.resolver, self.fmt('str', color_index)))
            cols.append((query.resolved, self.fmt('date', color_index)))

        # Write row
        for colnum, (value, cell_format) in enumerate(cols):
            self.write(self.row, colnum, value, cell_format)
        self.row += 1
