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
'''Data Quality Report classes'''

from collections import Counter

import logging
from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell

from dftoolkit.query import QCType

#####################################################################
# Quality Stats - Keeps track of quality statistics
#####################################################################
class QualityStats:
    '''Keep track of quality statistics'''
    def __init__(self):
        self.npids = 0
        self.nrecs = 0
        self.nfinalrecs = 0
        self.nvisits = 0
        self.nreports = 0
        self.nvisitslost = 0
        self.nconsecoverdue = 0
        self.qc_nrecs = 0
        self.qc_gt60days = 0
        self.qc_types = Counter()
        self.qc_reckeys = {}

    def handle_query(self, query):
        '''add a data query to the stats'''
        if query.is_pending or query.is_resolved:
            return
        self.qc_reckeys[(query.visit_num, query.plate_num)] = 1
        self.qc_nrecs = len(self.qc_reckeys)
        self.qc_types[query.qctype] += 1
        if query.age > 60:
            self.qc_gt60days += 1

    def handle_data(self, record):
        '''handle a data record'''
        self.nrecs += 1
        if record.final:
            self.nfinalrecs += 1

    def merge_mpqc(self):
        '''merge MPQC and ECMPQC'''
        self.qc_types[QCType.MISSINGPAGE] += self.qc_types[QCType.ECMISSINGPAGE]
        self.qc_types[QCType.ECMISSINGPAGE] = 0

    @property
    def total_qcs(self):
        '''returns the total number of QCs'''
        return sum(self.qc_types.values())

    @property
    def expected_recs(self):
        '''returns the number of records expected'''
        return self.nrecs + self.qc_types[QCType.MISSINGPAGE] + \
               self.qc_types[QCType.OVERDUEVISIT] + \
               self.qc_types[QCType.ECMISSINGPAGE]

    @property
    def qcs_per_patient(self):
        '''returns the number of QCs per patient'''
        return self.total_qcs / self.npids if self.npids else 0.0

    @property
    def percent_final(self):
        '''returns the percentage of records that are final'''
        return self.nfinalrecs / self.nrecs if self.nrecs else 0.0

    @property
    def percent_complete(self):
        '''calculate the percentable completion (final/expected)'''
        n_expected = self.expected_recs
        if n_expected:
            complete_percent = self.nfinalrecs / (n_expected + 0.0)
        else:
            complete_percent = 0.0
        return complete_percent

    def __add__(self, other):
        '''add two QualityStats objects and return the sum'''
        res = QualityStats()
        res.npids = self.npids + other.npids
        res.nrecs = self.nrecs + other.nrecs
        res.nfinalrecs = self.nfinalrecs + other.nfinalrecs
        res.nvisits = self.nvisits + other.nvisits
        res.nreports = self.nreports + other.nreports
        res.nvisitslost = self.nvisitslost + other.nvisitslost
        res.nconsecoverdue = self.nconsecoverdue + other.nconsecoverdue
        res.qc_nrecs = self.qc_nrecs + other.qc_nrecs
        res.qc_gt60days = self.qc_gt60days + other.qc_gt60days
        res.qc_types = self.qc_types + other.qc_types
        return res

    def __repr__(self):
        return '<Stats pids=%d nrecs=%d finalrecs=%d visits=%d reports=%d ' \
            'lostvisits=%d nconsecutive=%d>' % (self.npids, self.nrecs,
                                                self.nfinalrecs, self.nvisits,
                                                self.nreports, self.nvisitslost,
                                                self.nconsecoverdue)

