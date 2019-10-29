from setuptools import setup, find_packages
from codecs import open
import os
import re
import subprocess
import sys
from pillar.version import Version

_dir = os.path.dirname(os.path.abspath(__file__))
version = Version(os.path.join(_dir, 'blurdev'), 'blur-blurdev')

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
        "future==0.17.1",
        "configparser==3.7.4",
        "certifi==2019.6.16",
        "Jinja2==2.10.1",
        "MarkupSafe==1.1.1",
        "Pygments==2.4.2",
        "sentry-sdk==0.10.2",
        "urllib3==1.25.3",
        "blur-pillar>=0.13.0",
        "blur-recoil>=0.6.0",
        "blur-cute>=0.14.0",
    ],
    include_package_data=True,
    author='Blur Studio',
    author_email='pipeline@blur.com',
    entry_points={
        'gui_scripts': [
            # Create executable items that work even if using virtualenv, or editable installs
            'treegrunt = blurdev.runtimes.treegrunt:main',
            'treegrunt-tool = blurdev.runtimes.run_tool:main',
            'blurdev-protocol = blurdev.runtimes.protocol:main',
            'blurdev-logger = blurdev.runtimes.logger:main',
            'blurIDE = blurdev.runtimes.ide_editor:main',
        ],
        'blurdev.toolbars': [
            'Favorites = blurdev.gui.toolbars.toolstoolbar:FavoritesToolbar',
            'User = blurdev.gui.toolbars.toolstoolbar:UserToolbar',
        ],
    },
)
