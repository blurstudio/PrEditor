#!/usr/bin/env python
from __future__ import absolute_import, print_function

import os
import sys

try:
    import configparser
except Exception:
    import ConfigParser as configparser  # noqa: N813

# define the default environment variables
OS_TYPE = ''
if os.name == 'posix':
    OS_TYPE = 'Linux'
elif os.name == 'nt':
    OS_TYPE = 'Windows'
elif os.name == 'osx':
    OS_TYPE = 'MacOS'

# The sections to add from settings.ini
# The order matters. Add from most specific to least specific.
# Example: Add Windows Offline, then Windows, then Default.
# Environment variables that exist in os.environ will not be added.
_SECTIONS_TO_ADD = []
if os.getenv('BDEV_OFFLINE') == '1':
    _SECTIONS_TO_ADD.append('{} Offline'.format(OS_TYPE))
_SECTIONS_TO_ADD += [OS_TYPE, 'Default']

_currentEnv = ''
defaults = {}


def environStr(value):
    if sys.version_info[0] > 2:
        # Python 3 requires a unicode value. aka str(), which these values already are
        return value
    # Python 2 requires str object, not unicode
    return value.encode('utf8')


def addConfigSection(config_parser, section):
    """
    Add a config section to os.environ for a section.

    Does not add options that already exist in os.environ.

    Args:
        config_parser (configparser.RawConfigParser): The parser to read from.
            Must already be read.
        section (str): The section name to add.
    """

    for option in config_parser.options(section):
        if option.upper() not in os.environ:
            value = config_parser.get(section, option)
            if value == 'None':
                value = ''
            # In python2.7 on windows you can't pass unicode values to
            # subprocess.Popen's env argument. This is the reason we are calling str()
            os.environ[environStr(option.upper())] = environStr(value)


# load the default environment from the settings INI
config = configparser.RawConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'resource', 'settings.ini'))
for section in _SECTIONS_TO_ADD:
    addConfigSection(config, section)

# store the blurdev path in the environment
os.environ['BDEV_PATH'] = environStr(os.path.dirname(__file__))
