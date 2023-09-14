#
# Copyright 2020-2023, Martin Renters
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

from collections import namedtuple
from datetime import date
from .rangelist import SubjectList, SiteList

#############################################################################
# COUNTRY MAPPING
#############################################################################
CountryRegion = namedtuple('CountryRegion', ['country', 'region'])
countryregion = {
    "ABW": CountryRegion('Aruba', 'Caribbean'),
    "AFG": CountryRegion('Afghanistan', 'Southern Asia'),
    "AGO": CountryRegion('Angola', 'Middle Africa'),
    "AIA": CountryRegion('Anguilla', 'Caribbean'),
    "ALA": CountryRegion('Aland Islands', 'Northern Europe'),
    "ALB": CountryRegion('Albania', 'Southern Europe'),
    "AND": CountryRegion('Andorra', 'Southern Europe'),
    "ANT": CountryRegion('Netherlands Antilles', ''),
    "ARE": CountryRegion('United Arab Emirates', 'Western Asia'),
    "ARG": CountryRegion('Argentina', 'South America'),
    "ARM": CountryRegion('Armenia', 'Western Asia'),
    "ASM": CountryRegion('American Samoa', 'Polynesia'),
    "ATA": CountryRegion('Antarctica', 'Antarctica'),
    "ATF": CountryRegion('French Southern Territories', 'Eastern Africa'),
    "ATG": CountryRegion('Antigua and Barbuda', 'Caribbean'),
    "AUS": CountryRegion('Australia', 'Australia and New Zealand'),
    "AUT": CountryRegion('Austria', 'Western Europe'),
    "AZE": CountryRegion('Azerbaijan', 'Western Asia'),
    "BA1": CountryRegion('British Antarctic Territories', ''),
    "BDI": CountryRegion('Burundi', 'Eastern Africa'),
    "BEL": CountryRegion('Belgium', 'Western Europe'),
    "BEN": CountryRegion('Benin', 'Western Africa'),
    "BES": CountryRegion('Bonaire, Saint Eustatius and Saba', 'Caribbean'),
    "BFA": CountryRegion('Burkina Faso', 'Western Africa'),
    "BGD": CountryRegion('Bangladesh', 'Southern Asia'),
    "BGR": CountryRegion('Bulgaria', 'Eastern Europe'),
    "BHR": CountryRegion('Bahrain', 'Western Asia'),
    "BHS": CountryRegion('Bahamas', 'Caribbean'),
    "BIH": CountryRegion('Bosnia and Herzegovina', 'Southern Europe'),
    "BLM": CountryRegion('St. Barths', 'Caribbean'),
    "BLR": CountryRegion('Belarus', 'Eastern Europe'),
    "BLZ": CountryRegion('Belize', 'Central America'),
    "BMU": CountryRegion('Bermuda', 'North America'),
    "BOL": CountryRegion('Bolivia', 'South America'),
    "BRA": CountryRegion('Brazil', 'South America'),
    "BRB": CountryRegion('Barbados', 'Caribbean'),
    "BRN": CountryRegion('Brunei Darussalam', 'South-eastern Asia'),
    "BTN": CountryRegion('Bhutan', 'Southern Asia'),
    "BVT": CountryRegion('Bouvet Island', 'South America'),
    "BWA": CountryRegion('Botswana', 'Southern Africa'),
    "CAF": CountryRegion('Central African Republic', 'Middle Africa'),
    "CAN": CountryRegion('Canada', 'North America'),
    "CCK": CountryRegion('Cocos (Keeling) Islands', 'Australia and New Zealand'),
    "CHE": CountryRegion('Switzerland', 'Western Europe'),
    "CHI": CountryRegion('Channel Islands', 'Northern Europe'),
    "CHL": CountryRegion('Chile', 'South America'),
    "CHN": CountryRegion('China', 'Eastern Asia'),
    "CIV": CountryRegion("Cote d'Ivoire", 'Western Africa'),
    "CMR": CountryRegion('Cameroon', 'Middle Africa'),
    "COD": CountryRegion('DR Congo', 'Middle Africa'),
    "COG": CountryRegion('Congo Republic', 'Middle Africa'),
    "COK": CountryRegion('Cook Islands', 'Polynesia'),
    "COL": CountryRegion('Colombia', 'South America'),
    "COM": CountryRegion('Comoros', 'Eastern Africa'),
    "CPV": CountryRegion('Cabo Verde', 'Western Africa'),
    "CRI": CountryRegion('Costa Rica', 'Central America'),
    "CUB": CountryRegion('Cuba', 'Caribbean'),
    "CUW": CountryRegion('Curacao', 'Caribbean'),
    "CXR": CountryRegion('Christmas Island', 'Australia and New Zealand'),
    "CYM": CountryRegion('Cayman Islands', 'Caribbean'),
    "CYP": CountryRegion('Cyprus', 'Western Asia'),
    "CZE": CountryRegion('Czech Republic', 'Eastern Europe'),
    "DEU": CountryRegion('Germany', 'Western Europe'),
    "DJI": CountryRegion('Djibouti', 'Eastern Africa'),
    "DMA": CountryRegion('Dominica', 'Caribbean'),
    "DNK": CountryRegion('Denmark', 'Northern Europe'),
    "DOM": CountryRegion('Dominican Republic', 'Caribbean'),
    "DZA": CountryRegion('Algeria', 'Northern Africa'),
    "EAT": CountryRegion('Tanganjika', 'Eastern Africa'),
    "EAZ": CountryRegion('Zanzibar', 'Eastern Africa'),
    "ECU": CountryRegion('Ecuador', 'South America'),
    "EGY": CountryRegion('Egypt', 'Northern Africa'),
    "ERI": CountryRegion('Eritrea', 'Eastern Africa'),
    "ESH": CountryRegion('Western Sahara', 'Northern Africa'),
    "ESP": CountryRegion('Spain', 'Southern Europe'),
    "EST": CountryRegion('Estonia', 'Northern Europe'),
    "ETH": CountryRegion('Ethiopia', 'Eastern Africa'),
    "FIN": CountryRegion('Finland', 'Northern Europe'),
    "FJI": CountryRegion('Fiji', 'Melanesia'),
    "FLK": CountryRegion('Falkland Islands', 'South America'),
    "FRA": CountryRegion('France', 'Western Europe'),
    "FRO": CountryRegion('Faroe Islands', 'Northern Europe'),
    "FSM": CountryRegion('Micronesia, Fed. Sts.', 'Micronesia'),
    "GAB": CountryRegion('Gabon', 'Middle Africa'),
    "GBR": CountryRegion('United Kingdom', 'Northern Europe'),
    "GEO": CountryRegion('Georgia', 'Western Asia'),
    "GGY": CountryRegion('Guernsey', 'Northern Europe'),
    "GHA": CountryRegion('Ghana', 'Western Africa'),
    "GIB": CountryRegion('Gibraltar', 'Southern Europe'),
    "GIN": CountryRegion('Guinea', 'Western Africa'),
    "GLP": CountryRegion('Guadeloupe', 'Caribbean'),
    "GMB": CountryRegion('Gambia', 'Western Africa'),
    "GNB": CountryRegion('Guinea-Bissau', 'Western Africa'),
    "GNQ": CountryRegion('Equatorial Guinea', 'Middle Africa'),
    "GRC": CountryRegion('Greece', 'Southern Europe'),
    "GRD": CountryRegion('Grenada', 'Caribbean'),
    "GRL": CountryRegion('Greenland', 'North America'),
    "GTM": CountryRegion('Guatemala', 'Central America'),
    "GUF": CountryRegion('French Guiana', 'South America'),
    "GUM": CountryRegion('Guam', 'Micronesia'),
    "GUY": CountryRegion('Guyana', 'South America'),
    "HKG": CountryRegion('Hong Kong', 'Eastern Asia'),
    "HMD": CountryRegion('Heard and McDonald Islands', 'Australia and New Zealand'),
    "HND": CountryRegion('Honduras', 'Central America'),
    "HRV": CountryRegion('Croatia', 'Southern Europe'),
    "HTI": CountryRegion('Haiti', 'Caribbean'),
    "HUN": CountryRegion('Hungary', 'Eastern Europe'),
    "IDN": CountryRegion('Indonesia', 'South-eastern Asia'),
    "IMN": CountryRegion('Isle of Man', 'Northern Europe'),
    "IND": CountryRegion('India', 'Southern Asia'),
    "IOT": CountryRegion('British Indian Ocean Territory', 'Eastern Africa'),
    "IRL": CountryRegion('Ireland', 'Northern Europe'),
    "IRN": CountryRegion('Iran', 'Southern Asia'),
    "IRQ": CountryRegion('Iraq', 'Western Asia'),
    "ISL": CountryRegion('Iceland', 'Northern Europe'),
    "ISR": CountryRegion('Israel', 'Western Asia'),
    "ITA": CountryRegion('Italy', 'Southern Europe'),
    "JAM": CountryRegion('Jamaica', 'Caribbean'),
    "JEY": CountryRegion('Jersey', 'Northern Europe'),
    "JOR": CountryRegion('Jordan', 'Western Asia'),
    "JPN": CountryRegion('Japan', 'Eastern Asia'),
    "KAZ": CountryRegion('Kazakhstan', 'Central Asia'),
    "KEN": CountryRegion('Kenya', 'Eastern Africa'),
    "KGZ": CountryRegion('Kyrgyz Republic', 'Central Asia'),
    "KHM": CountryRegion('Cambodia', 'South-eastern Asia'),
    "KIR": CountryRegion('Kiribati', 'Micronesia'),
    "KNA": CountryRegion('St. Kitts and Nevis', 'Caribbean'),
    "KOR": CountryRegion('South Korea', 'Eastern Asia'),
    "KWT": CountryRegion('Kuwait', 'Western Asia'),
    "LAO": CountryRegion('Laos', 'South-eastern Asia'),
    "LBN": CountryRegion('Lebanon', 'Western Asia'),
    "LBR": CountryRegion('Liberia', 'Western Africa'),
    "LBY": CountryRegion('Libya', 'Northern Africa'),
    "LCA": CountryRegion('St. Lucia', 'Caribbean'),
    "LIE": CountryRegion('Liechtenstein', 'Western Europe'),
    "LKA": CountryRegion('Sri Lanka', 'Southern Asia'),
    "LSO": CountryRegion('Lesotho', 'Southern Africa'),
    "LTU": CountryRegion('Lithuania', 'Northern Europe'),
    "LUX": CountryRegion('Luxembourg', 'Western Europe'),
    "LVA": CountryRegion('Latvia', 'Northern Europe'),
    "MAC": CountryRegion('Macau', 'Eastern Asia'),
    "MAF": CountryRegion('Saint-Martin', 'Caribbean'),
    "MAR": CountryRegion('Morocco', 'Northern Africa'),
    "MCO": CountryRegion('Monaco', 'Western Europe'),
    "MDA": CountryRegion('Moldova', 'Eastern Europe'),
    "MDG": CountryRegion('Madagascar', 'Eastern Africa'),
    "MDV": CountryRegion('Maldives', 'Southern Asia'),
    "MEX": CountryRegion('Mexico', 'Central America'),
    "MHL": CountryRegion('Marshall Islands', 'Micronesia'),
    "MKD": CountryRegion('North Macedonia', 'Southern Europe'),
    "MLI": CountryRegion('Mali', 'Western Africa'),
    "MLT": CountryRegion('Malta', 'Southern Europe'),
    "MMR": CountryRegion('Myanmar', 'South-eastern Asia'),
    "MNE": CountryRegion('Montenegro', 'Southern Europe'),
    "MNG": CountryRegion('Mongolia', 'Eastern Asia'),
    "MNP": CountryRegion('Northern Mariana Islands', 'Micronesia'),
    "MOZ": CountryRegion('Mozambique', 'Eastern Africa'),
    "MRT": CountryRegion('Mauritania', 'Western Africa'),
    "MSR": CountryRegion('Montserrat', 'Caribbean'),
    "MTQ": CountryRegion('Martinique', 'Caribbean'),
    "MUS": CountryRegion('Mauritius', 'Eastern Africa'),
    "MWI": CountryRegion('Malawi', 'Eastern Africa'),
    "MYS": CountryRegion('Malaysia', 'South-eastern Asia'),
    "MYT": CountryRegion('Mayotte', 'Eastern Africa'),
    "NAM": CountryRegion('Namibia', 'Southern Africa'),
    "NCL": CountryRegion('New Caledonia', 'Melanesia'),
    "NER": CountryRegion('Niger', 'Western Africa'),
    "NFK": CountryRegion('Norfolk Island', 'Australia and New Zealand'),
    "NGA": CountryRegion('Nigeria', 'Western Africa'),
    "NIC": CountryRegion('Nicaragua', 'Central America'),
    "NIU": CountryRegion('Niue', 'Polynesia'),
    "NLD": CountryRegion('Netherlands', 'Western Europe'),
    "NOR": CountryRegion('Norway', 'Northern Europe'),
    "NPL": CountryRegion('Nepal', 'Southern Asia'),
    "NRU": CountryRegion('Nauru', 'Polynesia'),
    "NZL": CountryRegion('New Zealand', 'Australia and New Zealand'),
    "OMN": CountryRegion('Oman', 'Western Asia'),
    "PAK": CountryRegion('Pakistan', 'Southern Asia'),
    "PAN": CountryRegion('Panama', 'Central America'),
    "PCN": CountryRegion('Pitcairn', 'Polynesia'),
    "PER": CountryRegion('Peru', 'South America'),
    "PHL": CountryRegion('Philippines', 'South-eastern Asia'),
    "PLW": CountryRegion('Palau', 'Micronesia'),
    "PNG": CountryRegion('Papua New Guinea', 'Melanesia'),
    "POL": CountryRegion('Poland', 'Eastern Europe'),
    "PRI": CountryRegion('Puerto Rico', 'Caribbean'),
    "PRK": CountryRegion('North Korea', 'Eastern Asia'),
    "PRT": CountryRegion('Portugal', 'Southern Europe'),
    "PRY": CountryRegion('Paraguay', 'South America'),
    "PSE": CountryRegion('Palestine', 'Western Asia'),
    "PYF": CountryRegion('French Polynesia', 'Polynesia'),
    "QAT": CountryRegion('Qatar', 'Western Asia'),
    "REU": CountryRegion('Reunion', 'Eastern Africa'),
    "ROU": CountryRegion('Romania', 'Eastern Europe'),
    "RUS": CountryRegion('Russia', 'Eastern Europe'),
    "RWA": CountryRegion('Rwanda', 'Eastern Africa'),
    "SAU": CountryRegion('Saudi Arabia', 'Western Asia'),
    "SDN": CountryRegion('Sudan', 'Northern Africa'),
    "SEN": CountryRegion('Senegal', 'Western Africa'),
    "SGP": CountryRegion('Singapore', 'South-eastern Asia'),
    "SGS": CountryRegion('South Georgia and South Sandwich Is.', 'South America'),
    "SHN": CountryRegion('St. Helena', 'Western Africa'),
    "SJM": CountryRegion('Svalbard and Jan Mayen Islands', 'Northern Europe'),
    "SLB": CountryRegion('Solomon Islands', 'Melanesia'),
    "SLE": CountryRegion('Sierra Leone', 'Western Africa'),
    "SLV": CountryRegion('El Salvador', 'Central America'),
    "SMR": CountryRegion('San Marino', 'Southern Europe'),
    "SOM": CountryRegion('Somalia', 'Eastern Africa'),
    "SPM": CountryRegion('St. Pierre and Miquelon', 'North America'),
    "SRB": CountryRegion('Serbia', 'Southern Europe'),
    "SSD": CountryRegion('South Sudan', 'Eastern Africa'),
    "STP": CountryRegion('Sao Tome and Principe', 'Middle Africa'),
    "SUN": CountryRegion('Soviet Union (former)', 'Eastern Europe'),
    "SUR": CountryRegion('Suriname', 'South America'),
    "SVK": CountryRegion('Slovakia', 'Eastern Europe'),
    "SVN": CountryRegion('Slovenia', 'Southern Europe'),
    "SWE": CountryRegion('Sweden', 'Northern Europe'),
    "SWZ": CountryRegion('Eswatini', 'Southern Africa'),
    "SXM": CountryRegion('Sint Maarten', 'Caribbean'),
    "SYC": CountryRegion('Seychelles', 'Eastern Africa'),
    "SYR": CountryRegion('Syria', 'Western Asia'),
    "TCA": CountryRegion('Turks and Caicos Islands', 'Caribbean'),
    "TCD": CountryRegion('Chad', 'Middle Africa'),
    "TGO": CountryRegion('Togo', 'Western Africa'),
    "THA": CountryRegion('Thailand', 'South-eastern Asia'),
    "TJK": CountryRegion('Tajikistan', 'Central Asia'),
    "TKL": CountryRegion('Tokelau', 'Polynesia'),
    "TKM": CountryRegion('Turkmenistan', 'Central Asia'),
    "TLS": CountryRegion('Timor-Leste', 'South-eastern Asia'),
    "TON": CountryRegion('Tonga', 'Polynesia'),
    "TTO": CountryRegion('Trinidad and Tobago', 'Caribbean'),
    "TUN": CountryRegion('Tunisia', 'Northern Africa'),
    "TUR": CountryRegion('Türkiye', 'Western Asia'),
    "TUV": CountryRegion('Tuvalu', 'Polynesia'),
    "TWN": CountryRegion('Taiwan', 'Eastern Asia'),
    "TZA": CountryRegion('Tanzania', 'Eastern Africa'),
    "UGA": CountryRegion('Uganda', 'Eastern Africa'),
    "UKR": CountryRegion('Ukraine', 'Eastern Europe'),
    "UMI": CountryRegion('United States Minor Outlying Islands', 'Micronesia'),
    "URY": CountryRegion('Uruguay', 'South America'),
    "USA": CountryRegion('United States', 'North America'),
    "UZB": CountryRegion('Uzbekistan', 'Central Asia'),
    "VAT": CountryRegion('Vatican', 'Southern Europe'),
    "VCT": CountryRegion('St. Vincent and the Grenadines', 'Caribbean'),
    "VEN": CountryRegion('Venezuela', 'South America'),
    "VGB": CountryRegion('British Virgin Islands', 'Caribbean'),
    "VIR": CountryRegion('United States Virgin Islands', 'Caribbean'),
    "VNM": CountryRegion('Vietnam', 'South-eastern Asia'),
    "VUT": CountryRegion('Vanuatu', 'Melanesia'),
    "WLF": CountryRegion('Wallis and Futuna Islands', 'Polynesia'),
    "WSM": CountryRegion('Samoa', 'Polynesia'),
    "XKX": CountryRegion('Kosovo', 'Southern Europe'),
    "YEM": CountryRegion('Yemen', 'Western Asia'),
    "ZAF": CountryRegion('South Africa', 'Southern Africa'),
    "ZMB": CountryRegion('Zambia', 'Eastern Africa'),
    "ZWE": CountryRegion('Zimbabwe', 'Eastern Africa'),
}

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
        self._region = None
        self._country = None
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
            'country': '_country',
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

        # Map date type attributes to actual date types or None
        for attribute in ['begin_date', 'end_date', 'protocol1_date',
                          'protocol2_date', 'protocol3_date',
                          'protocol4_date', 'protocol5_date']:
            value = getattr(site, attribute)
            if value:
                try:
                    value = date(*map(int, value.split('/')))
                    setattr(site, attribute, value)
                except (IndexError, ValueError, TypeError):
                    setattr(site, attribute, None)
            else:
                setattr(site, attribute, None)

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

    @property
    def country(self):
        '''returns country or Unknown'''
        return self._country or 'Unknown'

    @property
    def region(self):
        '''returns region or Unknown'''
        return countryregion.get(
            self.country, CountryRegion('Unknown',
                                        self._region or 'Unknown')).region

    @property
    def decoded_country(self):
        '''returns the full country name from a 3 character code'''
        return countryregion.get(self.country,
                                 CountryRegion(self.country, 'Unknown')).country

    def update_location(self, region, country):
        '''Sets or updates region or country information'''
        self._region = region
        self._country = country

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

    def get_site(self, site_num):
        '''return the site data for site_num'''
        for site in self._sites:
            if site.number == site_num:
                return site
        raise IndexError(f'Request for non-existent site {site_num}')

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
