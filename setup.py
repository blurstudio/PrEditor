from setuptools import setup, find_packages
from codecs import open
import os
from os import path
import re
import subprocess
from setuptools.command.install import install

_dir = path.dirname(path.abspath(__file__))
import sys

sys.path.append(r'\\snake\user\public\liam\test_packages')
import blurutils.version

version = blurutils.version.Version(os.path.join(_dir, 'blurdev'))

# Get the long description from the README file
with open(path.join(_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='blur-blurdev',
    version=version.get_version_string(),
    description='blurdev',
    long_description=long_description,
    url='https://gitlab.blur.com/pipeline/blurdev.git',
    download_url='https://gitlab.blur.com/pipeline/blurdev/repository/archive.tar.gz?ref=master',
    license='Proprietary',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: Other/Proprietary License',
        'Private :: Do Not Upload',
    ],
    keywords='blurdev',
    packages=find_packages(exclude=['docs', 'installers', 'tests']),
    scripts=['post_install_blurdev.py',],
    include_package_data=True,
    author='Blur Studio',
    author_email='pipeline@blur.com',
)
