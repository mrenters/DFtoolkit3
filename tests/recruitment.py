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
'''Recruitment Report tests'''

import unittest
from datetime import date
from dftoolkit.recruitment import RecruitmentData, nmonths, month_columns

class RecruitmentDataTests(unittest.TestCase):
    def setUp(self):
        data = RecruitmentData()
        data.activate(date(2023, 1, 1))
        for dat in [
                date(2023, 1, 2),
                date(2023, 1, 2),
                date(2023, 1, 3),
                date(2023, 1, 5),
                date(2023, 1, 5),
                date(2023, 1, 10),
                date(2023, 1, 10),
                date(2023, 1, 10),
                date(2023, 1, 11)
        ]:
            data.recruit(dat)
        self.data = data
        self.data1 = RecruitmentData()

    def test_dates(self):
        self.assertEqual(self.data.activation, date(2023, 1, 1))
        self.assertEqual(self.data.firstpt, date(2023, 1, 2))
        self.assertEqual(self.data.lastpt, date(2023, 1, 11))
        self.assertEqual(self.data.deactivation, None)

    def test_total_pts(self):
        self.assertEqual(self.data.total_pts, 9)
        self.assertEqual(self.data1.total_pts, 0)

    def test_days_active(self):
        self.assertEqual(self.data.days_active(date(2023, 2, 1)), 31)
        self.assertEqual(self.data1.days_active(date(2023, 2, 1)), 0)

    def test_count_between(self):
        self.assertEqual(
            self.data.count_between(date(2023, 1, 1), date(2023, 1, 5)), 5)
        self.assertEqual(
            self.data1.count_between(date(2023, 1, 1), date(2023, 1, 5)), 0)

    def test_count_yymm(self):
        self.assertEqual(
            self.data.count_yymm(date(2023, 1, 1)), 9)
        self.assertEqual(
            self.data.count_yymm(date(2023, 2, 1)), 0)
        self.assertEqual(
            self.data1.count_between(date(2023, 1, 1), date(2023, 1, 5)), 0)

    def test_best(self):
        self.assertEqual(
            self.data.best(date(2023, 5, 15), 7),
            (6, date(2023, 1, 5), date(2023, 1, 11)))
        self.assertEqual(
            self.data.best(date(2023, 5, 15), 1),
            (3, date(2023, 1, 10), date(2023, 1, 10)))
        self.assertEqual(
            self.data.best(date(2023, 5, 15), 2),
            (4, date(2023, 1, 10), date(2023, 1, 11)))
        self.assertEqual(
            self.data.best(date(2023, 5, 15), 30),
            (9, date(2023, 1, 2), date(2023, 1, 11)))
        self.assertEqual(
            self.data1.best(date(2023, 5, 15), 30),
            (0, None, None))

class RecruitmentFunctions(unittest.TestCase):
    def test_column_months(self):
        self.assertEqual(month_columns(date(2022, 8, 20), date(2023, 5, 15)),
                         ['May-23', 'Apr-23', 'Mar-23', 'Feb-23', 'Jan-23',
                          'Dec-22', 'Nov-22', 'Oct-22', 'Sep-22', 'Aug-22'])

    def test_nmonths(self):
        self.assertEqual(nmonths(date(2022, 8, 20), date(2023, 5, 15)), 10)
        self.assertEqual(nmonths(date(2023, 5, 1), date(2023, 5, 15)), 1)
        self.assertEqual(nmonths(date(2023, 5, 15), date(2023, 5, 1)), 1)

if __name__ == '__main__':
    unittest.main()
