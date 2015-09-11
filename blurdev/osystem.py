"""
This module provides additional methods that aren't easily found in existing
python or Qt modules for cross-platform usage.

The osystem module provides a number of functions to make dealing with
paths and other platform-specific things in a more abstract platform-agnostic
way.

.. data:: EXTENSION_MAP

   Dictionary of (extension: blurdev_enviroment_variable) pairs used by 
   :func:`startfile` to execute scripts and other files.
   This allows blurdev to associate filetypes with executable targets outside
   of the normal windows file association mechanism.

"""

import os
import subprocess

from PyQt4.QtCore import QProcess

import blurdev
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
    getPointerSize = lambda: size
    return size


# Get the active version of python, not a hard coded value.
def pythonPath(pyw=False, architecture=None):
    if settings.OS_TYPE != 'Windows':
        return 'python'
    # Attempt to get the basepath from the registry
    try:
        basepath, typ = blurdev.osystem.registryValue(
            'HKEY_LOCAL_MACHINE',
            r'SOFTWARE\Python\PythonCore\2.7\InstallPath',
            '',
            architecture=architecture,
        )
    except WindowsError:
        basepath = ''
    if not basepath:
        from distutils.sysconfig import get_python_inc

        # Unable to pull the path from the registry just use the current python path
        basepath = os.path.split(get_python_inc())[0]
    # build the path to the python executable. If requested use pythonw instead of python
    return os.path.join(basepath, 'python{w}.exe'.format(w=pyw and 'w' or ''))


EXTENSION_MAP = {}


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
    keys = re.findall('\$(\w+)|\${(\w+)\}|\%(\w+)\%', text)

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
            if not key in cache:
                cache[key] = value
                value = expandvars(value, cache)
            else:
                print 'WARNING! %s environ variable contains a circular dependency' % key
                value = cache[key]
        else:
            value = repl

        output = output.replace(repl, value)

    return output


def console(filename):
    """Starts a console window at the given path

    """
    # pull the filpath from the inputed filename
    fpath = str(filename)
    if not os.path.isdir(fpath):
        fpath = os.path.dirname(fpath)

    # run the file in windows
    cmd = expandvars(os.environ.get('BDEV_CMD_SHELL_BROWSE', ''))
    if not cmd:
        return False

    if settings.OS_TYPE != 'Windows':
        subprocess.Popen(cmd % {'filepath': fpath}, shell=True)
    else:
        QProcess.startDetached('cmd.exe', [], fpath)

    return True


def createShortcut(
    title, args, startin=None, target=None, icon=None, path=None, description=''
):
    """Creates a shortcut. 
        
    Windows: If icon is provided it looks for a .ico file with the same name 
    as the provided icon.  If it can't find a .ico file it will attempt to 
    create one using ImageMagick(http://www.imagemagick.org/).  ImageMagick 
    should be installed to the 32bit program files 
    (64Bit Windows: C:\Program Files (x86)\ImageMagick, 
    32Bit Windows: C:\Program Files\ImageMagick)
    
    :param title: the title for the shortcut
    :param args: argument string to pass to target command
    :param startin: path where the shortcut should run target command
    :param target: the target for the shortcut
    :param icon: path to the icon the shortcut should use
    :param path: path where the shortcut should be created
    :param description: helpful description for the shortcut
                    
    """
    if settings.OS_TYPE == 'Windows':
        from . import scripts

        if not path:
            path = scripts.winshell.desktop(1)
            if not os.path.exists(path):
                os.makedirs(path)
        if not target:
            import sys

            target = sys.executable
        if not startin:
            startin = os.path.split(args)[0]
        if icon:
            pathName, ext = os.path.splitext(icon)
            if not ext == '.ico':
                icon = pathName + '.ico'
            # calculate the path to copy the icon to
            outPath = r'%s\blur\icons' % os.getenv('appdata')
            if not os.path.exists(outPath):
                os.makedirs(outPath)
            outIcon = os.path.abspath('%s\%s.ico' % (outPath, title))
            if os.path.exists(icon):
                import shutil

                shutil.copyfile(icon, outIcon)
                if os.path.exists(outIcon):
                    icon = outIcon
                else:
                    icon = None
            else:
                if ext == '.png':
                    if getPointerSize() == 64:
                        progF = 'ProgramFiles(x86)'
                    else:
                        progF = 'programfiles'
                    converter = r'%s\ImageMagick\convert.exe' % os.getenv(progF)
                    if os.path.exists(converter):
                        icon = outIcon
                        cmd = '"%s" "%s.png" "%s"' % (converter, pathName, icon)
                        out = subprocess.Popen(cmd)
                        out.wait()
                        if not os.path.exists(icon):
                            icon = None
                    else:
                        icon = None

        shortcut = os.path.join(path, '%s.lnk' % title)
        # If the shortcut description is longer than 260 characters, the target may end up with
        # random unicode characters, and the icon is not set properly. The Properties dialog only
        # shows 259 characters in the description, so we limit the description to 259 characters.
        description = description[:259]

        print shortcut, '---', target, '---', args, '---', startin, '---', icon, '---', description
        if icon:
            scripts.winshell.CreateShortcut(
                shortcut,
                target,
                Arguments='"%s"' % args,
                StartIn=startin,
                Icon=(icon, 0),
                Description=description,
            )
        else:
            scripts.winshell.CreateShortcut(
                shortcut,
                target,
                Arguments=args,
                StartIn=startin,
                Description=description,
            )
        blurdev.media.setAppIdForIcon(shortcut, 'Blur.%s' % title.replace(' ', ''))


