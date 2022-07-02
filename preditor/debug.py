"""
.. warning::

   The python standard library provides a very powerful and flexible logging
   and debugging module --
   `logging <http://docs.python.org/library/logging.html>`_.

   Only use this module if you are updating an existing tool or library that
   uses it or is part of a larger blur system that uses it.

   If you are creating a new tool or library, use the
   `logging <http://docs.python.org/library/logging.html>`_ module in the
   standard library instead.

.. deprecated:: 2.0


The preditor debug module defines a handful of functions, as well as a single
enumerated type, and a single class, to help with the creation and printing
of logging messages.

The preditor debug module defines a single enumerated type -- :data:`DebugLevel`
-- that is used to discriminate between the various types of logging messages.

.. data:: DebugLevel

   An :class:`enum` used to set different levels of debugging.  Current
   values are Low, Medium, and High

"""

from __future__ import print_function
from __future__ import absolute_import
import datetime
import inspect
import os
import six
import sys
import traceback

from Qt import QtCompat

from . import core
from .contexts import ErrorReport
from .enum import enum

_currentLevel = int(os.environ.get('BDEV_DEBUG_LEVEL', '0'))
_debugLogger = None
_errorReport = []

DebugLevel = enum('Low', 'Mid', 'High')


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

    from pillar.streamhandler_helper import StreamHandlerHelper

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
        self.actions = core.shouldReportException(
            *exc_info, actions=self.actions
        )

        self.call_base_excepthook(exc_info)
        if debugLevel() == 0:
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

        from .utils.error import ErrorEmail

        email_addresses = os.getenv('BDEV_ERROR_EMAIL')
        if email_addresses:
            mailer = ErrorEmail(*exc_info)
            mailer.send(email_addresses)

    def send_logger_error(self, exc_info):
        """
        Shows logger prompt.
        """
        if not self.actions.get("prompt", False):
            return

        from .gui.loggerwindow import LoggerWindow
        from .gui.console import ConsoleEdit
        from .gui.errordialog import ErrorDialog

        instance = LoggerWindow.instance(create=False)

        if instance:
            # logger reference deleted, fallback and print to console
            if not QtCompat.isValid(instance):
                print("[LoggerWindow] LoggerWindow object has been deleted.")
                print(traceback)
                return

            # logger is visible
            if instance.isVisible():
                if instance.uiAutoPromptACT.isChecked():
                    instance.console().startInputLine()
                return

        # error already prompted
        if ConsoleEdit._errorPrompted:
            return

        # Preemptively marking error as "prompted" (handled) to avoid errors
        # from being raised multiple times due to C++ and/or threading error
        # processing.
        try:
            ConsoleEdit._errorPrompted = True
            errorDialog = ErrorDialog(core.rootWindow())
            errorDialog.setText(exc_info)
            errorDialog.exec_()

        # interruptted until dialog closed
        finally:
            ConsoleEdit._errorPrompted = False

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
# A pdb that works inside qt and softwares we run qt inside, like 3ds Max
_blurPdb = None


def getPdb():
    """Creates or returns a instance of pdb that works when normal pdb doesnt.

    The first time this is called it creates a pdb instance using PdbInput and PdbOutput
    for stdin and stdout. Any future calls to getPdb will return this same pdb. If pdb
    is activated, it will open preditor in a new instance of python using
    preditor.external, all pdb output will be routed to this new logger. Commands typed
    in this logger will be passed back to this instance of pdb.

    Returns:
        pdb.Pdb: Special instance of pdb.
    """
    global _blurPdb
    if not _blurPdb:
        from .utils.pdbio import PdbInput, PdbOutput, BlurPdb

        # Skip these modules because they are not being debugged. Generally this needs
        # to ignore the Logger Window modules because printing causes the next function
        # to run into these making debugging annoying to say the least.
        skip = os.environ['BDEV_PDB_SKIP'].split(',')
        _blurPdb = BlurPdb(stdin=PdbInput(), stdout=PdbOutput(), skip=skip)
    return _blurPdb


def set_trace():
    """Call getPdb().set_trace().

    Enter the debugger at the calling stack frame. This is useful to hard-code a
    breakpoint at a given point in a program, even if the code is not otherwise being
    debugged (e.g. when an assertion fails).
    """
    bPdb = getPdb()
    # Use the autoUp feature to step above the call to bPdb.set_trace so the user is at
    # the line that called this function, not inside this function.
    bPdb.stdin.setAutoUp(True)
    bPdb.set_trace()


def post_mortem(t=None):
    """Call getPdb().post_mortem().

    Enter post-mortem debugging of the given traceback object. If no traceback is given,
    it uses the exception that is currently being handled (for the default to be used,
    this function must be called from within the except of a try/except statement.)

    See Also:
        preditor.debug.pm()

    Args:
        t (traceback): exception to preform a post_mortem on.
    """
    # Copied from Python 2.7's pdb because post_mortem doesn't support custom pdb.
    # handling the default
    if t is None:
        # sys.exc_info() returns (type, value, traceback) if an exception is
        # being handled, otherwise it returns None
        t = sys.exc_info()[2]
        if t is None:
            raise ValueError(
                "A valid traceback must be passed if no " "exception is being handled"
            )

    p = getPdb()
    p.reset()
    p.interaction(None, t)


