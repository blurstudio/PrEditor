#!/usr/bin/env python
import os
import platform

# define the default environment variables
OS_TYPE = platform.uname()[2]

_inited = False
defaults = {}

# load the default settings from the settings INI
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read(os.path.dirname(__file__) + '/resource/settings.ini')
for option in config.options(OS_TYPE):
    if not option in os.environ:
        value = config.get(OS_TYPE, option)
        if value == 'None':
            value = ''
        os.environ[option.upper()] = value

# define environment loading/restoring methods
def init():
    global _inited
    if _inited:
        return

    _inited = True
    from optparse import OptionParser

    # initialize command line options
    parser = OptionParser()
    parser.add_option(
        '-d', '--debug', dest='debug', help='set the debug level for the system'
    )
    parser.add_option(
        '-p', '--preference_root', dest='preference_root', help='set the user pref file'
    )
    parser.add_option(
        '-t', '--trax_root', dest='trax_root', help='set the import location for trax'
    )
    parser.add_option(
        '-s',
        '--settings_env',
        dest='settings_env',
        help='set the default settings environment',
    )
    parser.add_option(
        '-z', '--zip_exec', dest='zip_exec', help='set the zip executable location'
    )

    import sys

    (options, args) = parser.parse_args(sys.argv)
    if options.preference_root:
        os.environ['BDEV_PREFERENCE_ROOT'] = options.preference_root
    if options.trax_root:
        os.environ['BDEV_TRAX_ROOT'] = options.trax_root
    if options.settings_env:
        os.environ['BDEV_SETTINGS_ENV'] = options.settings_env
    if options.zip_exec:
        os.environ['BDEV_ZIP_EXEC'] = options.zip_exc
    if options.debug:
        os.environ['BDEV_DEBUG_LEVEL'] = options.debug

    # initialize the default variables
    setup(os.environ['BDEV_SETTINGS_ENV'])
    registerPath(os.environ['BDEV_TRAX_ROOT'])


def normalizePath(path):
    import os

    path = os.path.abspath(unicode(path))

    # use lowercase for windows since we don't want duplicates - in other
    # operating systems, the path is case-sensitive
    if OS_TYPE == 'Windows':
        path = path.lower()

    return path


def record(name, inherits=''):
    """
        Records the current environment settings to the inputed environment
        name.

        :param name:
            <str> name of the environment to record the current settings to
        :param env_vars:
            <bool> flag whether or not the os.environ variables should be saved
        :param sys_paths:
            <bool> flag whether or not the sys.path data should be saved
    """
    import blurdev
    from blurdev.XML import XMLDocument

    doc = XMLDocument()
    root = doc.addNode('settings')
    root.setAttribute('version', 1.0)
    if inherits:
        root.setAttribute('inherits', inherits)

    # record environment variables
    import os

    variables = root.addNode('variables')

    for key, value in os.environ.items():
        xvariable = variables.addNode('variable')
        xvariable.setAttribute('key', key)
        xvariable.setAttribute('value', value)

    # record the sys paths
    import sys

    paths = root.addNode('paths')
    for path in sys.path:
        xpath = paths.addNode('path')
        xpath.setAttribute('value', path)

    doc.save(blurdev.resourcePath('settings_env/%s.xml' % name))


def registerPath(path):
    path = normalizePath(path)
    import os.path, sys

    if path and path != '.' and not path in sys.path:
        import sys

        sys.path.insert(0, path)
        return True
    return False


def setup(name):
    import blurdev
    from blurdev.XML import XMLDocument

    doc = XMLDocument()
    settingsfile = blurdev.resourcePath('settings_env/%s.xml' % name)
    print 'loading settingsfile', settingsfile

    # load the settings file
    if not doc.load(settingsfile):
        return False

    import os, sys

    # use inheritance
    inherits = doc.root().attribute('inherits')
    if inherits:
        setup(inherits)

    # load the environment variables
    vars = doc.root().findChild('variables')
    if vars:
        for var in vars.children():
            os.environ[var.attribute('key')] = var.attribute('value')

    # load the system paths
    paths = doc.root().findChild('paths')
    if paths:
        for path in paths.children():
            loc = path.attribute('value')
            if loc in sys.path:
                continue

            sys.path.insert(0, loc)

    return True
