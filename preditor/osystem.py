"""
This module provides additional methods that aren't easily found in existing
python or Qt modules for cross-platform usage.

The osystem module provides a number of functions to make dealing with
paths and other platform-specific things in a more abstract platform-agnostic
way.
"""
from __future__ import absolute_import, print_function

import os
import subprocess
import sys
from builtins import str as text

import preditor

from . import settings


def getPointerSize():
    import struct

    try:
        size = struct.calcsize('P')
    except struct.error:
        # Older installations can only query longs
        size = struct.calcsize('l')
    size *= 8
    global getPointerSize

    def getPointerSize():
        return size

    return size


# Get the active version of python, not a hard coded value.
def pythonPath(pyw=False, architecture=None):
    if settings.OS_TYPE != 'Windows':
        return 'python'
    from distutils.sysconfig import get_python_inc

    # Unable to pull the path from the registry just use the current python path
    basepath = os.path.split(get_python_inc())[0]
    # build the path to the python executable. If requested use pythonw instead of
    # python
    return os.path.join(basepath, 'python{w}.exe'.format(w=pyw and 'w' or ''))


def defaultLogFile(filename='preditorProtocol.log'):
    """Returns a default log file path often used for redirecting stdout/err to.
    Uses the `BDEV_PATH_BLUR` environment variable as the basepath.

    Args:
        filename (str, optional): filename to log to.
    """
    basepath = expandvars(os.environ['BDEV_PATH_BLUR'])
    return os.path.join(basepath, filename)


def expandvars(text, cache=None):
    """
    Recursively expands the text variables, vs. the os.path.expandvars
    method which only works at one level.

    :param text: text string to expand
    :type text: str
    :param cache: used internally during recursion to prevent infinite loop
    :type cache: dict
    :rtype: str

    """
    # make sure we have data
    if not text:
        return ''

    import re

    # check for circular dependencies
    if cache is None:
        cache = {}

    # return the cleaned variable
    output = str(text)
    keys = re.findall(r'\$(\w+)|\${(\w+)\}|\%(\w+)\%', text)

    for first, second, third in keys:
        repl = ''
        key = ''
        if first:
            repl = '$%s' % first
            key = first
        elif second:
            repl = '${%s}' % second
            key = second
        elif third:
            repl = '%%%s%%' % third
            key = third
        else:
            continue

        value = os.environ.get(key)
        if value:
            if key not in cache:
                cache[key] = value
                value = expandvars(value, cache)
            else:
                print(
                    'WARNING! %s environ variable contains a circular dependency' % key
                )
                value = cache[key]
        else:
            value = repl

        output = output.replace(repl, value)

    return output


def explore(filename, dirFallback=False):
    """Launches the provided filename in the prefered editor for the specific platform.

    Args:
        filename (str): The file path to explore to.
        dirFallback (bool): If True, and the file path does not exist, explore to
            the deepest folder that does exist.

    Returns:
        bool: If it was able to explore the filename.
    """
    # pull the file path from the inputed filename
    fpath = os.path.normpath(filename)

    if dirFallback:
        # If the provided filename does not exist, recursively check each parent folder
        # for existence.
        while not os.path.exists(fpath) and not os.path.ismount(fpath):
            fpath = os.path.split(fpath)[0]

    # run the file in windows
    if settings.OS_TYPE == 'Windows':
        env = subprocessEnvironment()
        if os.path.isfile(fpath):
            subprocess.Popen(r'explorer.exe /select, "{}"'.format(fpath), env=env)
            return True
        subprocess.Popen(r'explorer.exe "{}"'.format(fpath), env=env)
        return True

    # run the file in linux
    elif settings.OS_TYPE == 'Linux':
        cmd = expandvars(os.environ.get('BDEV_CMD_BROWSE', ''))
        if not cmd:
            return False
        subprocess.Popen(cmd % {'filepath': fpath}, shell=True)
        return True
    return False


