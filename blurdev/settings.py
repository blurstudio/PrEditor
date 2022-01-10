#!/usr/bin/env python
from __future__ import print_function

from __future__ import absolute_import
import copy
import os
import sys
import site
import re
import glob

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
_inited = False
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
config.read(os.path.dirname(__file__) + '/resource/settings.ini')
for section in _SECTIONS_TO_ADD:
    addConfigSection(config, section)

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

    # register default paths
    for key in sorted(list(os.environ.keys()), reverse=True):
        if key.startswith('BDEV_INCLUDE_'):
            path = os.environ[key]
            if not path:
                # If set to a empty value, don't register the path
                continue
            if key == 'BDEV_INCLUDE_TRAX':
                # check if trax is installed, if not then register the offline trax
                # classes
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
    """Add the key value pair to both the current os.environ, and the startup_environ"""
    value = environStr(value)
    os.environ[key] = value
    startup_environ[key] = value


def registerPath(path):
    path = os.path.abspath(path)
    # We won't register a path that does not exist to not clutter sys.path.
    if path != '.' and path not in sys.path and os.path.exists(path):
        # Add the path to the top of sys.path so code in this folder is run before
        # other code with the same name.
        sys.path.insert(0, path)
        # Process any .pth files in this directory, Using our version of addsitedir
        # so windows and linux paths in the .pth work. This makes it so any .egg-link
        # installed packages get appended to sys.path and loaded. Egg-link installs
        # are handled by the easy-install.pth file
        addsitedir(path)
        return True
    return False


def addpackage(sitedir, name, known_paths):
    """Process a .pth file within the site-packages directory:
    For each line in the file, either combine it with sitedir to a path
    and add that to known_paths, or execute it if it starts with 'import '.

    NOTE: this function replicates the function in python's site module
    It adds the ability to translate linux or windows paths to the current
    platform in pth files. It can be used as a direct replacement to calling
    the site function. See the `toSystemPath` function.
    """
    if known_paths is None:
        known_paths = site._init_pathinfo()
        reset = True
    else:
        reset = False
    fullname = os.path.join(sitedir, name)
    try:
        f = open(fullname, "r")
    except OSError:
        return
    with f:
        for n, line in enumerate(f):
            if line.startswith("#"):
                continue
            try:
                if line.startswith(("import ", "import\t")):
                    exec(line)
                    continue
                line = toSystemPath(line.rstrip())
                dir, dircase = site.makepath(sitedir, line)
                if dircase not in known_paths and os.path.exists(dir):
                    sys.path.append(dir)
                    known_paths.add(dircase)
            except Exception:
                print(
                    "Error processing line {:d} of {}:\n".format(n + 1, fullname),
                    file=sys.stderr,
                )
                import traceback

                for record in traceback.format_exception(*sys.exc_info()):
                    for line in record.splitlines():
                        print('  ' + line, file=sys.stderr)
                print("\nRemainder of file ignored", file=sys.stderr)
                break
    if reset:
        known_paths = None
    return known_paths


def addsitedir(sitedir, known_paths=None):
    """Add 'sitedir' argument to sys.path if missing and handle .pth files in
    'sitedir'

    NOTE: this function replicates the function in python's site module
    It adds the ability to translate linux or windows paths to the current
    platform in pth files. It can be used as a direct replacement to calling
    the site function. See the `toSystemPath` function.
    """
    if known_paths is None:
        known_paths = site._init_pathinfo()
        reset = True
    else:
        reset = False
    sitedir, sitedircase = site.makepath(sitedir)
    if sitedircase not in known_paths:
        sys.path.append(sitedir)  # Add path component
        known_paths.add(sitedircase)
    try:
        names = os.listdir(sitedir)
    except OSError:
        return
    names = [name for name in names if name.endswith(".pth")]
    for name in sorted(names):
        addpackage(sitedir, name, known_paths)
    if reset:
        known_paths = None
    return known_paths


def pathReplacements():
    """A list of replacements to apply to file paths.

    Returns a list of ('windows', 'linux') tuples. `toSystemPath` uses this list
    to translate file paths to the current system.

    This list is controlled by the BDEV_PATH_REPLACEMENTS environment variable.
    Each windows/linux mapping is defined as windows,linux. These are separated
    by a ;. This ensures that we can define drive letter replacements that work
    on linux.

    Example:
        `BDEV_PATH_REPLACEMENTS=\\aserver\ashare,/mnt/ashare;G:,/blur/g`

    Returns:
        list: The list of path replacements.
    """
    ret = os.environ.get('BDEV_PATH_REPLACEMENTS', '').split(';')
    return [mapping.split(',') for mapping in ret]


def pthPaths(dirname):
    """Returns the absolute paths defined in any .pth file in dirname.

    This does not process any imports in the .pth file. The file paths are
    converted to the current operating system by `toSystemPath`. These paths
    have os.path.normpath, abspath and normcase called on them.

    Args:
        dirname (str): All .pth files in this directory are searched for paths.

    Returns:
        paths (list): A list of paths that will be added to sys.path when `addsitedir
            ` is called.
        skipped (list): A list of .pth files that could not be read.
        pthFiles (list): All .pth file paths that were processed.
    """
    paths = []
    skipped = []
    pthFiles = glob.glob(os.path.join(dirname, '*.pth'))
    for filename in pthFiles:
        try:
            with open(filename, 'r') as f:
                for line in f:
                    if line.startswith(("import ", "import\t", "#")):
                        # For this code, we don't actually want to process imports
                        # and always want to ignore comment lines
                        continue
                    # Adjust path for the current os and call os.path.normpath
                    line = toSystemPath(line.rstrip())
                    # dircase has os.path.abspath and os.path.normcase called on it
                    _, dircase = site.makepath(dirname, line)
                    paths.append(dircase)
        except IOError:
            # We can't process this item, likely due to permissions.
            skipped.append(filename)
    return paths, skipped, pthFiles


def _path_escape(pattern):
    """Changes the pattern to match forward and backslash path separators.

    Replaces backslashes with `[\\\\/]` so we can match windows and linux paths.
    It then applies the same `re.escape` logic to any other characters as python 2.
    """
    s = list(pattern)
    alphanum = frozenset(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )
    for i, c in enumerate(pattern):
        if c in {'\\', '/'}:
            s[i] = '[\\\\/]'
        elif c not in alphanum:
            if c == "\000":
                s[i] = "\\000"
            else:
                s[i] = "\\" + c
    return pattern[:0].join(s)


def toSystemPath(path, os_type=OS_TYPE):
    """Ensure the file path is correct for the current os.

    Args:
        path (str): The file path to convert to the current operating system.
        os_type (str, optional): Override the os the path is generated for. Defaults
            to `blurdev.settings.OS_TYPE`.

    Returns:
        All replacements in `pathReplacements` applied to path, with `os.path.normpath`
        called on it for Windows. For Linux all `\\` are converted to forward slashes.
    """
    replacements = pathReplacements()
    if os_type == 'Windows':
        src = 1
        dest = 0
    else:
        src = 0
        dest = 1
    for replacement in replacements:

        def repl(match):
            # Don't modify our replacement string, just insert it.
            return replacement[dest]

        pattern = replacement[src]
        pattern = _path_escape(pattern)
        # Find and replace the text of the file paths ignoring case without
        # affecting the case of the remaining string case.
        path = re.sub(pattern, repl, path, flags=re.I)
    if os_type == 'Windows':
        return os.path.normpath(path)
    return path.replace('\\', '/')