#####################################################################
# DataQualityReport - Generate Data Quality Report
#####################################################################
class DataQualityReport:
    '''A Data Quality report'''
    def __init__(self, study, config):
        self.study = study
        self.config = config
        self.enrolled_patients = {}
        self.patients = {}

    #################################################################
    # load_enrolled_patients - Load a list of patients we're interested in
    #################################################################
    def load_enrolled_patients(self, path):
        '''load list of patients of interest'''
        with open(path, 'r') as idlist:
            for rec in idlist:
                try:
                    pid = int(rec)
                except ValueError:
                    print('Invalid patient ID record:', rec)
                    continue

                self.enrolled_patients[pid] = True

    #################################################################
    # load_data_recs - Load the data records and count them
    #################################################################
    def load_data_recs(self):
        '''Load data record information into report'''
        site_filter = self.config['sites']
        pid_filter = self.config['ids']
        visit_filter = self.config['visits']
        plate_filter = self.config['plates']

        for plate in self.study.plates:
            if plate.number > 500 or plate.number not in plate_filter:
                continue
            for record in self.study.data(plate):
                if record.pending:
                    continue
                if self.enrolled_patients and \
                    record.pid not in self.enrolled_patients:
                    continue
                if record.pid not in pid_filter or \
                    record.visit_num not in visit_filter:
                    continue
                if self.study.sites.pid_to_site_number(record.pid) \
                    not in site_filter:
                    continue
                patient = self.patients.setdefault(record.pid, QualityStats())
                patient.npids = 1
                patient.handle_data(record)

    #################################################################
    # load_queries - Load QC database
    #################################################################
    def load_queries(self):
        '''Load query information into report'''
        plate_filter = self.config['plates']
        visit_filter = self.config['visits']

        for query in self.study.queries():
            if query.plate_num not in plate_filter:
                continue
            if query.visit_num not in visit_filter:
                continue

            patient = self.patients.get(query.pid)
            if patient:
                patient.handle_query(query)

    #################################################################
    # load_schedule - Loads visit schedule data
    #################################################################
    def load_schedule(self):
        '''load DFX_scheduling data'''
        visits_filter = self.config['visits']
        reports_filter = self.config['reports']
        consecutive = 0
        last_patient = None
        try:
            for entry in self.study.api.schedules():
                # Is this a new patient?
                if last_patient != entry.pid:
                    last_patient = entry.pid
                    consecutive = 0

                # Skip cycles and visits we're not interested in
                if entry.is_cycle or entry.visit_status == 'not done' or \
                    entry.visit_number not in visits_filter:
                    consecutive = 0
                    continue

                # Pull patient and process if of interest
                patient = self.patients.get(entry.pid)
                if patient:

                    # If overdue, add increment consecutive counter
                    if entry.visit_status == 'overdue':
                        consecutive += 1
                        # Do we have a consecutive block?
                        # (only count second of block)
                        if consecutive == 2:
                            patient.nconsecoverdue += 1
                        continue

                    # If this is a report, count it is a report
                    if entry.visit_number in reports_filter:
                        patient.nreports += 1
                    elif entry.visit_status == 'missed':
                        patient.nvisitslost += 1
                    else:
                        patient.nvisits += 1
        except IOError:
            logging.error('No scheduling information found')

    #################################################################
    # summarize - Summerize by site/country
    #################################################################
    def summarize(self):
        '''summarize data by country and site'''
        country_metrics = {}
        site_metrics = {}

        merge_mpqc = self.config.get('merge_mpqc', False)
        for patient, data in self.patients.items():
            if merge_mpqc:
                data.merge_mpqc()

            site = self.study.sites.pid_to_site(patient)
            site_metrics[site] = data + \
                site_metrics.get(site, QualityStats())

        for site, data in site_metrics.items():
            country_metrics[site.country] = data + \
                country_metrics.get(site.country, QualityStats())

        return country_metrics, site_metrics

    #################################################################
    # generate_xlsx - Generate an Excel report
    #################################################################
    def generate_xlsx(self, filename):
        '''generate Excel report'''
        country_metrics, site_metrics = self.summarize()
        qc_types = self.study.qc_types.sorted_types
        if self.config.get('merge_mpqc', False):
            qc_types = list(filter(lambda x: x[0] != QCType.ECMISSINGPAGE,
                                   qc_types))

        xlsx = DataQualityXLSX(filename,
                               self.study.study_name + ' Data Quality Report',
                               qc_types)
        for country in sorted(country_metrics.keys()):
            xlsx.add_country_row(country, country_metrics[country])
        for site in sorted(site_metrics.keys()):
            xlsx.add_site_row(site, site_metrics[site])
        for patient in sorted(self.patients.keys()):
            site = self.study.sites.pid_to_site(patient)
            xlsx.add_subject_row(site, patient, self.patients[patient])
        xlsx.close_workbook()

    #################################################################
    # generate_reportcards - Generate PDF report cards
    #################################################################
    def generate_reportcards(self, rules, reportdir):
        '''generate PDF report cards'''

