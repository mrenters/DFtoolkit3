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

'''This module implements the API Access functions'''

import os
import subprocess

from PIL import Image

from .rangelist import SubjectList
from .schedule import ScheduleEntry

class APIBase:
    # pylint: disable=no-self-use
    '''API Base base'''
    def __init__(self):
        self.studynum = None

    def attachment_context(self, raster):
        # pylint: disable=unused-argument
        '''Returns a the creation time of a raster file'''
        return None

    def background(self, plate, visit_num=None, preferred_types=None):
        # pylint: disable=unused-argument
        '''Returns a background image'''
        return None

    def config(self):
        '''Gets study server configuration file'''
        raise IOError

    def countries(self):
        '''Gets DFcountries file (DFtoolkit extension)'''
        raise IOError

    def domain_map(self):
        '''Gets DFdomains file (DFtoolkit extension)'''
        raise IOError

    def missing_map(self):
        '''Returns DFmissing_map content'''
        raise IOError

    def qc_types(self):
        '''Returns DFproblem_map content'''
        raise IOError

    def page_map(self):
        '''Returns DFpage_map content'''
        raise IOError

    def priority_file(self, name):
        # pylint: disable=unused-argument
        '''Gets a priorityfile (DFtoolkit extension)'''
        raise IOError

    def setup(self):
        '''Gets DFsetup file'''
        raise IOError

    def sites(self):
        '''Returns DFcenters content'''
        raise IOError

    def visit_map(self):
        '''Returns DFvisit_map content'''
        raise IOError

    def data(self, plate, subjects=SubjectList(default_all=True),
             missing_records=False, secondary_records=False):
        '''Returns patient data records for plate'''
        raise IOError

    def queries(self, subjects=SubjectList(default_all=True)):
        '''Returns query records'''
        raise IOError

    def reasons(self, subjects=SubjectList(default_all=True)):
        '''Returns reason records'''
        raise IOError

    def schedules(self, subjects=SubjectList(default_all=True)):
        '''Returns schedule records'''
        raise IOError

    def attachment(self, attachment):
        '''Returns an attachment'''
        raise IOError

    def audit(self, subjects=SubjectList(default_all=True)):
        '''Returns audit records'''
        raise IOError

