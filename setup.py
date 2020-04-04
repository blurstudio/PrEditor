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
        # Please keep list alphabetical
        'blur-cute>=0.16.0',
        'blur-pillar>=0.16.0',
        'certifi==2019.9.11',
        'configparser>=4.0.2',
        'Deprecated>=1.2.7',
        'future>=0.18.2',
        'Jinja2>=2.10.3',
        'MarkupSafe>=1.1.1',
        'Pygments>=2.4.2',
        'python-redmine>=2.1.1',
        'QScintilla>=2.11.4',
        'sentry-sdk>=0.13.2',
        'urllib3>=1.25.7',
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
        'console_scripts': [
            # Launch the blurdev-logger in a console mode so we can debug why the gui_scripts
            # are not running if there is a pip dependency version issue.
            'blurdev-console = blurdev.runtimes.logger:main',
        ],
        'blurdev.toolbars': [
            'Favorites = blurdev.gui.toolbars.toolstoolbar:FavoritesToolbar',
            'User = blurdev.gui.toolbars.toolstoolbar:UserToolbar',
        ],
        'blurdev.tools.paths': ['TREEGRUNT_ROOT = blurdev.tools:toolPaths',],
        'blurdev.protocol_handlers': [
            'Treegrunt = blurdev.protocols.treegrunt_handler:TreegruntHandler',
            'Blurdev = blurdev.protocols.blurdev_handler:BlurdevHandler',
            'WriteStdOutput = blurdev.protocols.write_std_output_handler:WriteStdOutputHandler',
        ],
    },
)
