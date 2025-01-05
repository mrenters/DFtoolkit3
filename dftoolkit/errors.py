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
'''DFtoolkit logging functions'''

import logging
import sys
import traceback

def setup_logging(verbose=0, filename=None, mode='a'):
    '''Sets up logging'''
    level = logging.WARNING
    if verbose >= 2:
        level = logging.DEBUG
    if verbose == 1:
        level = logging.INFO

    # Remove old handler
    log = logging.getLogger()
    for handler in log.handlers:
        if isinstance(handler, logging.StreamHandler):
            log.removeHandler(handler)

    if filename is None:
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.FileHandler(filename, mode, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    log.setLevel(level)
    log.addHandler(handler)

def print_exception(verbose=0, msg=None):
    '''Print a python exception to stderr'''
    err_type, err_value, err_traceback = sys.exc_info()
    msgs = traceback.format_exception_only(err_type, err_value)
    if msg:
        print(msg)
    if verbose:
        msgs = traceback.format_exception(err_type, err_value,
                                          err_traceback)
    for err_string in msgs:
        print(err_string, end='', file=sys.stderr)
