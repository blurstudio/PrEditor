from __future__ import print_function
from __future__ import absolute_import
import sys
import os
import shutil
import tempfile
import errno
import time
import blurdev
import logging

# Note: If a different version of python is launched importing pre-compiled modules
# could cause a exception. For example, MotionBuilder 2016 has python 2.7.6 embeded,
# while at blur we currently have python 2.7.3 installed externally. Also applications
# like Maya 2016 compile python with newer versions of Visual Studio than normal which
# also causes problems.
import blurdev.debug
import traceback

# If possible use blur.Stone's isRunning. It works in Maya 2016 without needing to
# compile a special build of psutil. If neither psutil or blur.Stone is installed
# monitorForCrash will not be launched and temp files will be orphaned if python
# is killed by a external process.
try:
    # If Stone is not importable monitorForCrash for clash will not be used
    import blur.Stone as Stone
except ImportError:
    Stone = None
try:
    import psutil
except ImportError:
    psutil = None

_LOGGER = logging.getLogger(__name__)


def monitorForCrash(pid, conn):
    """Multiprocessing function used to clean up temp files if the parent process is
    killed.
    """
    # Note: importing inside this function can cause dll errors when running inside a
    # DCC.
    try:
        tempFiles = []
        tempDirs = []
        _LOGGER.info(
            '[monitorForCrash] Checking pid, {}, {}'.format(pid, (Stone, psutil))
        )
        while (Stone and Stone.isRunning(pid)) or psutil and psutil.pid_exists(pid):
            try:
                if conn.poll():
                    data = conn.recv()
                    if data[0] == 'tempFile':
                        tempFiles.append(data[1])
                        _LOGGER.info(
                            '[monitorForCrash] Adding tempFile, {}'.format(data[1])
                        )
                        # Check for more data instead of sleeping
                        continue
                    elif data[0] == 'tempDir':
                        tempDirs.append(data[1])
                        _LOGGER.info(
                            '[monitorForCrash] Adding tempDir, {}'.format(data[1])
                        )
                        # Check for more data instead of sleeping
                        continue
                    elif data[0] == 'finished':
                        _LOGGER.info(
                            '[monitorForCrash] Parent process is done, '
                            'exiting without doing anything'
                        )
                        return
            except IOError as e:
                if e.errno == 109:
                    # The pipe has been ended, assume the parent process was killed
                    _LOGGER.info('[monitorForCrash] IOError 109')
                    break
            time.sleep(1)

        _LOGGER.info('[monitorForCrash] Removing tempFiles, {}'.format(tempFiles))
        _LOGGER.info('[monitorForCrash] Removing tempDirs, {}'.format(tempDirs))
        # Remove any created folders from disk and their contents
        for tempDir in tempDirs:
            shutil.rmtree(tempDir, ignore_errors=True)
        # Remove any created temp files
        for tempFile in tempFiles:
            try:
                os.remove(tempFile)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    _LOGGER.info(
                        '[monitorForCrash] File already deleted, {}, {}'.format(
                            e, tempFile
                        )
                    )
    except Exception:
        traceback.print_exc()
        time.sleep(20)
        raise