def explore(filename):
    """ Launches the filename given the current platform
    """
    # pull the filpath from the inputed filename
    fpath = os.path.normpath(unicode(filename))
    # run the file in windows
    if settings.OS_TYPE == 'Windows':
        if os.path.isfile(fpath):
            subprocess.Popen(r'explorer.exe /select, "{}"'.format(fpath))
            return True
        subprocess.Popen(r'explorer.exe "{}"'.format(fpath))
        return True

    if not os.path.isdir(fpath):
        fpath = os.path.split(fpath)[0]

    # run the file in linux
    elif settings.OS_TYPE == 'Linux':
        cmd = expandvars(os.environ.get('BDEV_CMD_BROWSE', ''))
        if not cmd:
            return False
        subprocess.Popen(cmd % {'filepath': fpath}, shell=True)


def programFilesPath(path=''):
    """ Returns the path to 32bit program files on windows.
    
        :param path: this string is appended to the path
    """
    if getPointerSize() == 64:
        progF = 'ProgramFiles(x86)'
    else:
        progF = 'programfiles'
    return r'%s\%s' % (os.getenv(progF), path)


def shell(command, basepath='', persistent=False):
    """
    Runs the given shell command in its own window.  The command will be run
    from the current working directory, or from *basepath*, if given.  
    If persistent is True, the shell will stay open after the command is run.

    """
    if not basepath:
        basepath = os.curdir

    # run it in debug mode for windows
    if settings.OS_TYPE == 'Windows':
        if persistent:
            success, value = QProcess.startDetached(
                'cmd.exe', ['/k', command], basepath
            )
        else:
            success, value = QProcess.startDetached(
                'cmd.exe', ['/c', command], basepath
            )

    # run it for Linux systems
    elif settings.OS_TYPE == 'Linux':
        shellcmd = expandvars(os.environ.get('BDEV_CMD_SHELL_EXEC', ''))
        if not shellcmd:
            return False

        # create a temp shell file
        temppath = os.environ.get('BDEV_PATH_TEMP', '')
        if not temppath:
            return False

        if not os.path.exists(temppath):
            os.mkdir(temppath)

        # write a temp shell command
        tempfilename = os.path.join(temppath, 'debug.sh')
        tempfile = open(tempfilename, 'w')
        tempfile.write('echo "running command: %s"\n' % (command))
        tempfile.write(command)
        tempfile.close()

        # make sure the system can run the file
        os.system('chmod 0755 %s' % tempfilename)

        # run the file
        success = subprocess.Popen(
            shellcmd % {'basepath': basepath, 'command': command}, shell=True
        )
    else:
        return False
    return success