#####################################################################
# DataQualityXLSX - The Excel Data Quality Report
#####################################################################
class DataQualityXLSX:
    '''Data Quality report output in Excel format'''
    TABLE_START_ROW = 3
    def __init__(self, filename, title, qc_types):
        self.workbook = Workbook(filename)
        self.title = title
        self.qc_types = qc_types
        self.formats = {
            'title': self.workbook.add_format({
                'font_size': 24,
                'font_color': 'white',
                'bg_color': '#244062',
                'align': 'center',
                'valign': 'vcenter'
            }),
            'blue_header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'font_size': 10,
                'bg_color': '#244062',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '@',
                'border_color': 'white',
                'border': 1
            }),
            'green_header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'font_size': 10,
                'bg_color': '#4f6228',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '@',
                'border_color': 'white',
                'border': 1
            }),
            'purple_header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'font_size': 10,
                'bg_color': '#403151',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '@',
                'border_color': 'white',
                'border': 1
            }),
            'orange_header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'font_size': 10,
                'bg_color': '#974706',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '@',
                'border_color': 'white',
                'border': 1
            }),
            'blue_number': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': 'white',
                'bg_color': '#244062',
                'text_wrap': True,
                'num_format': '0',
            }),
            'blue_percent': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': 'white',
                'bg_color': '#244062',
                'text_wrap': True,
                'num_format': '0.00%',
            }),
            'blue_float': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': 'white',
                'bg_color': '#244062',
                'text_wrap': True,
                'num_format': '0.0',
            }),
            'number':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0',
            }),
            'red_number': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#F8696B',
                'text_wrap': True,
                'num_format': '0',
            }),
            'percent': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0.00%',
            }),
            'float': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0.0',
            }),
            'string': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': '0',
            }),
            'date': self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'num_format': 'yyyy-mm-dd',
            })
        }
        self.country_sheet = self.workbook.add_worksheet('Country')
        self.site_sheet = self.workbook.add_worksheet('Site')
        self.subject_sheet = self.workbook.add_worksheet('Subject')
        self.country_row = self.TABLE_START_ROW
        self.site_row = self.TABLE_START_ROW
        self.subject_row = self.TABLE_START_ROW

    def add_country_row(self, country, metrics):
        '''add a row to the country sheet'''
        number_format = self.formats['number']
        string_format = self.formats['string']
        self.country_sheet.write(self.country_row, 0, country, string_format)
        self.country_sheet.write(self.country_row, 1, metrics.npids,
                                 number_format)
        self.write_metrics(self.country_sheet, self.country_row, 2, metrics)
        self.country_row += 1

    def add_site_row(self, site, metrics):
        '''add a row to the site sheet'''
        number_format = self.formats['number']
        string_format = self.formats['string']
        self.site_sheet.write(self.site_row, 0, site.country, string_format)
        self.site_sheet.write(self.site_row, 1, site.number, number_format)
        self.site_sheet.write(self.site_row, 2, site.investigator,
                              string_format)
        self.site_sheet.write(self.site_row, 3, metrics.npids, number_format)
        self.write_metrics(self.site_sheet, self.site_row, 4, metrics)
        self.site_row += 1

    def add_subject_row(self, site, subject, metrics):
        '''add a row to the patient sheet'''
        number_format = self.formats['number']
        string_format = self.formats['string']
        self.subject_sheet.write(self.subject_row, 0, site.country,
                                 string_format)
        self.subject_sheet.write(self.subject_row, 1, site.number,
                                 number_format)
        self.subject_sheet.write(self.subject_row, 2, site.investigator,
                                 string_format)
        self.subject_sheet.write(self.subject_row, 3, subject, number_format)
        self.write_metrics(self.subject_sheet, self.subject_row, 4, metrics)
        self.subject_row += 1

    def add_table(self, sheet, table_name, row, columns):
        '''adds in the table headers'''
        blue_header = self.formats['blue_header']
        green_header = self.formats['green_header']
        purple_header = self.formats['purple_header']
        orange_header = self.formats['orange_header']

        visits = [
            ('Visits Completed', 10, 'sum'),
            ('Reports Completed', 10, 'sum'),
            ('Visits Marked Missed', 10, 'sum'),
            ('Blocks of Consecutive Overdue Visits', 10, 'sum,gt0')
        ]
        data_quality = [
            ('Actual Number of Data Records', 10, 'sum'),
            ('Number of Final Data Records', 10, 'sum'),
            ('%Final', 10, '%final,percent,max_good'),
            ('Expected Number of Records', 10, 'sum'),
            ('%Complete', 10, '%complete,percent,max_good'),
            ('Outstanding Queries', 10, 'sum'),
            ('Records affected by Queries', 10, 'sum'),
            ('Outstanding Queries / Subject', 10, 'qcs_subject,float,max_bad'),
            ('Outstanding Queries >60days', 10, 'sum,max_bad')
        ]

        # Build the table headers
        table_headers = [{'header': name, 'header_format': blue_header} \
            for name, _, _ in columns]
        table_headers.extend([{'header': name, 'header_format': green_header} \
            for name, _, _ in visits])
        table_headers.extend([{'header': name, 'header_format': purple_header} \
            for name, _, _ in data_quality])
        table_headers.extend([{'header': name, 'header_format': orange_header} \
            for _, name in self.qc_types])

        # Add title
        sheet.merge_range(0, 0, 0, len(table_headers)-1, self.title,
                          self.formats['title'])
        sheet.set_row(0, 75)

        # If nothing to report, put out message
        if row == self.TABLE_START_ROW:
            sheet.merge_range(self.TABLE_START_ROW, 0,
                              self.TABLE_START_ROW, len(table_headers)-1,
                              'No data to report')
            return

        # Add section headers and table
        sheet.merge_range(self.TABLE_START_ROW-2, 0,
                          self.TABLE_START_ROW-2, len(columns)-1,
                          None, blue_header)
        sheet.merge_range(self.TABLE_START_ROW-2, len(columns),
                          self.TABLE_START_ROW-2,
                          len(columns) + len(visits) - 1,
                          'Visits', green_header)
        sheet.merge_range(self.TABLE_START_ROW-2,
                          len(columns) + len(visits),
                          self.TABLE_START_ROW-2,
                          len(columns)+len(visits)+len(data_quality)-1,
                          'Data Quality', purple_header)
        sheet.merge_range(self.TABLE_START_ROW-2,
                          len(columns) + len(visits) + len(data_quality),
                          self.TABLE_START_ROW-2,
                          len(table_headers) - 1,
                          'Query Types', orange_header)
        sheet.add_table(self.TABLE_START_ROW-1, 0,
                        row-1, len(table_headers)-1, {
                            'autofilter': True, 'name': table_name,
                            'columns': table_headers})
        sheet.set_row(self.TABLE_START_ROW-1, 75)

        # Set column widths
        columns.extend(visits)
        columns.extend(data_quality)
        columns.extend([(name, 10, 'sum') for _, name in self.qc_types])
        for col, (name, width, formula) in enumerate(columns):
            sheet.set_column(col, col, width)

            # Calculate summary formula
            cell_format = self.formats['blue_number']
            if 'float' in formula:
                cell_format = self.formats['blue_float']
            if 'percent' in formula:
                cell_format = self.formats['blue_percent']
            if 'max_bad' in formula:
                sheet.conditional_format(
                    self.TABLE_START_ROW, col, row-1, col, {
                        'type': '3_color_scale',
                        'min_color': '#63BE7B',
                        'mid_color': '#FFEB84',
                        'max_color': '#F8696B'
                    })
            if 'max_good' in formula:
                sheet.conditional_format(
                    self.TABLE_START_ROW, col, row-1, col, {
                        'type': '3_color_scale',
                        'min_color': '#F8696B',
                        'mid_color': '#FFEB84',
                        'max_color': '#63BE7B'
                    })
            if 'gt0' in formula:
                sheet.conditional_format(
                    self.TABLE_START_ROW, col, row-1, col, {
                        'type': 'cell',
                        'criteria': '>',
                        'value': 0,
                        'format': self.formats['red_number']
                    })

            # Now generate the correct formula, replacing existing tokens
            if 'sum' in formula:
                formula = f'=SUBTOTAL(109, {table_name}[{name}])'
            elif 'count' in formula:
                formula = f'=SUBTOTAL(103, {table_name}[{name}])'
            elif '%final' in formula:
                # Beware of cell offsets!
                formula = '=IFERROR({final}/{nrecs}, 0.0)'.format(
                    final=xl_rowcol_to_cell(row, col-1),
                    nrecs=xl_rowcol_to_cell(row, col-2))
            elif '%complete' in formula:
                # Beware of cell offsets!
                formula = '=IFERROR({final}/{complete}, 0.0)'.format(
                    final=xl_rowcol_to_cell(row, col-3),
                    complete=xl_rowcol_to_cell(row, col-1))
            elif 'qcs_subject' in formula:
                # Beware of cell offsets!
                formula = '=IFERROR({qcs}/{npids}, 0.0)'.format(
                    qcs=xl_rowcol_to_cell(row, col-2),
                    npids=xl_rowcol_to_cell(row, col-12))

            sheet.write(row, col, formula, cell_format)

    def write_metrics(self, sheet, row, col, metrics):
        '''write QualityStats metrics to the worksheet'''
        number_format = self.formats['number']
        percent_format = self.formats['percent']
        float_format = self.formats['float']
        sheet.write(row, col, metrics.nvisits, number_format)
        sheet.write(row, col+1, metrics.nreports, number_format)
        sheet.write(row, col+2, metrics.nvisitslost, number_format)
        sheet.write(row, col+3, metrics.nconsecoverdue, number_format)
        sheet.write(row, col+4, metrics.nrecs, number_format)
        sheet.write(row, col+5, metrics.nfinalrecs, number_format)
        sheet.write(row, col+6, metrics.percent_final, percent_format)
        sheet.write(row, col+7, metrics.expected_recs, number_format)
        sheet.write(row, col+8, metrics.percent_complete, percent_format)
        sheet.write(row, col+9, metrics.total_qcs, number_format)
        sheet.write(row, col+10, metrics.qc_nrecs, number_format)
        sheet.write(row, col+11, metrics.qcs_per_patient, float_format)
        sheet.write(row, col+12, metrics.qc_gt60days, number_format)
        for qc_col, (qc_type, _) in enumerate(self.qc_types):
            sheet.write(row, col+qc_col+13, metrics.qc_types[qc_type],
                        number_format)
        return col

    def close_workbook(self):
        '''finalizes the tables and closes the workbook'''
        self.add_table(self.country_sheet, 'Countries', self.country_row, [
            ('Country', 15, 'count'),
            ('Subjects Recruited', 10, 'sum')
        ])
        self.add_table(self.site_sheet, 'Sites', self.site_row, [
            ('Country', 15, 'count'),
            ('Site', 10, 'count'),
            ('Investigator', 30, 'count'),
            ('Subjects Recruited', 10, 'sum'),
        ])
        self.add_table(self.subject_sheet, 'Subjects', self.subject_row, [
            ('Country', 15, 'count'),
            ('Site', 10, 'count'),
            ('Investigator', 30, 'count'),
            ('Subject', 10, 'count')
        ])
        self.workbook.close()