class APIFiles(APIBase):
    '''API as File I/O'''
    def __init__(self, studydir):
        super().__init__()
        self.studydir = studydir
        self.pagedir = None
        self.background_cache = {}
        self.shadow_pages = None
        with open(os.path.join(studydir, 'lib',
                               'DFserver.cf'), 'r') as config:

            studydir = None

            for line in config.read().splitlines():
                config = line.split('=')
                if len(config) < 2:
                    continue
                if config[0] == 'STUDY_DIR':
                    studydir = config[1]
                elif config[0] == 'PAGE_DIR':
                    self.pagedir = config[1]
                elif config[0] == 'STUDY_NUMBER':
                    self.studynum = int(config[1])

            if self.pagedir and studydir:
                self.pagedir = self.pagedir.replace('$(STUDY_DIR)', studydir)

        if not self.pagedir:
            self.pagedir = os.path.join(studydir, 'pages')

    def attachment_context(self, raster):
        '''Returns a the creation time of a raster file'''
        mtime = None
        path = os.path.join(self.studydir, 'pages', raster)
        if os.path.isfile(path) and os.access(path, os.R_OK):
            mtime = os.path.getmtime(path)
        return mtime

    def background(self, plate, visit_num=None, preferred_types=None):
        '''Returns a background image for plate'''
        if plate.ecrf:
            return None
        bkgds = []

        # Build a list of possible background filenames
        if preferred_types:
            if isinstance(preferred_types, str):
                preferred_types = preferred_types.split(',')
            for bkgd in preferred_types:
                bkgd = "".join(filter(str.isalnum, bkgd))
                if not bkgd:
                    continue
                if visit_num is not None:
                    bkgds.append('DFbkgd%03d_%d_%s.png' % (plate.number,
                                                           visit_num, bkgd))
                bkgds.append('DFbkgd%03d_all_%s.png' % (plate.number, bkgd))

        if visit_num is not None:
            bkgds.append('DFbkgd%03d_%d.png' % (plate.number, visit_num))
        bkgds.append('DFbkgd%03d.png' % plate.number)
        bkgds.append('plt%03d.png' % plate.number)
        bkgds.append('plt%03d' % plate.number)

        # Now cycle through them and see whether we can find one.
        # Cache results, both positive and negative
        img = None
        for bkgd in bkgds:
            img = self.background_cache.get(bkgd)
            if img == 'NOT FOUND':
                continue
            if img is not None:
                return img
            path = os.path.join(self.studydir, 'bkgd', bkgd)
            try:
                img = Image.open(path)
                self.background_cache[bkgd] = img
                break
            except IOError:
                self.background_cache[bkgd] = 'NOT FOUND'

        return img

    def config(self):
        '''Gets study server configuration file'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFserver.cf'), 'r') as data:
            return data.read()

    def countries(self):
        '''Gets DFcountries file (DFtoolkit extension)'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFcountries'), 'r') as data:
            return data.read()

    def domain_map(self):
        '''Gets DFdomains file (DFtoolkit extension)'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFdomain_map'), 'r') as data:
            return data.read()

    def missing_map(self):
        '''Returns DFmissing_map content'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFmissing_map'), 'r') as data:
            return data.read()

    def qc_types(self):
        '''Returns DFproblem_map content'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFqcproblem_map'), 'r') as data:
            return data.read()

    def page_map(self):
        '''Returns DFpage_map content'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFpage_map'), 'r') as data:
            return data.read()

    def priority_file(self, name):
        '''Gets a priorityfile (DFtoolkit extension)'''
        with open(name, 'r') as data:
            return data.read()

    def setup(self):
        '''Gets DFsetup file'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFsetup'), 'r') as data:
            return data.read()

    def sites(self):
        '''Returns DFcenters content'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFcenters'), 'r') as data:
            return data.read()

    def visit_map(self):
        '''Returns DFvisit_map content'''
        with open(os.path.join(self.studydir,
                               'lib', 'DFvisit_map'), 'r') as data:
            return data.read()

    def data(self, plate, subjects=SubjectList(default_all=True),
             missing_records=False, secondary_records=False):
        '''Returns patient data records for plate'''
        rectypes = 'primary'
        if missing_records:
            rectypes += ',lost'
        if secondary_records:
            rectypes += ',secondary'

        args = ['/opt/dfdiscover/bin/DFexport.rpc',
                '-s', rectypes]

        if not subjects.empty:
            args.append('-I')
            args.append(str(subjects))

        # Add study, plate, -
        args.append(str(self.studynum))
        args.append(str(plate.number))
        args.append('-')
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        for data in proc.stdout:
            try:
                record = data.decode('utf-8')
            except UnicodeDecodeError:
                record = data.decode('latin-1')
            yield record.rstrip('\n')

        proc.wait()

    def queries(self, subjects=SubjectList(default_all=True)):
        '''Returns query records'''
        args = ['/opt/dfdiscover/bin/DFexport.rpc',
                '-s', 'all']

        if not subjects.empty:
            args.append('-I')
            args.append(str(subjects))

        # Add study, plate, -
        args.append(str(self.studynum))
        args.append('511')
        args.append('-')
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        for data in proc.stdout:
            try:
                record = data.decode('utf-8')
            except UnicodeDecodeError:
                record = data.decode('latin-1')
            yield record.rstrip('\n')

        proc.wait()

    def reasons(self, subjects=SubjectList(default_all=True)):
        '''Returns reason records'''
        args = ['/opt/dfdiscover/bin/DFexport.rpc',
                '-s', 'all']

        if not subjects.empty:
            args.append('-I')
            args.append(str(subjects))

        # Add study, plate, -
        args.append(str(self.studynum))
        args.append('510')
        args.append('-')
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        for data in proc.stdout:
            try:
                record = data.decode('utf-8')
            except UnicodeDecodeError:
                record = data.decode('latin-1')
            yield record.rstrip('\n')

        proc.wait()

    def schedules(self, subjects=SubjectList(default_all=True)):
        '''Returns schedule records'''
        with open(os.path.join(self.studydir, 'work',
                               'DFX_schedule'), 'r') as data:
            for line in data:
                entry = ScheduleEntry.from_xschedule(line)
                if entry.pid not in subjects:
                    continue
                yield entry

    def attachment(self, attachment):
        '''Return an attachment, may cause exception'''
        if self.shadow_pages is not None:
            pagedirs = [self.shadow_pages]
        else:
            pagedirs = []
        pagedirs.extend([os.path.join(self.studydir, 'pages'), self.pagedir])

        for pagedir in pagedirs:
            try:
                with open(os.path.join(pagedir, attachment), 'rb') as data:
                    return data.read()
            except Exception:
                pass
        raise IOError

    def audit(self, subjects=SubjectList(default_all=True)):
        '''Returns audit records'''
        args = ['/opt/dfdiscover/bin/DFaudittrace', '-s', str(self.studynum),
                '-d', '19900101-today', '-N', '-q', '-r']

        if not subjects.empty:
            args.append('-I')
            args.append(str(subjects))

        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        for data in proc.stdout:
            try:
                record = data.decode('utf-8')
            except UnicodeDecodeError:
                record = data.decode('latin-1')
            yield record.rstrip('\n')

        proc.wait()
