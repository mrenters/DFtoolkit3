import os
import sys
from warnings import warn
from setuptools import setup

if sys.version_info < (3, 6, 0):
    warn("The minimum Python version supported by dftoolkit is 3.6.0")
    exit()

from dftoolkit import __version__

def pkg_data(name):
    items = []
    for dir, _, files in os.walk(name):
        for file in files:
            items.append(os.path.join(dir, file))
    return (name, items)

setup(
    name='dftoolkit',
    version=__version__,
    description='DFdiscover/DataFax Library for Python',
    url='http://www.teckelworks.com',
    author='Martin Renters',
    author_email='martin@teckelworks.com',
    license='GPLv3',
    packages=['dftoolkit'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    scripts = [
        'scripts/annotateCRF',
        'scripts/closeoutPDF',
        'scripts/datachanges',
        'scripts/make_closeout_db',
        'scripts/missingvalues',
        'scripts/updateinfo',
        'scripts/EClist',
        'scripts/QC2Excel',
        'scripts/schema2excel',
    ],
    package_data={'dftoolkit': ['fonts/*', 'vba/*']},
    #data_files = [ pkg_data('dftoolkit/fonts'), pkg_data('dftoolkit/vba') ]
)