def startfile(filename, debugLevel=None, basePath='', cmd=None, architecture=None):
    """
    Runs the filename in a shell with proper commands given, or passes 
    the command to the shell. (CMD in windows) the current platform
    
    :param filename: path to the file to execute
    :type filename: str
    :param debugLevel: debug level
    :type debugLevel: :data:`blurdev.debug.DebugLevel`
    :param basePath: working directory where the command should be called
                     from.  If omitted, the current working directory is used.
    :type basePath: str
    
    """
    # determine the debug level
    debug = blurdev.debug

    success = False
    filename = str(filename)

    # make sure that the code we're running
    if not (os.path.isfile(filename) or filename.startswith('http://')):
        return False

    if debugLevel is None:
        debugLevel = debug.debugLevel()

    # determine the base path for the system
    filename = str(filename)
    if not basePath:
        basePath = os.path.split(filename)[0]

    # strip out the information we need
    ext = os.path.splitext(filename)[1]
    if cmd is None:
        if filename.startswith('http://'):
            cmd = expandvars(os.environ.get('BDEV_CMD_WEB', ''))
        elif ext in (".py", ".pyw"):
            cmd = (
                pythonPath(pyw=ext == ".pyw", architecture=architecture)
                + ' "%(filepath)s"'
            )
        else:
            cmd = expandvars(os.environ.get(EXTENSION_MAP.get(ext, ''), ''))

    options = {'filepath': filename, 'basepath': basePath}

    # build the environment to pass along
    env = None
    env = os.environ.copy()
    actEnv = blurdev.activeEnvironment()
    envPath = actEnv.path()
    if envPath:
        env['BLURDEV_PATH'] = str(envPath)
        email = actEnv.emailOnError()
        if email:
            env['BLURDEV_ERROR_EMAIL'] = str(email[0])
        env['BDEV_ENVIRONMENT_OFFLINE'] = repr(actEnv.isOffline())
        env['BDEV_ENVIRONMENT_DEVEL'] = repr(actEnv.isDevelopment())
        env['BDEV_ENVIRONMENT_ENVIRON_FILE'] = str(actEnv.sourceFile())

    # Sets the stylesheet env variable so that launched applications can use it.
    stylesheet = blurdev.core.styleSheet()
    if stylesheet:
        env['BDEV_STYLESHEET'] = str(stylesheet)

    # if the debug level is high, run the command with a shell in the background
    if ext == '.sh' or debugLevel == debug.DebugLevel.High:
        # run it in debug mode for windows
        if settings.OS_TYPE == 'Windows':
            # make sure .pyw files are opened with python.exe, not pythonw.exe so we can actually debug problems.
            if ext == '.pyw':
                cmd = (
                    pythonPath(pyw=False, architecture=architecture) + ' "%(filepath)s"'
                )
            if cmd:
                success = subprocess.Popen(
                    'cmd.exe /k %s' % cmd % options, env=env, cwd=basePath
                )
            else:
                success = subprocess.Popen(
                    'cmd.exe /k "%s"' % filename, env=env, cwd=basePath
                )

        # run it for Linux systems
        elif settings.OS_TYPE == 'Linux':
            debugcmd = expandvars(os.environ.get('BDEV_CMD_SHELL_DEBUG', ''))

            # if there is a command associated with the inputed file, use that
            if not cmd:
                cmd = expandvars(os.environ.get('BDEV_CMD_SHELL_EXECFILE', ''))

            # create a temp shell file
            temppath = os.environ.get('BDEV_PATH_TEMP', '')
            if not temppath:
                return False

            if not os.path.exists(temppath):
                os.mkdir(temppath)

            # write a temp shell command
            tempfilename = os.path.join(temppath, 'debug.sh')
            tempfile = open(tempfilename, 'w')
            tempfile.write('echo "running command: %s"\n' % (cmd % options))
            tempfile.write(cmd % options)
            tempfile.close()

            # make sure the system can run the file
            os.system('chmod 0755 %s' % tempfilename)

            # run the file
            options['filepath'] = tempfilename
            success = subprocess.Popen(debugcmd % options, shell=True)

        return success
    # otherwise run it directly
    else:
        # run the command in windows
        if settings.OS_TYPE == 'Windows':
            if cmd:
                success = subprocess.Popen(
                    cmd % options, shell=True, cwd=basePath, env=env
                )
            else:
                success = subprocess.Popen(
                    '"%s"' % filename, cwd=basePath, env=env, shell=True
                )
            if not success:
                try:
                    success = os.startfile(filename)
                except:
                    pass

        # in other platforms, we'll use subprocess.Popen
        else:
            if cmd:
                success = subprocess.Popen(cmd % options, shell=True)
            else:
                cmd = expandvars(os.environ.get('BDEV_CMD_SHELL_EXECFILE', ''))
                if not cmd:
                    return False
                success = subprocess.Popen(cmd % options, shell=True)
    return success