def subprocessEnvironment(env=None):
    """Returns a copy of the environment that will restore a new python instance to
    current state.

    Provides a environment dict that can be passed to subprocess.Popen that will restore
    the current treegrunt environment settings, and blurdev stylesheet. It also resets
    any environment variables set by a dcc that may cause problems when running a
    subprocess.

    Args:

        env (dict, Optional): The base dictionary that is modified with blurdev
            variables. if None(default) it will be populated with a copy of os.environ.

    Returns:
        dict: A list of environment variables to be passed to subprocess's env argument.
    """
    if env is None:
        env = os.environ.copy()

    # By default libstone adds "C:\Windows\System32\blur64" or "C:\blur\common" to
    # QApplication.libraryPaths(), setting this env var to a invalid path disables that.
    # Leaving this set likely will cause the subprocess to not be configured correctly.
    # The subprocess should be responsible for setting this variable
    if 'LIBSTONE_QT_LIBRARY_PATH' in env:
        del env['LIBSTONE_QT_LIBRARY_PATH']

    # If PYTHONPATH is being used, attempt to reset it to the system value.
    # Applications like maya add PYTHONPATH, and this breaks subprocesses.
    if env.get('PYTHONPATH'):
        if settings.OS_TYPE == 'Windows':
            try:
                # Store the 'PYTHONPATH' from the system registry if set
                env['PYTHONPATH'] = getEnvironmentVariable('PYTHONPATH')
            except WindowsError:
                # If the registry is not set, then remove the variable
                del env['PYTHONPATH']

    # If PYTHONHOME is used, just remove it. This variable is supposed to point
    # to a folder relative to the python stdlib
    # Applications like Houdini add PYTHONHOME, and it breaks the subprocesses
    if env.get('PYTHONHOME'):
        if settings.OS_TYPE == 'Windows':
            try:
                # Store the 'PYTHONHOME' from the system registry if set
                env['PYTHONHOME'] = getEnvironmentVariable('PYTHONHOME')
            except WindowsError:
                # If the registry is not set, then remove the variable
                del env['PYTHONHOME']

    # Some DCC's require inserting or appending path variables. When using subprocess
    # these path variables may cause problems with the target application. This allows
    # removing those path variables from the environment being passed to subprocess.
    def normalize(i):
        return os.path.normpath(os.path.normcase(i))

    removePaths = set([normalize(x) for x in preditor.core._removeFromPATHEnv])

    # blurpath records any paths it adds to the PATH variable and other env variable
    # modifications it makes, revert these changes.
    try:
        import blurpath

        # Restore the original environment variables stored by blurpath.
        blurpath.resetEnvVars(env)  # blurpath v0.0.16 or newer
    except ImportError:
        pass
    except AttributeError:
        # TODO: Once blurpath v0.0.16 or newer is passed out, remove the
        # outter AttributeError except block. Its just for backwards compatibility.
        try:
            removePaths.update([normalize(x) for x in blurpath.addedToPathEnv])
        except AttributeError:
            pass

    path = env.get('PATH')
    if path:
        paths = [
            x for x in path.split(os.path.pathsep) if normalize(x) not in removePaths
        ]
        path = os.path.pathsep.join(paths)
        # subprocess does not accept unicode in python 2
        if sys.version_info[0] == 2 and isinstance(path, text):
            path = path.encode('utf8')
        env['PATH'] = path

    # settings.environStr does nothing in python3, so this code only needs
    # to run in python2
    if sys.version_info[0] < 3:
        # subprocess explodes if it receives unicode in Python2 and in Python3,
        # it explodes if it *doesn't* receive unicode.
        temp = {}
        for k, v in env.items():
            # Attempt to remove any unicode objects. Ignore any conversion failures
            try:
                k = settings.environStr(k)
            except Exception:
                pass
            try:
                v = settings.environStr(v)
            except AttributeError:
                pass
            temp[k] = v
        env = temp

    return env


