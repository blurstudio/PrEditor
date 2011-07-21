##
# 	\namespace	blurdev.osystem
#
# 	\remarks	This module provides additional methods that aren't easily found in existing
# 				python or Qt modules for cross-platform usage
#
# 	\author		eric.hulser@blur.com
# 	\author		Blur Studio
# 	\date		04/20/11
#

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
        \remarks	recursively expands the text variables, vs.
                    the os.path.expandvars method which only
                    works at one level
        \param		text		<str>
        \param		cache		<dict> { <str>: <str>, .. }		protects against recursive calls
        \return		<str>
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

    # resolve any duplicated path separators, etc.
    return os.path.normpath(output)


def console(filename):
    """
        \remarks	starts a console window at the given path
        \param		filename	<str>
        \return		<bool> success
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


def explore(filename):
    """
        \remarks	launches the filename given the current platform
        \param		filename	<str>
        \return		<bool> success
    """
    # pull the filpath from the inputed filename
    fpath = str(filename)
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


def shell(command, basepath='', persistent=False):
    """
        \remarks	runs the inputed shell command in its own window. If persistent keep the shell open after the command is run. Returns success
        
        \param		command		<command to run>
        \param		persistent	<bool>
        \return		<bool>
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
        \remarks	runs the filename in a shell with proper commands given, or passes the command to the shell. (CMD  in windows)
                    the current platform
        \param		filename	<str>
        \param		debugLevel	<blurdev.debug.DebugLevel>
        \param		basePath	<str>
        \return		<bool> success
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
