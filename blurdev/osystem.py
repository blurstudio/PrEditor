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
import re
import subprocess

from PyQt4.QtCore import QProcess

from blurdev import settings

EXTENSION_MAP = {
    '.py': 'BDEV_CMD_PYTHON',
}


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

    # check for circular dependencies
    if cache == None:
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
        import blurdev.scripts

        if not path:
            path = blurdev.scripts.winshell.desktop(1)
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
                    import platform

                    if platform.architecture()[0] == '64bit':
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
        print shortcut, '---', target, '---', args, '---', startin, '---', icon, '---', description
        if icon:
            blurdev.scripts.winshell.CreateShortcut(
                shortcut,
                target,
                Arguments='"%s"' % args,
                StartIn=startin,
                Icon=(icon, 0),
                Description=description,
            )
        else:
            blurdev.scripts.winshell.CreateShortcut(
                shortcut,
                target,
                Arguments=args,
                StartIn=startin,
                Description=description,
            )
        import blurdev.media

        blurdev.media.setAppIdForIcon(shortcut, 'Blur.%s' % title.replace(' ', ''))


def explore(filename):
    """Launches the filename given the current platform

    """
    # pull the filpath from the inputed filename
    fpath = os.path.normpath(unicode(filename))
    if not os.path.isdir(fpath):
        fpath = os.path.split(fpath)[0]

    # run the file in windows
    if settings.OS_TYPE == 'Windows':
        return os.startfile(fpath)

    # run the file in linux
    elif settings.OS_TYPE == 'Linux':
        cmd = expandvars(os.environ.get('BDEV_CMD_BROWSE', ''))
        if not cmd:
            return False

        subprocess.Popen(cmd % {'filepath': fpath}, shell=True)


def programFilesPath(path=''):
    """Returns the path to 32bit program files on windows.
    
    :param path: this string is appended to the path
    
    """
    import platform

    if platform.architecture()[0] == '64bit':
        progF = 'ProgramFiles(x86)'
    else:
        progF = 'programfiles'
    return r'%s\%s' % (os.getenv(progF), path)


def shell(command, basepath='', persistent=False):
    """
    Runs the given shell command in its own window.  The command will be run
    from the current working directory, or from *basepath*, if given.  
    If persistent is True, the shell will stay open after the command is run.
>
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


def startfile(filename, debugLevel=None, basePath='', cmd=None):
    """
    Runs the filename in a shell with proper commands given, or passes 
    the command to the shell. (CMD in windows) the current platform
    
    :param filename: path to the file to execute
    :type filename: str
    :param debugLevel: debug level
    :type debugLevel: :data:`blurdev.debug.DebugLevel`
    :param basePath: working directory where the command should be called
                     from.  If omitted, the current working directory is
                     used.
    :type basePath: str
    
    """
    # determine the debug level
    import os
    from blurdev import debug
    from PyQt4.QtCore import QProcess
    import subprocess

    success = False
    filename = str(filename)

    # make sure that the code we're running
    if not (os.path.isfile(filename) or filename.startswith('http://')):
        return False

    if debugLevel == None:
        debugLevel = debug.debugLevel()

    # determine the base path for the system
    filename = str(filename)
    if not basePath:
        basePath = os.path.split(filename)[0]

    # strip out the information we need
    ext = os.path.splitext(filename)[1]
    if cmd == None:
        if filename.startswith('http://'):
            cmd = expandvars(os.environ.get('BDEV_CMD_WEB', ''))
        else:
            cmd = expandvars(os.environ.get(EXTENSION_MAP.get(ext, ''), ''))

    options = {'filepath': filename, 'basepath': basePath}

    # if the debug level is high, run the command with a shell in the background
    if ext == '.sh' or debugLevel == debug.DebugLevel.High:
        # run it in debug mode for windows
        if settings.OS_TYPE == 'Windows':
            if cmd:
                success, value = QProcess.startDetached(
                    'cmd.exe', ['/k', '"%s"' % (cmd % options)], basePath
                )
            else:
                success, value = QProcess.startDetached(
                    'cmd.exe', ['/k', filename], basePath
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
                success = subprocess.Popen(cmd % options, shell=True)
            else:
                success, value = QProcess.startDetached(filename, [], basePath)

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
