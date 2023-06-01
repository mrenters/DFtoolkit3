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
'''This file implements a recruitment report'''

import logging
from collections import Counter
from datetime import date, timedelta
from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell

from dftoolkit.rangelist import SiteList

def nmonths(min_dt, max_dt):
    '''returns the number of months of date ranges'''
    return (max_dt.year - min_dt.year)*12 + \
           (max_dt.month - min_dt.month) + 1

def month_columns(min_dt, max_dt):
    '''return Mon-YY column names for columns from max_dt to min_dt'''
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    year = max_dt.year
    month = max_dt.month
    columns = []
    while year > min_dt.year or \
        (year == min_dt.year and month >= min_dt.month):
        columns.append(f'{months[month-1]}-{year%100:02}')
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return columns

def days(from_dt, to_dt):
    '''returns the number of days betwen two dates'''
    return (to_dt - from_dt).days if from_dt and to_dt else None

class RecruitmentData:
    '''A class for holding site recruitment data'''
    def __init__(self, activation=None, deactivation=None):
        self.activation = activation
        self.deactivation = deactivation
        self.firstpt = None
        self.lastpt = None
        self.ptevents = Counter()

    def activate(self, dat):
        '''Activate the site'''
        self.activation = dat

    def deactivate(self, dat):
        '''Deactivate the site'''
        self.deactivation = dat

    def recruit(self, dat):
        '''Recruit a patient. This will also set activation, first/last pt'''
        if not self.activation or self.activation > dat:
            self.activation = dat
        if not self.firstpt or dat < self.firstpt:
            self.firstpt = dat
        if not self.lastpt or dat > self.lastpt:
            self.lastpt = dat
        self.ptevents[dat] += 1

    @property
    def total_pts(self):
        '''return the total number of patients for this site'''
        return sum(self.ptevents.values())

    def days_active(self, now):
        '''return the number of days this site has been active'''
        return (now-self.activation).days if self.activation else 0

    def days_firstpt(self, now):
        '''return the number of days since first pt was recruited'''
        return (now-self.firstpt).days if self.firstpt else 0

    def count_between(self, start, end):
        '''Return the number of patients activated start, end'''
        return sum([cnt for dat, cnt in self.ptevents.items() \
                   if start <= dat <= end])

    def first_count(self, end_dt, ndays):
        '''return patient count for the first ndays'''
        if not self.firstpt or end_dt < self.firstpt:
            return 0
        end_dt = min(end_dt, self.firstpt + timedelta(ndays-1))
        return self.count_between(self.firstpt, end_dt)

    def last_count(self, end_dt, ndays):
        '''return patient count for the last ndays'''
        return self.count_between(end_dt - timedelta(ndays-1), end_dt)

    def count_yymm(self, yymm, end_dt):
        '''Return the number of patients activated in YYMM'''
        return sum([cnt for dat, cnt in self.ptevents.items() \
                   if dat <= end_dt and \
                      yymm.year == dat.year and yymm.month == dat.month])

    def mean_activation(self, end_dt):
        '''mean recruitment since activation'''
        days_active = self.days_active(end_dt)
        if days_active < 1:
            return 0.0

        periods_active = ((days_active-1)//30)+1.0
        return self.count_between(self.firstpt, end_dt) / periods_active

    def mean_firstpt(self, end_dt):
        '''mean recruitment since first patient'''
        days_active = self.days_firstpt(end_dt)
        if days_active < 1:
            return 0.0

        periods_active = ((days_active-1)//30)+1.0
        return self.count_between(self.firstpt, end_dt) / periods_active

    def best(self, end_dt, ndays):
        '''Returns count, start, end date for the best nday period'''
        ptevents = list(filter(lambda x: x[0] <= end_dt, self.ptevents.items()))
        if not ptevents:
            return (0, None, None)

        dates, counts = zip(*sorted(ptevents))

        best_start_dat = best_end_dat = cur_start_dat = cur_end_dat = dates[0]
        best_count = cur_count = cur_start_idx = 0

        for idx, dat in enumerate(dates):
            # Have we exceeded the ndays window?
            if (dat-cur_start_dat).days >= ndays:
                if cur_count >= best_count:
                    best_count = cur_count
                    best_start_dat = cur_start_dat
                    best_end_dat = cur_end_dat

                # bring us back under the ndays window and subtract
                # patient counts that are outside of the current window
                while cur_start_idx < idx:
                    cur_count -= counts[cur_start_idx]
                    assert cur_count >= 0
                    cur_start_idx += 1
                    cur_start_dat = dates[cur_start_idx]

                    if (dat-cur_start_dat).days < ndays:
                        break

            cur_end_dat = dat
            cur_count += counts[idx]

        # If we have a new local maximum at the end, save it
        if cur_count >= best_count:
            best_count = cur_count
            best_start_dat = cur_start_dat
            best_end_dat = cur_end_dat

        return (best_count, best_start_dat, best_end_dat)

class RecruitmentReport:
    '''A recruitment report'''
    def __init__(self, study, config):
        self.study = study
        self.enddate = config.get('enddate', date.today())
        self.ndays = config.get('ndays', 90)
        self.site_list = config.get('sites', SiteList(default_all=True))
        self.total_target = config.get('target', 0)
        self.sitedata = {
            site: RecruitmentData(site.begin_date, site.end_date) \
                for site in study.sites if not site.is_error_monitor
        }

    def read_events(self, path):
        '''Read study events in the form command|site|date'''
        sites = self.study.sites
        with open(path, 'r') as events:
            for line in events.read().splitlines():
                try:
                    command, site_str, dat = line.split('|')
                except (IndexError, ValueError, TypeError):
                    logging.warning('Bad events entry: %s', line)
                    continue

                try:
                    site = sites.get_site(int(site_str))
                except (IndexError, ValueError, TypeError):
                    logging.warning('Bad/Unknown site number in entry: %s',
                                    line)
                    continue

                try:
                    dat = date(*map(int, dat.replace('/', '-').split('-')))
                except (IndexError, ValueError, TypeError):
                    logging.warning('Bad date (YYYY/MM/DD) in entry: %s', line)
                    continue

                # Are we filtering out this site?
                if site.number not in self.site_list:
                    continue

                sitedata = self.sitedata.get(site)
                if command in ('randomize', 'enroll'):
                    sitedata.recruit(dat)
                elif command == 'activate':
                    sitedata.activate(dat)
                elif command == 'deactivate':
                    sitedata.deactivate(dat)
                else:
                    logging.error('Bad command: %s', line)

    def activation_epoch(self):
        '''Find the earilest activation date'''
        activations = [
            data.activation for data in self.sitedata.values() \
            if data.activation
        ]
        return min(activations) if activations else None

    def generate_xlsx(self, filename):
        '''generate an Excel file of the recruitment data'''
        # Find the earliest activation date
        start_dt = self.enddate
        for data in self.sitedata.values():
            if data.activation and data.activation < start_dt:
                start_dt = data.activation

        xlsx = RecruitmentXLSX(filename, start_dt, self.enddate, self.ndays,
                               self.total_target)
        for site, data in sorted(self.sitedata.items(),
                                 key=lambda x: x[0].number):
            if not site.number in self.site_list:
                continue
            xlsx.add_site(site, data)
        xlsx.close_workbook()

class RecruitmentXLSX:
    '''Generate an Excel recruitment report'''
    def __init__(self, filename, min_dt, max_dt, ndays, total_target):
        self.workbook = Workbook(filename)
        self.min_dt = min_dt
        self.max_dt = max_dt
        self.ndays = ndays
        self.total_target = total_target
        self.monthly_column_start = 0
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
            'number':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
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
            }),
            'red':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#9c0006',
                'bg_color': '#ffc7ce',
                'text_wrap': True,
                'num_format': '0',
            }),
            'blue':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#244062',
                'bg_color': '#dce6f1',
                'text_wrap': True,
                'num_format': '0',
            }),
            'gray':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#000000',
                'bg_color': '#cccccc',
                'text_wrap': True,
                'num_format': '0',
            }),
            'darkgray':  self.workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#ffffff',
                'bg_color': '#888888',
                'text_wrap': True,
                'num_format': '0',
            })
        }
        self.worksheet = self.workbook.add_worksheet('Data')
        self.row = 1

    def add_site(self, site, data):
        '''add a row with the site information'''
        row = self.row
        sheet = self.worksheet
        sheet.set_row(row, 45)
        sheet.write_string(row, 0, site.country, self.formats['string'])
        sheet.write_number(row, 1, site.number, self.formats['number'])
        sheet.write_string(row, 2, site.name, self.formats['string'])
        sheet.write_string(row, 3, site.investigator,
                           self.formats['string'])
        sheet.write(row, 4, data.deactivation, self.formats['date'])
        sheet.write(row, 5, data.activation, self.formats['date'])
        sheet.write(row, 6, data.firstpt, self.formats['date'])
        sheet.write(row, 7, data.lastpt, self.formats['date'])
        sheet.write(row, 8, days(data.activation, self.max_dt),
                    self.formats['number'])
        sheet.write(row, 9, days(data.activation, data.firstpt),
                    self.formats['number'])
        sheet.write(row, 10, days(data.lastpt, self.max_dt),
                    self.formats['number'])
        best_count, _, best_end = data.best(self.max_dt, self.ndays)
        sheet.write(row, 11, days(best_end, self.max_dt),
                    self.formats['number'])
        sheet.write(row, 12, best_count/(self.ndays/30.0),
                    self.formats['float'])
        sheet.write(row, 13,
                    data.last_count(self.max_dt, self.ndays)/(self.ndays/30.0),
                    self.formats['float'])
        sheet.write(row, 14,
                    data.first_count(self.max_dt, self.ndays)/(self.ndays/30.0),
                    self.formats['float'])
        sheet.write(row, 15, data.mean_activation(self.max_dt),
                    self.formats['float'])
        sheet.write(row, 16, data.mean_firstpt(self.max_dt),
                    self.formats['float'])
        sheet.write(row, 17, data.count_between(self.min_dt, self.max_dt),
                    self.formats['number'])
        sheet.write(row, 18, site.enroll, self.formats['number'])
        sheet.write(row, 19, '=IFERROR({0}/{1}, "")'.format(
            xl_rowcol_to_cell(row, 17),
            xl_rowcol_to_cell(row, 18)),
                    self.formats['percent'])
        sheet.add_sparkline(row, 20, {'range': '{0}:{1}'.format(
            xl_rowcol_to_cell(row, 21),
            xl_rowcol_to_cell(row, 21 + nmonths(self.min_dt, self.max_dt)-1))})

        col = 21
        current = date(self.max_dt.year, self.max_dt.month, 1)
        end = self.min_dt
        while current.year > end.year or \
            (current.year == end.year and current.month >= end.month):
            count = data.count_yymm(current, self.max_dt)
            before_activation = not data.activation or \
                current.year < data.activation.year or \
                (current.year == data.activation.year and \
                 current.month < data.activation.month)
            before_firstpt = not data.firstpt or \
                current.year < data.firstpt.year or \
                (current.year == data.firstpt.year and \
                 current.month < data.firstpt.month)
            after_deactivation = data.deactivation and \
                (current.year > data.deactivation.year or \
                (current.year == data.deactivation.year and \
                 current.month > data.deactivation.month))
            if before_activation or after_deactivation:
                sheet.write(row, col, None, self.formats['darkgray'])
            elif before_firstpt:
                sheet.write_string(row, col, '', self.formats['gray'])
            elif count > 0:
                sheet.write(row, col, count, self.formats['blue'])
            else:
                sheet.write(row, col, count, self.formats['red'])

            if current.month == 1:
                current = current.replace(year=current.year-1, month=12)
            else:
                current = current.replace(month=current.month-1)

            col += 1
        self.row = row + 1

    def add_table(self):
        '''add the table to the workbook'''
        sheet = self.worksheet
        columns = [
            ('Country', 15, 'none'),
            ('Site', 9, 'none'),
            ('Name', 20, 'none'),
            ('Investigator', 20, 'none'),
            ('Deactivation', 12, 'none'),
            ('Activation', 12, 'none'),
            ('First Subject', 12, 'none'),
            ('Last Subject', 12, 'none'),
            ('Days Since Activation', 11, 'max_good, mean'),
            ('Days to First Subject', 11, 'min_good, mean'),
            ('Days since Last Subject', 11, 'min_good, mean'),
            ('Days since Best Recruit', 11, 'min_good, mean'),
            (f'Best Recruit Rate\n({self.ndays} days)', 11, 'max_good, mean'),
            (f'Last Recruit Rate\n({self.ndays} days)', 11, 'max_good, mean'),
            (f'First Recruit Rate\n({self.ndays} days)', 11, 'max_good, mean'),
            ('Mean Recruit Rate\n(Activation)', 11, 'max_good, mean'),
            ('Mean Recruit Rate\n(First Subj)', 11, 'max_good, mean'),
            ('Total Subjects', 11, 'max_good, sum'),
            ('Target', 11, 'max_good, total_target'),
            ('% of Target', 11, 'max_good, target%'),
            ('Performance Graph\n(Most to Least Recent)', 25, 'labels')
        ]
        self.monthly_column_start = len(columns)
        # Add in Monthly data
        for colname in month_columns(self.min_dt, self.max_dt):
            columns.append((colname, 8, 'sum, stats'))

        # If no data, don't add the table
        if self.row == 1:
            sheet.merge_range(0, 0, 0, len(columns)-1, 'No recruitment data')
            return

        sheet.set_row(0, 90)

        # Set column widths, coloring and totaling
        for colno, (colname, colwidth, coding) in enumerate(columns):
            sheet.set_column(colno, colno, colwidth)
            if 'max_good' in coding:
                sheet.conditional_format(1, colno, self.row-1, colno, {
                    'type': '3_color_scale',
                    'min_color': "#F8696B",
                    'mid_color': "#FFEB84",
                    'max_color': "#63BE7b"})
            if 'min_good' in coding:
                sheet.conditional_format(1, colno, self.row-1, colno, {
                    'type': '3_color_scale',
                    'max_color': "#F8696B",
                    'mid_color': "#FFEB84",
                    'min_color': "#63BE7b"})
            if 'sum' in coding:
                sheet.write(self.row, colno,
                            f'=SUBTOTAL(109, Data[{colname}])',
                            self.formats['number'])
            if 'stats' in coding:
                # Cumulative total
                sheet.write(self.row+1, colno,
                            '=SUM({0}:{1})'.format(
                                xl_rowcol_to_cell(self.row, colno),
                                xl_rowcol_to_cell(self.row, len(columns))),
                            self.formats['number'])
                # Sites Recruiting
                sheet.write(self.row+2, colno,
                            f'=SUBTOTAL(102, Data[{colname}])',
                            self.formats['number'])
                # Sites Open
                sheet.write(self.row+3, colno,
                            f'=SUBTOTAL(103, Data[{colname}])',
                            self.formats['number'])
                # % Recruiting
                sheet.write(self.row+4, colno,
                            '=IFERROR({0}/{1}, 0)'.format(
                                xl_rowcol_to_cell(self.row+2, colno),
                                xl_rowcol_to_cell(self.row+3, colno)),
                            self.formats['percent'])
                # Rate Recruiting
                sheet.write(self.row+5, colno,
                            '=IFERROR({0}/{1}, 0)'.format(
                                xl_rowcol_to_cell(self.row, colno),
                                xl_rowcol_to_cell(self.row+2, colno)),
                            self.formats['float'])
                # Rate Open
                sheet.write(self.row+6, colno,
                            '=IFERROR({0}/{1}, 0)'.format(
                                xl_rowcol_to_cell(self.row, colno),
                                xl_rowcol_to_cell(self.row+3, colno)),
                            self.formats['float'])
            if 'mean' in coding:
                sheet.write(self.row, colno,
                            f'=IFERROR(SUBTOTAL(101, Data[{colname}]), "")',
                            self.formats['float'])
            if 'total_target' in coding:
                sheet.write(self.row, colno,
                            self.total_target if self.total_target else None,
                            self.formats['number'])
            if 'target%' in coding:
                sheet.write(self.row, colno,
                            '=IFERROR({0}/{1}, "")'.format(
                                xl_rowcol_to_cell(self.row, colno-2),
                                xl_rowcol_to_cell(self.row, colno-1)),
                            self.formats['percent'])
            if 'labels' in coding:
                sheet.write(self.row, colno, 'Total', self.formats['header'])
                sheet.write(self.row+1, colno, 'Cumulative Total',
                            self.formats['header'])
                sheet.write(self.row+2, colno, 'Sites Recruiting',
                            self.formats['header'])
                sheet.write(self.row+3, colno, 'Sites Open',
                            self.formats['header'])
                sheet.write(self.row+4, colno, '%Recruiting',
                            self.formats['header'])
                sheet.write(self.row+5, colno, 'Rate (recruiting)',
                            self.formats['header'])
                sheet.write(self.row+6, colno, 'Rate (open)',
                            self.formats['header'])

        headers = [
            {'header': colname, 'header_format': self.formats['header']} \
            for colname, _, coding in columns]
        sheet.add_table(0, 0, self.row-1, len(columns)-1, {
            'autofilter': True, 'name': 'Data', 'columns': headers})
        sheet.set_zoom(80)
        sheet.freeze_panes(1, 2)

    def add_charts(self):
        '''Add Recruitment charts'''
        if self.row == 1:
            return
        monthly_start = self.monthly_column_start
        monthly_end = monthly_start + nmonths(self.min_dt, self.max_dt) - 1
        sheet = self.workbook.add_worksheet('Charts')
        chart = self.workbook.add_chart({'type': 'column'})
        chart.add_series({
            'categories': ['Data', 0, monthly_start, 0, monthly_end],
            'values': ['Data', self.row, monthly_start, self.row, monthly_end],
            'name': 'Subjects'
        })
        chart.set_title({'name': 'Subject Recruitment by Month'})
        chart.set_x_axis({'reverse': True})
        chart.set_size({
            'width': 1000,
            'height': 600,
            'x_offset': 20,
            'y_offset': 30
        })
        chart.set_legend({'position': 'bottom'})
        sheet.insert_chart(0, 0, chart)

        chartcumlulative = self.workbook.add_chart({'type': 'column'})
        chartcumlulative.add_series({
            'categories': ['Data', 0, monthly_start, 0, monthly_end],
            'values': ['Data', self.row+1, monthly_start,
                       self.row+1, monthly_end],
            'name': 'Cumulative Total'
        })
        chartcumlulative.set_title({
            'name': 'Subject Recruitment Cumulative Total'
        })
        chartcumlulative.set_x_axis({'reverse': True})
        chartcumlulative.set_size({
            'width': 1000,
            'height': 600,
            'x_offset': 20,
            'y_offset': 720
        })
        chartcumlulative.set_legend({'position': 'bottom'})
        sheet.insert_chart(0, 0, chartcumlulative)

        # Sites
        chartsites = self.workbook.add_chart({'type': 'line'})
        chartsites.add_series({
            'values': ['Data', self.row+3, monthly_start,
                       self.row+3, monthly_end],
            'name': 'Open Sites',
            'marker': {'type': 'diamond'}
        })
        chartsites.add_series({
            'categories': ['Data', 0, monthly_start, 0, monthly_end],
            'values': ['Data', self.row+2, monthly_start,
                       self.row+2, monthly_end],
            'name': 'Recruiting Sites',
            'marker': {'type': 'diamond'}
        })
        chartsites.set_title({'name': 'Site Recruitment'})
        chartsites.set_x_axis({'reverse': True})
        chartsites.set_size({
            'width': 1000,
            'height': 600,
            'x_offset': 20,
            'y_offset': 1440
        })
        chartsites.set_legend({'position': 'bottom'})
        sheet.insert_chart(0, 0, chartsites)
        sheet.hide_gridlines(2)

    def close_workbook(self):
        '''close the workbook'''
        self.add_table()
        self.add_charts()
        self.workbook.close()
