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

'''Sites related code'''

from .rangelist import SubjectList, SiteList

#############################################################################
# Site - An entry from the centers database
#############################################################################
class Site:
    '''Site information'''
    def __init__(self, number):
        self._number = number
        self.is_error_monitor = False
        self.contact = ''
        self.name = ''
        self.address = ''
        self.fax = ''
        self.region = 'Unknown'
        self.country = 'Unknown'
        self.begin_date = None
        self.end_date = None
        self.enroll = 0
        self.protocol1 = ''
        self.protocol1_date = None
        self.protocol2 = ''
        self.protocol2_date = None
        self.protocol3 = ''
        self.protocol3_date = None
        self.protocol4 = ''
        self.protocol4_date = None
        self.protocol5 = ''
        self.protocol5_date = None
        self.test_site = 0
        self.phone = ''
        self.investigator = ''
        self.investigator_phone = ''
        self.reply_address = ''
        self.patients = SubjectList()

    @classmethod
    def from_dfcenters(cls, line):
        '''Create Site entry from DFcenters database entry'''
        fields = line.split('|')
        if len(fields) < 11:
            raise ValueError('Incorrectly formatted DFcenters entry: ' + line)
        site = cls(int(fields[0]))
        site.contact = fields[1]
        site.name = fields[2]
        site.address = fields[3]
        site.fax = fields[4]

        # decode attributes
        variable_map = {
            'county': 'country',
            'beginDate': 'begin_date',
            'endDate': 'end_date',
            'enroll': 'enroll',
            'protocol1': 'protocol1',
            'protocol1Date': 'protocol1_date',
            'protocol2': 'protocol2',
            'protocol2Date': 'protocol2_date',
            'protocol3': 'protocol3',
            'protocol3Date': 'protocol3_date',
            'protocol4': 'protocol4',
            'protocol4Date': 'protocol4_date',
            'protocol5': 'protocol5',
            'protocol5Date': 'protocol5_date',
            'testSite': 'test_site'
        }
        for attribute in fields[5].split(';'):
            attribute = attribute.split(':')
            if len(attribute) < 2:
                continue
            key, value = attribute[0].strip(), attribute[1].strip()
            if key in variable_map:
                setattr(site, variable_map[key], value)

        site.phone = fields[6]
        site.investigator = fields[7]
        site.investigator_phone = fields[8]
        site.reply_address = fields[9]
        if fields[10] == 'ERROR MONITOR':
            site.is_error_monitor = True
        else:
            for i in range(10, len(fields)):
                pid_list = fields[i].split(' ')
                if len(pid_list) == 2:
                    site.patients.append(int(pid_list[0]),
                                         int(pid_list[1]))
        return site

    def __repr__(self):
        '''Printable version of the entry'''
        return '{}: {}, patients: {}'.format(self._number, self.name,
                                             str(self.patients))

    @property
    def number(self):
        '''Gets site number'''
        return self._number

    def update_location(self, region, country):
        '''Sets or updates region or country information'''
        self.region = region
        self.country = country

    def __lt__(self, other):
        return self.number < other.number

#############################################################################
# Sites - Site Database
#############################################################################
class Sites:
    '''Sites Database'''
    def __init__(self):
        self._sites = []

    def __iter__(self):
        return iter(self._sites)

    def load(self, centersdb_string):
        '''Load centers database string'''
        lines = centersdb_string.splitlines()
        self._sites = [Site.from_dfcenters(line) for line in lines]

    def pid_to_site_number(self, pid):
        '''Find the site number for patient'''
        site = self.pid_to_site(pid)
        return site.number if site else 0

    def pid_to_site(self, pid):
        '''Find the Site entry for patient'''
        error_monitor = None
        for site in self._sites:
            if pid in site.patients:
                return site
            if site.is_error_monitor:
                error_monitor = site
        return error_monitor

    def merge_countries(self, countries_string):
        '''Merges DFcountries style region/country information file'''
        lines = countries_string.splitlines()
        for line in lines:
            fields = line.split('|')
            if len(fields) < 3:
                raise ValueError('Incorrectly formatted DFcountries entry: ' + \
                                  line)
            country = fields[0]
            region = fields[1]
            sites = SiteList()
            sites.from_string(fields[2])
            for site in self._sites:
                if site.number in sites:
                    site.update_location(region, country)
