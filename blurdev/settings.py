#!/usr/bin/env python

import copy
import os
import sys

try:
    import configparser
except:
    import ConfigParser as configparser

# define the default environment variables
OS_TYPE = ''
if os.name == 'posix':
    OS_TYPE = 'Linux'
elif os.name == 'nt':
    OS_TYPE = 'Windows'
elif os.name == 'osx':
    OS_TYPE = 'MacOS'

_currentEnv = ''
_inited = False
defaults = {}


def environStr(value):
    if sys.version_info[0] > 2:
        # Python 3 requires a unicode value. aka str(), which these values already are
        return value
    # Python 2 requires str object, not unicode
    return value.encode('utf8')


# load the default environment from the settings INI
config = configparser.RawConfigParser()
config.read(os.path.dirname(__file__) + '/resource/settings.ini')
for option in config.options(OS_TYPE):
    if option not in os.environ:
        value = config.get(OS_TYPE, option)
        if value == 'None':
            value = ''
        # In python2.7 on windows you can't pass unicode values to subprocess.Popen's env argument.
        # This is the reason we are calling str()
        os.environ[environStr(option.upper())] = environStr(value)

# store the blurdev path in the environment
os.environ['BDEV_PATH'] = environStr(os.path.dirname(__file__))

# setup defaults
os.environ.setdefault('BDEV_PARAM_BLURQT', '1')

# store the environment variables as the startup variables
startup_environ = copy.deepcopy(os.environ)


def current():
    return _currentEnv


# define environment loading/restoring methods
def init():
    global _inited
    if _inited:
        return
    _inited = True

    # set this variable in any runtime to load arguments from command line
    if hasattr(sys, 'argv') and os.environ.get('BDEV_EXEC') == '1':
        from optparse import OptionParser

        parser = OptionParser()
        parser.disable_interspersed_args()

        # add additional options from the environment
        for addtl in os.environ.get('BDEV_EXEC_OPTIONS', '').split(':'):
            if addtl:
                option, help = addtl.split('=')
                parser.add_option('', '--{}'.format(option), dest=option, help=help)

        # initialize common command line options
        parser.add_option(
            '-d', '--debug', dest='debug', help='set the debug level for the system'
        )
        parser.add_option(
            '-e',
            '--environment',
            dest='environment',
            help='set the trax startup environment',
        )
        parser.add_option(
            '-p',
            '--preference_root',
            dest='preference_root',
            help='set the user pref file',
        )
        parser.add_option(
            '-t',
            '--trax_root',
            dest='trax_root',
            help='set the import location for trax',
        )
        parser.add_option(
            '-z', '--zip_exec', dest='zip_exec', help='set the zip executable location'
        )
        parser.add_option(
            '-f', '--filename', dest='filename', help='set the filename to load in ide'
        )

        (options, args) = parser.parse_args(sys.argv)
        if options.preference_root:
            registerVariable('BDEV_PATH_PREFS', options.preference_root)
        if options.trax_root:
            registerVariable('BDEV_PATH_TRAX', options.trax_root)
        if options.zip_exec:
            registerVariable('BDEV_APP_ZIP', options.zip_exc)
        if options.debug:
            registerVariable('BDEV_DEBUG_LEVEL', options.debug)
        if options.environment:
            registerVariable('TRAX_ENVIRONMENT', options.environment)
        if options.filename:
            registerVariable('BDEV_FILE_START', options.filename)

        # set options
        for addtl in os.environ.get('BDEV_EXEC_OPTIONS', '').split(':'):
            if addtl:
                option, help = addtl.split('=')
                if option in options.__dict__ and options.__dict__[option] != None:
                    registerVariable(
                        'BDEV_OPT_%s' % option.upper(), options.__dict__[option]
                    )

    # register default paths
    for key in sorted(os.environ.keys(), reverse=True):
        if key.startswith('BDEV_INCLUDE_'):
            path = os.environ[key]
            if not path:
                # If set to a empty value, don't register the path
                continue
            if key == 'BDEV_INCLUDE_TRAX':
                # check if trax is installed, if not then register the offline trax classes
                if not os.path.isfile(r'%s\trax\__init__.py' % path):
                    registerPath(r'%s\traxoffline' % os.path.split(__file__)[0])
                    continue
            registerPath(path)


def normalizePath(path):
    path = os.path.abspath(path)
    # use lowercase for windows since we don't want duplicates - in other
    # operating systems, the path is case-sensitive
    if OS_TYPE == 'Windows':
        path = path.lower()
    return path


def registerVariable(key, value):
    """ Add the key value pair to both the current os.environ, and the startup_environ
    """
    value = environStr(value)
    os.environ[key] = value
    startup_environ[key] = value


def registerPath(path):
    path = normalizePath(path)
    if path and path != '.' and not path in sys.path:
        sys.path.insert(0, path)
        return True
    return False
