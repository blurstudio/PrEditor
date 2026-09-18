from __future__ import absolute_import, print_function

import datetime
import inspect
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Keeps the file `faulthandlerToFile` installed open for the life of the process
_faulthandlerFile = None


class FileLogger:
    def __init__(self, stdhandle, logfile, _print=True, clearLog=True):
        self.old_stream = stdhandle
        # Accept pathlib objects but store the path as a string
        self._logfile = os.fspath(logfile)
        self._print = _print
        if clearLog:
            # clear the log file
            self.clear()

    def clear(self, stamp=False):
        """Removes the contents of the log file."""
        open(self._logfile, 'w', newline="\n", encoding="utf-8").close()
        if stamp:
            print(self.stamp())

    def flush(self):
        if self.old_stream:
            self.old_stream.flush()

    def stamp(self):
        msg = '--------- Date: {today} Version: {version} ---------'
        return msg.format(today=datetime.datetime.today(), version=sys.version)

    def write(self, msg):
        # Newline forces windows to write unix style newlines
        with open(self._logfile, 'a', newline="\n", encoding="utf-8") as f:
            f.write(msg)

        if self._print:
            self.old_stream.write(msg)


def logToFile(path, stdout=True, stderr=True, useOldStd=True, clearLog=True):
    """Redirect all stdout and/or stderr output to a log file.

    Creates a FileLogger class for stdout and stderr and installs itself in python.
    All output will be logged to the file path. Prints the current datetime and
    sys.version info when stdout is True.

    Args:
        path (str or os.PathLike): File path to log output to.

        stdout (bool): If True(default) override sys.stdout.

        stderr (bool): If True(default) override sys.stderr.

        useOldStd (bool): If True, messages will be written to the FileLogger
            and the previous sys.stdout/sys.stderr.

        clearLog (bool): If True(default) clear the log file when this command is
        called.
    """
    if stderr:
        sys.stderr = FileLogger(sys.stderr, path, useOldStd, clearLog=clearLog)
    if stdout:
        sys.stdout = FileLogger(sys.stdout, path, useOldStd, clearLog=False)
        if clearLog:
            sys.stdout.clear(stamp=True)

    from .streamhandler_helper import StreamHandlerHelper

    # Update any StreamHandler's that were setup using the old stdout/err
    if stdout:
        StreamHandlerHelper.replace_stream(sys.stdout.old_stream, sys.stdout)
    if stderr:
        StreamHandlerHelper.replace_stream(sys.stderr.old_stream, sys.stderr)


def faulthandlerToFile(path, allThreads=True, clearLog=True, force=False):
    """Install faulthandler so hard crashes are written to a log file.

    Python normally can't report fatal errors like segfaults, they simply kill
    the process without any output. Enabling faulthandler makes python dump the
    traceback of each thread to a file when one of those errors happens, which
    is often the only record of what a host application was doing when it died.

    Unlike `logToFile` this doesn't touch sys.stdout/sys.stderr. faulthandler
    writes to the file descriptor directly, so it needs a real file on disk, not
    a `FileLogger`. The file is left open for the life of the process, closing
    it would leave faulthandler writing to an invalid file descriptor.

    If faulthandler is already enabled it's left alone unless force is used.
    This includes it being enabled outside of this function, for example by the
    `PYTHONFAULTHANDLER` env var or `python -X faulthandler`.

    Args:
        path (str or os.PathLike): File path to write faulthandler output to.

        allThreads (bool): If True(default) dump the traceback of all threads,
            otherwise only the thread that crashed.

        clearLog (bool): If True(default) clear the log file when this command
            is called, otherwise append to the existing contents.

        force (bool): If True, install faulthandler even if it was already
            enabled. Any file opened by a previous call is closed.

    Returns:
        bool: If faulthandler was installed by this call. False is returned if
            it was already enabled and force was not used.
    """
    global _faulthandlerFile
    import faulthandler

    if faulthandler.is_enabled() and not force:
        logger.debug('faulthandler is already enabled, not logging to: %s', path)
        return False

    # Newline forces windows to write unix style newlines
    output = open(path, 'w' if clearLog else 'a', newline="\n", encoding="utf-8")
    faulthandler.enable(file=output, all_threads=allThreads)

    # Only close the file used by a previous call once the new one is installed
    previous = _faulthandlerFile
    _faulthandlerFile = output
    if previous is not None:
        previous.close()

    return True


def printCallingFunction(compact=False):
    """Prints and returns info about the calling function

    Args:
        compact (bool): If set to True, prints a more compact printout

    Returns:
        str: Info on the calling function.
    """
    import inspect

    current = inspect.currentframe().f_back
    try:
        parent = current.f_back
    except AttributeError:
        print('No Calling function found')
        return
    currentInfo = inspect.getframeinfo(current)
    parentInfo = inspect.getframeinfo(parent)
    if parentInfo[3] is not None:
        context = ', '.join(parentInfo[3]).strip('\t').rstrip()
    else:
        context = 'No context to return'
    if compact:
        output = '# %s Calling Function: %s Filename: %s Line: %i Context: %s' % (
            currentInfo[2],
            parentInfo[2],
            parentInfo[0],
            parentInfo[1],
            context,
        )
    else:
        output = ["Function: '%s' in file '%s'" % (currentInfo[2], currentInfo[0])]
        output.append(
            "    Calling Function: '%s' in file '%s'" % (parentInfo[2], parentInfo[0])
        )
        output.append("    Line: '%i'" % parentInfo[1])
        output.append("    Context: '%s'" % context)
        output = '\n'.join(output)
    print(output)
    return output


def mroDump(obj, nice=True, joinString='\n'):
    """Formats inspect.getmro into text.

    For the given class object or instance of a class, use inspect to return the Method
    Resolution Order.

    Args: obj (object): The object to return the mro of. This can be a class object or
        instance.1

        nice (bool): Returns the same module names as help(object) if True, otherwise
        repr(object).

        joinString (str, optional): The repr of each class is joined by this string.

    Returns:
        str: A string showing the Method Resolution Order of the given object.
    """
    import pydoc

    # getmro requires a class, turn instances into a class
    if not inspect.isclass(obj):
        obj = type(obj)
    classes = inspect.getmro(obj)
    if nice:
        ret = [pydoc.classname(x, obj.__module__) for x in (classes)]
    else:
        ret = [repr(x) for x in (classes)]
    return joinString.join(ret)
