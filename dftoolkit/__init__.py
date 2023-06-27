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
'''DFtoolkit module'''

__version__ = '3.1.5'
__VERSION__ = __version__

import sys
from .api import APIFiles
from .study import Study
from .errors import print_exception

def study_from_files(studydir, verbose=0):
    '''load a study from files and terminate on error'''
    try:
        api = APIFiles(studydir)
    except Exception:
        print_exception(verbose,
                        'Unable to locate study or misconfigured study')
        sys.exit(2)

    try:
        study = Study(api)
        study.load()
    except Exception:
        print_exception(verbose, 'Unable to load study')
        sys.exit(2)

    return study
