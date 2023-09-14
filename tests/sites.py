#!/usr/bin/env python
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
'''Field level tests'''

import unittest
from dftoolkit.sites import Sites

centersdb = '''0|Error Monitor|Error Monitor||mailto:martin@teckelworks.com|country:;beginDate:;endDate:;enroll:;protocol1:;protocol1Date:;protocol2:;protocol2Date:;protocol3:;protocol3Date:;protocol4:;protocol4Date:;protocol5:;protocol5Date:;testSite:0|||||ERROR MONITOR
1|Dr. Abraham Lincoln|Hamilton General Hospital|123 Main Street West|mailto:martin@teckelworks.com|country:CAN;beginDate:2021/01/01;endDate:;enroll:;protocol1:;protocol1Date:;protocol2:;protocol2Date:;protocol3:;protocol3Date:;protocol4:;protocol4Date:;protocol5:;protocol5Date:;testSite:0|||||1001 1999
2|Dr. Susan Childs|Sick Kids Hospital|234 King Street|mailto:martin@teckelworks.com|country:USA;beginDate:;endDate:;enroll:;protocol1:;protocol1Date:;protocol2:;protocol2Date:;protocol3:;protocol3Date:;protocol4:;protocol4Date:;protocol5:;protocol5Date:;testSite:0|||||2001 2999
3|Dr. Nick Test|General Hospital|567 Queen Street|mailto:martin@teckelworks.com||||||3001 3999
'''

class SiteTests(unittest.TestCase):
    def setUp(self):
        self.sites = Sites()
        self.sites.load(centersdb)
        self.sites.merge_countries('Germany|Europe|2')

    def test_countryregion(self):
        self.assertEqual(self.sites.get_site(1).country, 'CAN')
        self.assertEqual(self.sites.get_site(1).decoded_country, 'Canada')
        self.assertEqual(self.sites.get_site(1).region, 'North America')

        self.assertEqual(self.sites.get_site(2).country, 'Germany')
        self.assertEqual(self.sites.get_site(2).decoded_country, 'Germany')
        self.assertEqual(self.sites.get_site(2).region, 'Europe')

        self.assertEqual(self.sites.get_site(3).country, 'Unknown')
        self.assertEqual(self.sites.get_site(3).decoded_country, 'Unknown')
        self.assertEqual(self.sites.get_site(3).region, 'Unknown')

    def test_lookups(self):
        self.assertEqual(self.sites.pid_to_site_number(1500), 1)
        self.assertEqual(self.sites.pid_to_site_number(9999), 0)

if __name__ == '__main__':
    unittest.main()
