from setuptools import setup, find_packages
from codecs import open
import os
import re
import subprocess
from setuptools.command.install import install
import sys

# Temporary until a blur-utils package is made
import platform

if 'Linux' == platform.system():
    libPath = r'/mnt/source/code/python/lib/'
else:
    libPath = r'\\source\production\code\python\lib'
if os.path.exists(os.path.join(libPath, 'blurutils')):
    sys.path.append(libPath)
else:
    # BlurOffline fix
    sys.path.append(r'C:\blur\dev\offline\code\python\lib')
try:
    import blurutils.version
except ImportError:
    raise

_dir = os.path.dirname(os.path.abspath(__file__))
version = blurutils.version.Version(os.path.join(_dir, 'blurdev'))

# Get the long description from the README file
with open(os.path.join(_dir, 'README.rst'), encoding='utf-8') as f:
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
    scripts=['post_install-blur-blurdev.py',],
    install_requires=[
        "future",
        "configparser",
        "certifi",
        "Jinja2",
        "MarkupSafe",
        "pygments",
        "sentry_sdk",
        "urllib3",
        'blur-pillar>=0.5.0',
        'blur-recoil>=0.6.0',
    ],
    include_package_data=True,
    author='Blur Studio',
    author_email='pipeline@blur.com',
    entry_points={
        'gui_scripts': [
            # Create executable items that work even if using virtualenv, or editable installs
            'treegrunt = blurdev.runtimes.treegrunt:main',
            'blurdev-protocol = blurdev.runtimes.protocol:main',
            'blurdev-logger = blurdev.runtimes.logger:main',
            'blurIDE = blurdev.runtimes.ide_editor:main',
        ],
    },
)
