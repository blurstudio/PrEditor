from __future__ import absolute_import, print_function

import datetime
import inspect
import logging
import sys
import traceback

from Qt import QtCompat

from . import core, root_window
from .contexts import ErrorReport

logger = logging.getLogger(__name__)


class FileLogger:
    def __init__(self, stdhandle, logfile, _print=True, clearLog=True):
        self._stdhandle = stdhandle
        self._logfile = logfile
        self._print = _print
        if clearLog:
            # clear the log file
            self.clear()

    def clear(self, stamp=False):
        """Removes the contents of the log file."""
        open(self._logfile, 'w').close()
        if stamp:
            msg = '--------- Date: {today} Version: {version} ---------'
            print(msg.format(today=datetime.datetime.today(), version=sys.version))

    def flush(self):
        self._stdhandle.flush()

    def write(self, msg):
        f = open(self._logfile, 'a')
        f.write(msg)
        f.close()
        if self._print:
            self._stdhandle.write(msg)


def logToFile(path, stdout=True, stderr=True, useOldStd=True, clearLog=True):
    """Redirect all stdout and/or stderr output to a log file.

    Creates a FileLogger class for stdout and stderr and installs itself in python.
    All output will be logged to the file path. Prints the current datetime and
    sys.version info when stdout is True.

    Args:
        path (str): File path to log output to.

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
        StreamHandlerHelper.replace_stream(sys.stdout._stdhandle, sys.stdout)
    if stderr:
        StreamHandlerHelper.replace_stream(sys.stderr._stdhandle, sys.stderr)


# --------------------------------------------------------------------------------


class BlurExcepthook(object):
    """
    Blur's excepthook override allowing for granular error handling
    customization.

    Stacked atop the standard library excepthook (by default), catches any
    unhandled exceptions and conditionally passes them to the following custom
    excepthooks:

        - *`call_base_excepthook`*
            excepthook callable supplied at initialization; if not supplied or
            invalid, executes standard library excepthook.

        - *`send_exception_email`*
            email notification.

        - *`send_logger_error`*
            logger console.

    Arguments:
        ehook (callable): An excepthook callable compatible with signature of
            sys.excepthook; defaults to original startup excepthook
    """

    def __init__(self, base_excepthook=None):
        self.base_excepthook = base_excepthook or sys.__excepthook__
        # We can't show the prompt if running headless.
        self.actions = dict(email=True, prompt=not core.headless)

    def __call__(self, *exc_info):
        """
        Executes overriden execpthook.

        Checks the results from the core's `shouldReportException` function as
        to if the current exception should be reported. (Why? Nuke, for
        example, uses exceptions to signal tradionally non-exception worthy
        events, such as when a user cancels an Open File dialog window.)
        """
        self.actions = core.shouldReportException(*exc_info, actions=self.actions)

        self.call_base_excepthook(exc_info)
        self.send_exception_email(exc_info)
        self.send_logger_error(exc_info)

        ErrorReport.clearReports()

    def call_base_excepthook(self, exc_info):
        """
        Process base excepthook supplied during object instantiation.

        A newline is printed pre-traceback to ensure the first line of output
        is not printed in-line with the prompt. This also provides visual
        separation between tracebacks, when recieved consecutively.
        """
        print("")
        try:
            self.base_excepthook(*exc_info)
        except (TypeError, NameError):
            sys.__excepthook__(*exc_info)

    def send_exception_email(self, exc_info):
        """
        Conditionally sends an exception email.
        """
        if not self.actions.get("email", False):
            return

        # email_addresses = os.getenv('BDEV_ERROR_EMAIL')
        # if email_addresses:
        #     from .utils.error import ErrorEmail
        #     mailer = ErrorEmail(*exc_info)
        #     mailer.send(email_addresses)

    def send_logger_error(self, exc_info):
        """
        Shows logger prompt.
        """
        if not self.actions.get("prompt", False):
            return

        from .gui.console import ConsolePrEdit
        from .gui.errordialog import ErrorDialog
        from .gui.loggerwindow import LoggerWindow

        instance = LoggerWindow.instance(create=False)

        if instance:
            # logger reference deleted, fallback and print to console
            if not QtCompat.isValid(instance):
                print("[LoggerWindow] LoggerWindow object has been deleted.")
                print(traceback)
                return

            # logger is visible and check if it was minimized on windows
            if instance.isVisible() and not instance.isMinimized():
                if instance.uiAutoPromptACT.isChecked():
                    instance.console().startInputLine()
                return

        # error already prompted
        if ConsolePrEdit._errorPrompted:
            return

        # Preemptively marking error as "prompted" (handled) to avoid errors
        # from being raised multiple times due to C++ and/or threading error
        # processing.
        try:
            ConsolePrEdit._errorPrompted = True
            errorDialog = ErrorDialog(root_window())
            errorDialog.setText(exc_info)
            errorDialog.exec_()

        # interruptted until dialog closed
        finally:
            ConsolePrEdit._errorPrompted = False

    @classmethod
    def install(cls, force=False):
        """
        Install Blur excepthook override, returing previously implemented
        excepthook function.

        Arguments:
            force (bool): force reinstallation of excepthook override when
                already previously implemented.

        Returns:
            func: pre-override excepthook function
        """
        ErrorReport.enabled = True
        prev_excepthook = sys.excepthook

        if not isinstance(prev_excepthook, BlurExcepthook) or force:
            sys.excepthook = cls(prev_excepthook)

        return prev_excepthook


# --------------------------------------------------------------------------------


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