def tempfile(filepath):
    return os.path.join(os.environ.get('BDEV_PATH_TEMP', ''), filepath)


def username():
    """
    This function checks the environment variables LOGNAME, USER, LNAME and 
    USERNAME, in order, and returns the value of the first one which is set 
    to a non-empty string. If none are set, the login name from the 
    password database is returned on systems which support the pwd module; 
    otherwise, returns an empty string.

    """
    import getpass

    try:
        return getpass.getuser()
    except getpass.GetPassWarning:
        pass
    return ''


# --------------------------------------------------------------------------------
# 								Read registy values
# --------------------------------------------------------------------------------
def getRegKey(registry, key, architecture=None):
    """ Returns a _winreg hkey or none.
    
    Args:
        registry (str): The registry to look in. 'HKEY_LOCAL_MACHINE' for example
        key (str): The key to open. r'Software\Autodesk\Softimage\InstallPaths' for example
        architecture (int | None): 32 or 64 bit. If None use system default. Defaults to None
    
    Returns:
        A _winreg handle object
    """
    # Do not want to import _winreg unless it is neccissary
    regKey = None
    import _winreg

    aReg = _winreg.ConnectRegistry(None, getattr(_winreg, registry))
    if architecture == 32:
        sam = _winreg.KEY_WOW64_32KEY
    elif architecture == 64:
        sam = _winreg.KEY_WOW64_64KEY
    else:
        sam = 0
    try:
        regKey = _winreg.OpenKey(aReg, key, 0, _winreg.KEY_READ | sam)
    except WindowsError:
        pass
    return regKey


def listRegKeyValues(registry, key, architecture=None):
    """ Returns a list of child keys and their values as tuples.
    
    Each tuple contains 3 items.
        - A string that identifies the value name
        - An object that holds the value data, and whose type depends on the underlying registry type
        - An integer that identifies the type of the value data (see table in docs for _winreg.SetValueEx)
    
    Args:
        registry (str): The registry to look in. 'HKEY_LOCAL_MACHINE' for example
        key (str): The key to open. r'Software\Autodesk\Softimage\InstallPaths' for example
        architecture (int | None): 32 or 64 bit. If None use system default. Defaults to None
    
    Returns:
        List of tuples
    """
    import _winreg

    regKey = getRegKey(registry, key, architecture=architecture)
    ret = []
    if regKey:
        subKeys, valueCount, modified = _winreg.QueryInfoKey(regKey)
        for index in range(valueCount):
            ret.append(_winreg.EnumValue(regKey, index))
    return ret


def listRegKeys(registry, key, architecture=None):
    import _winreg

    regKey = getRegKey(registry, key, architecture=architecture)
    ret = []
    if regKey:
        index = 0
        while True:
            try:
                ret.append(_winreg.EnumKey(regKey, index))
                index += 1
            except WindowsError:
                break
    return ret


def registryValue(registry, key, value_name, architecture=None):
    """ Returns the value and type of the provided registry key's value name.
    
    Args:
        registry (str): The registry to look in. 'HKEY_LOCAL_MACHINE' for example
        key (str): The key to open. r'Software\Autodesk\Softimage\InstallPaths' for example
        value_name (str): The name of the value to read. To read the '(Default)' key pass a 
            empty string.
        architecture (int | None): 32 or 64 bit. If None use system default. Defaults to None
    
    Returns:
        object: Value stored in key
        int: registry type for value. See _winreg's Value Types
    """
    # Do not want to import _winreg unless it is neccissary
    regKey = getRegKey(registry, key, architecture=architecture)
    if regKey:
        import _winreg

        return _winreg.QueryValueEx(regKey, value_name)
    return '', 0