# --------------------------------------------------------------------------------
#                               Read registy values
# --------------------------------------------------------------------------------
def getRegKey(registry, key, architecture=None, write=False):
    """Returns a winreg hkey or none.

    Args: registry (str): The registry to look in. 'HKEY_LOCAL_MACHINE' for example

        key (str): The key to open. r'Software\\Autodesk\\Softimage\\InstallPaths' for
            example

        architecture (int | None): 32 or 64 bit. If None use system default.
            Defaults to None

    Returns:
        A winreg handle object
    """
    # Do not want to import winreg unless it is neccissary
    regKey = None
    import winreg

    aReg = winreg.ConnectRegistry(None, getattr(winreg, registry))
    if architecture == 32:
        sam = winreg.KEY_WOW64_32KEY
    elif architecture == 64:
        sam = winreg.KEY_WOW64_64KEY
    else:
        sam = 0
    access = winreg.KEY_READ
    if write:
        access = winreg.KEY_WRITE
    try:
        regKey = winreg.OpenKey(aReg, key, 0, access | sam)
    except WindowsError:
        pass
    return regKey


def registryValue(registry, key, value_name, architecture=None):
    """Returns the value and type of the provided registry key's value name.

    Args:

        registry (str): The registry to look in. 'HKEY_LOCAL_MACHINE' for example

        key (str): The key to open. r'Software\\Autodesk\\Softimage\\InstallPaths' for
            example

        value_name (str): The name of the value to read. To read the '(Default)' key
            pass a empty string.

        architecture (int | None): 32 or 64 bit. If None use system default.
            Defaults to None.

    Returns:
        object: Value stored in key
        int: registry type for value. See winreg's Value Types
    """
    # Do not want to import winreg unless it is neccissary
    regKey = getRegKey(registry, key, architecture=architecture)
    if regKey:
        import winreg

        return winreg.QueryValueEx(regKey, value_name)
    return '', 0


def getEnvironmentRegKey(machine=False):
    """Get the Registry Path and Key for the environment, either of the current
    user or the system.

    Args:
        machine (bool, optional): If True, the system Environment location will
            be returned.  Otherwise, the Environment location for the current
            user will be returned.  Defaults to False.

    Returns:
        tuple: Returns a tuple of two strings (registry path, key).
    """
    registry = 'HKEY_CURRENT_USER'
    key = r'Environment'
    # Replace {PATH} with the existing path variable.
    if machine:
        registry = 'HKEY_LOCAL_MACHINE'
        key = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    return registry, key


def getEnvironmentVariable(value_name, system=None, default=None, architecture=None):
    """Returns the environment variable stored in the windows registry.

    Args:
        value_name (str): The name of the environment variable to get the value of.
        system (bool or None, optional): If True, then only look in the system
            environment variables. If False, then only look at the user
            environment variables. If None(default), then return the user value
            if set, otherwise return the system value.
        default: If the variable is not set, return this value.
            If None(default) then a WindowsError is raised.
        architecture (int or None): 32 or 64 bit. If None use system default.
            Defaults to None.

    Raises:
        WindowsError: [Error 2] is returned if the environment variable is not
            stored in the requested registry. If you pass a default value other
            than None this will not be raised.
    """
    if system is None and value_name.lower() == 'path':
        msg = "PATH is a special environment variable, set system to True or False."
        raise ValueError(msg)

    if not system:
        # system is None or False, so check user variables.
        registry, key = getEnvironmentRegKey(False)
        try:
            return registryValue(registry, key, value_name, architecture=architecture)[
                0
            ]
        except WindowsError:
            pass
        if system is False:
            # If system is False, then return the default.
            # If None, then check the system.
            if default is None:
                raise
            return default

    registry, key = getEnvironmentRegKey(True)
    try:
        return registryValue(registry, key, value_name, architecture=architecture)[0]
    except WindowsError:
        if default is None:
            raise
        return default