class TempFilesContext(object):
    """Context to create multiple temp files and directories that will be removed.

    This class is used to manage generation of multiple temp files and directories.
    The files and directories created by makeTempDirectory and makeTempFile will
    be removed once this contex exits.

    Keyed mode returns the same object if one of the make functions is called twice
    with the same key.

    If the environment variable "BDEV_KEEP_TEMPFILESCONTEXT" is set to "true", then
    the temp files and directories will not be removed when the context exits. This
    forces crashMonitor to False, and must be set before the Context is created. When
    the context exits, it will log a list of all temp directories and files that
    were created and not deleted.

    Note:
        The crashMonitor option uses multiprocessing to monitor if the main python
        module was killed. Because of how multiprocessing works on windows, if you
        used a script when launching python you need to make sure that the main
        module can be safely imported by a new Python interpreter without causing
        unintended side effects (such as calling TempFilesContext(crashMonitor=True)).
        Simply put, make sure you use in your scripts(if __name__ == '__main__':)
        See https://docs.python.org/2/library/multiprocessing.html#windows search
        for "Safe importing of main module" for more info.

    Args:
        keyed (bool): Enables Keyed mode. Defaults to True.
        dirname (str|None): If not None(the default) this is passed to tempfile
            functions as the dir kwarg if that kwarg is not provided in the call.
        crashMonitor (bool): If True(default), use multiprocessing to launch a watcher
            process if python is killed by some external process while inside this
            context this external process will remove all temp files created by the
            context.
        pythonw (bool): If True multiprocessing.set_executable will be set to
            pythonw.exe. If False (default) it will be set to python.exe. If False
            the log statements in the monitorForCrash() child process appear to
            be redirected back to the parent process. This is useful for debugging.
    """

    def __init__(
        self,
        keyed=True,
        dirname=None,
        crashMonitor=True,
        pythonw=False,
        defaultDir=None,
    ):
        # TODO: This can be removed when all the dependencies are refactored.
        if defaultDir is not None:
            warning = (
                'Use dirname argument instead of defaultDir with TempFilesContext.'
            )
            _LOGGER.warning(warning)
            dirname = defaultDir
        self.keyed = keyed
        self._dirname = dirname
        self._tempDirs = {}
        self._tempFiles = {}
        self.keepTempFiles = (
            os.getenv('BDEV_KEEP_TEMPFILESCONTEXT', 'false').lower() == 'true'
        )
        self.crashMonitor = crashMonitor if not self.keepTempFiles else False

        if self.crashMonitor:
            if Stone or psutil:
                import multiprocessing
                from multiprocessing import Process, Pipe

                self.pipe, child_conn = Pipe()
                pid = os.getpid()
                # If python is embeded in a application multiprocessing will launch a
                # new instance of that instead of python, so force it to run python.
                multiprocessing.set_executable(blurdev.osystem.pythonPath(pyw=pythonw))

                # multiprocessing requires sys.argv so manually create it if it doesn't
                # already exist
                if not hasattr(sys, 'argv'):
                    sys.argv = ['']
                # Some applications like MotionBuilder break multiprocessing with their
                # sys.argv values.
                argv = sys.argv
                try:
                    sys.argv = ['']
                    p = Process(target=monitorForCrash, args=(pid, child_conn))
                    p.start()
                finally:
                    # Restore the original sys.argv
                    sys.argv = argv
            else:
                self.crashMonitor = False
                _LOGGER.warning(
                    'blur.Stone or psutil not installed, crashMonitor disabled.'
                )

    def dirname(self):
        return self._dirname

    def makeTempDirectory(self, *args, **kwargs):
        """Creates a temporary directory and returns its file path.

        This directory and all of its contents are removed on exit.
        args and kwargs are passed to tempfile.NamedTemporaryFile after the
        "key" kwarg has been removed. If dir is not provided in kwargs and
        self._dirname is set, it will be added to kwargs.

        Args:
            key(str): If in keyed mode only one directory will be created
                for any key value. Any future calls to this function with
                the same key will return the same directory. If keyed is
                False, this will always return a new directory name. The
                default key is 'default'.

        Returns:
            str: The full path to the temporary directory.
        """
        if self.keyed:
            key = kwargs.pop('key', 'default')
        else:
            # This is not keyed, so generate a new key each time its called
            key = len(self._tempDirs)

        if key not in self._tempDirs:
            # If a dirname was provided, make sure its included
            if self._dirname is not None and 'dir' not in kwargs:
                kwargs['dir'] = self._dirname
                _LOGGER.info(
                    'makeTempDirectory adding dirname {}'.format(self._dirname)
                )

            tempDir = tempfile.mkdtemp(*args, **kwargs)
            self._tempDirs[key] = tempDir
            if self.crashMonitor:
                self.pipe.send(('tempDir', tempDir))
        return self._tempDirs[key]

    def makeTempFile(self, *args, **kwargs):
        """Creates a tempfile using tempfile.mkstemp and returns the path to the file.

        This file will only be valid till the context exits. Any args and kwargs are
        passed to tempfile.mkstemp after any extra keyword arguments are removed from
        kwargs. If dir is not provided in kwargs and self.dirname is set, it will be
        added to kwargs.

        Args:
            key(str): If in keyed mode only one directory will be created for any key
                value. Any future calls to this function with the same key will return
                the same directory. If keyed is False, this will always return a new
                directory name. Must be a keyword argument, defaults to 'default'.
            closeHandle (bool, optional): If True, the file handle created by mkstemp
                is immediately closed so the file is unlocked for other processes to
                modify. This will be removed when the context exits. Must be a keyword
                argument, defaults to False.

        Returns:
            str: the full path to the temporary file.
        """
        if self.keyed:
            key = kwargs.pop('key', 'default')
        else:
            # This is not keyed, so generate a new key each time its called
            key = len(self._tempFiles)

        closeHandle = kwargs.pop('closeHandle', False)

        if key not in self._tempFiles:
            # If a dirname was provided, make sure its included
            if self._dirname is not None:
                _LOGGER.info('DEFAULT DIR {}'.format([self._dirname, kwargs]))
                if 'dir' not in kwargs:
                    kwargs['dir'] = self._dirname
                    _LOGGER.info('makeTempFile adding dirname {}'.format(self._dirname))

            tempFile = tempfile.mkstemp(*args, **kwargs)
            self._tempFiles[key] = tempFile
            if self.crashMonitor:
                self.pipe.send(('tempFile', tempFile[1]))
            if closeHandle:
                os.close(tempFile[0])
        return self._tempFiles[key][1]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # If using the environment variable to keep files around, log some useful
        # debug info and exit without removing the files.
        if self.keepTempFiles:
            from pprint import pformat

            _LOGGER.info('\nBDEV_KEEP_TEMPFILESCONTEXT is True, keeping temp files.')
            _LOGGER.info('--- Orphaned Directories:')
            _LOGGER.info(pformat(self._tempDirs))
            _LOGGER.info('--- Orphaned Files:')
            _LOGGER.info(pformat(self._tempFiles))
            return
        # Remove any created folders from disk and their contents
        for tempDir in self._tempDirs.values():
            shutil.rmtree(tempDir)
        self._tempDirs = {}
        # Remove any created temp files
        for tempFile in self._tempFiles.values():
            _LOGGER.debug("tempFile removed: {}".format(tempFile))
            try:
                os.close(tempFile[0])
            except OSError as e:
                _LOGGER.warning('Problem closing tempfile, {}'.format(e))
            try:
                os.remove(tempFile[1])
            except OSError as e:
                if e.errno == errno.ENOENT:
                    _LOGGER.info('File already deleted {}'.format(e))
        self._tempFiles = {}
        if self.crashMonitor:
            # Tell the crashMonitor that the temp files have been deleted and it can
            # just exit
            self.pipe.send(('finished', ''))
            self.pipe.close()