def pm():
    """Calls preditor.debug.post_mortem passing in sys.last_traceback."""
    post_mortem(sys.last_traceback)


# --------------------------------------------------------------------------------


def clearErrorReport():
    """Clears the current report"""
    global _errorReport
    _errorReport = []


def debugMsg(msg, level=2, fmt=None):
    """Prints out a debug message to the stdout if the inputed level is
    greater than or equal to the current debugging level

    Args: msg (str): message to output level (preditor.debug.DebugLevel, optional):
        Minimum DebugLevel msg should be printed. Defaults to DebugLevel.Mid. fmt (str
        or None, optional): msg is formatted with this string. Fills in {level} and
        {msg} args. If None, a default string is used.
    """
    if level <= debugLevel():
        if fmt is None:
            fmt = 'DEBUG ({level}) : {msg}'
        if callable(msg):
            msg = msg()
        print(fmt.format(level=DebugLevel.keyByValue(level), msg=msg))


def debugObject(object, msg, level=2, fmt=None):
    """Uses :func:`debugMsg` to output to the stdout a debug message
    including the reference of where the object calling the method is located.

    Args: object (object): the object to include in the output message. msg (str):
        message to output level (preditor.debug.DebugLevel, optional): Minimum DebugLevel
        msg should be printed. Defaults to DebugLevel.Mid. fmt (str or None, optional):
        msg is formatted with this string. Fills in {level} and {msg} args. If None, a
        default string is used.
    """
    debugMsg(lambda: debugObjectString(object, msg), level, fmt=fmt)


def debugObjectString(object, msg):
    import inspect

    # debug a module
    if inspect.ismodule(object):
        return '[%s module] :: %s' % (object.__name__, msg)

    # debug a class
    elif inspect.isclass(object):
        return '[%s.%s class] :: %s' % (object.__module__, object.__name__, msg)

    # debug an instance method
    elif inspect.ismethod(object):
        return '[%s.%s.%s method] :: %s' % (
            object.im_class.__module__,
            object.im_class.__name__,
            object.__name__,
            msg,
        )

    # debug a function
    elif inspect.isfunction(object):
        return '[%s.%s function] :: %s' % (object.__module__, object.__name__, msg)


def debugStubMethod(object, msg, level=2):
    """Uses :func:`debugObject` to display that a stub method has not been provided
    functionality.

    Args:
        object (object): the object to include in the output message

        msg (str): message to output

        level (preditor.debug.DebugLevel, optional): Minimum DebugLevel msg should be
            printed. Defaults to DebugLevel.Mid.
    """
    debugObject(object, 'Missing Functionality: %s' % msg, level)


def debugVirtualMethod(cls, object):
    """Uses :func:`debugObject` to display that a virtual function has not been overloaded

    Args:
        cls: the class object where the "virtual" method is defined
        object: the "virtual" method include in the output message
    """
    debugObject(
        object, 'Virtual method has not been overloaded from %s class' % cls.__name__
    )


def debugLevel():
    """Returns the current debugging level"""
    return _currentLevel


def errorsReported():
    """Returns whether or not the error report is empty

    Returns:
        bool:
    """
    return len(_errorReport) > 0


def isDebugLevel(level):
    """Checks to see if the current debug level greater than or equal to the inputed level

    Args:
        level (preditor.debug.DebugLevel):

    Returns
        bool: the current debug level is greater than or equal to level
    """
    if isinstance(level, six.string_types):
        level = DebugLevel.value(str(level))
    return level <= debugLevel()


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


def reportError(msg, debugLevel=1):
    """Adds the inputed message to the debug report

    Args:
        msg (str): the message to add to the debug report.

        debugLevel (preditor.debug.DebugLevel, optional): Only adds msg to the debug
            report if debugLevel is this level or higher. Defaults to DebugLevel.Low.
    """
    if isDebugLevel(debugLevel):
        _errorReport.append(str(msg))


def showErrorReport(
    subject='Errors Occurred',
    message='There were errors that occurred.  Click the Details button for more info.',
):
    if not errorsReported():
        from Qt.QtWidgets import QMessageBox

        QMessageBox.critical(None, subject, message)
    else:
        from .gui.dialogs.detailreportdialog import DetailReportDialog

        DetailReportDialog.showReport(
            None, subject, message, '<br>'.join([str(r) for r in _errorReport])
        )
        return True


def setDebugLevel(level):
    """Sets the debug level for the preditor system module

    Args:
        level (preditor.debug.DebugLevel): Value to set the debug level to.

    Returns:
        bool: The debug level was changed.
    """
    global _currentLevel

    # check for the debug value if a string is passed in
    if isinstance(level, six.string_types):
        try:
            # Check if a int value was passed as a string
            level = int(level)
        except ValueError:
            level = DebugLevel.value(str(level))

    # clear the debug level
    if not level:
        _currentLevel = 0
        return True

    # assign the debug flag
    if DebugLevel.isValid(level):
        _currentLevel = level
        return True
    else:
        debugObject(setDebugLevel, '%s is not a valid <DebugLevel> value' % level)
        return False
