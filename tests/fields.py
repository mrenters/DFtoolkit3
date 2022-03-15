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
'''Generate a PDF file with study annotation information'''

import unittest
from dftoolkit import Study, APIFiles

class FieldTests(unittest.TestCase):
    def setUp(self):
        api = APIFiles('/opt/studies/teckelworks')
        self.study = Study(api)
        if not self.study.load():
            raise AssertianError('unable to load study')

    def test_boxgroups(self):
        plate = self.study.plate(1)
        self.assertEqual(plate.field(6).box_groups, [3])
        self.assertEqual(plate.field(7).box_groups, [2, 3])
        self.assertEqual(plate.field(8).box_groups, [4, 2, 2])

if __name__ == '__main__':
    unittest.main()