class ErrorReport(object):
    """Allows you to provide additional debug info if a error happens in this context.

    The blurdev Python Logger can send a error email when any python error is raised.
    Sometimes just a traceback does not provide enough information to debug the
    traceback. This class allows you to provide additional information to the error
    report only if it is generated. For example if your treegrunt environment does not
    have a email setup, or the current debug level is not set to Disabled.

    ErrorReport can be used as a with context, or as a function decorator.

    Examples:
        This example shows a class using both the with context and a decorated method.

        from blurdev.contexts import ErrorReport
        class Test(object):
            def __init__(self):
                self.value = None
            def errorInfo(self):
                # The text returned by this function will be included in the error email
                return 'Info about the Test class: {}'.format(self.value)
            def doStuff(self):
                with ErrorReport(self.errorInfo, 'Test.doStuff'):
                    self.value = 'doStuff'
                    raise RuntimeError("BILL")
            @ErrorReport(errorInfo, 'Test.doMoreStuff')
            def doMoreStuff(self):
                self.value = 'doMoreStuff'
                raise RuntimeError("BOB")

    Using this class does not initialize the Python Logger, so you don't need to worry
    if your class is running headless and not use this class. However unless you set up
    your own error reporting system the callbacks will not be called and nothing will be
    reported.

    If you want to set up your own error reporting system you need to set
    `ErrorReport.enabled = True`. Then you will need to call ErrorReport.clearReports()
    any time excepthook is called. This prevents a buildup of all error reports any time
    a exception occurs. It should always be in place when you set enabled == True to
    prevent wasting memory. Calling ErrorReport.generateReport() will return the info
    you should include in your report. Calling generateReport is optional, but must be
    called before calling clearReports.

    Args:
        callback (function): If a exception happens this function is called and its
            returned value is added to the error email if sent. No arguments are passed
            to this function and it is expected to only return a string.
        title (str, optional): This short string is added to the title of the
            ErrorReport.
    Attributes:
        enabled (bool): If False(the default), then all callbacks are cleared even if
            there is a exception. This is used to prevent these functions from leaking
            memory if there isn't a excepthook calling clearReports.
    """

    __reports__ = []
    enabled = False

    def __init__(self, callback, title=''):
        self._callback = callback
        self._title = title

    def __call__(self, funct):
        def wrapper(wrappedSelf, *args, **kwargs):
            unbound = self._callback
            self._callback = self._callback.__get__(wrappedSelf)
            try:
                with self:
                    return funct(wrappedSelf, *args, **kwargs)
            finally:
                self._callback = unbound

        return wrapper

    def __enter__(self):
        type(self).__reports__.append((self._title, self._callback))

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If exc_type is None, then no exception was raised, so we should remove the
        # callback. If cls.enabled is False, then nothing has set itself up to call
        # clearReports. We need to remove the callback so it doesn't stay in memory.
        if exc_type is None or not type(self).enabled:
            type(self).__reports__.remove((self._title, self._callback))

    @classmethod
    def clearReports(cls):
        """Removes all of the currently stored callbacks.

        This should be called after all error reporting is finished, or if a error
        happened and there is nothing to report it. If you set cls.enabled to True,
        something in excepthook should call this to prevent keeping refrences to
        functions from staying in memory.
        """
        cls.__reports__ = []

    @classmethod
    def generateReport(cls, fmt='{result}'):
        """Executes and returns all of the currently stored callbacks.
        Args:

            ftm (str, Optional): The results of the callbacks will be inserted into this
                string using str.format into {results}.
        Returns:
            list: A list of tuples for all active ErrorReport classes. The tuples
                contain two strings; the title string, and result of the passed in
                callback function.
        """
        ret = []
        for title, callback in cls.__reports__:
            result = callback()
            ret.append((title, fmt.format(result=result)))
        return ret
