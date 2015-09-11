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


The blurdev debug module defines a handful of functions, as well as a single
enumerated type, and a single class, to help with the creation and printing
of logging messages.

The blurdev debug module defines a single enumerated type -- :data:`DebugLevel`
-- that is used to discriminate between the various types of logging messages.

.. data:: DebugLevel

   An :class:`enum` used to set different levels of debugging.  Current 
   values are Low, Medium, and High
   
"""

import os
import sys
import datetime
import time
import weakref

from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QMessageBox

import blurdev
from .enum import enum

_currentLevel = int(os.environ.get('BDEV_DEBUG_LEVEL', '0'))
_debugLogger = None
_errorReport = []

DebugLevel = enum('Low', 'Mid', 'High')


class Stopwatch(object):
    """ Tracks the total time from the creation of the Stopwatch till Stopwatch.stop is called.
    
    You can capture lap data as well, this allows you to time the total execution time but also
    check how long each section of code is taking. While this class takes a blurdev.debug.DebugLevel
    param that prevent's the class from printing, and this class is designed to take as little time
    to run as possible, Stopwatch is a profiling class and should be removed from final code.
    
    Example:
        from blurdev.enum import Enum, EnumGroup
        w = Stopwatch('EnumGroup', useClock=True)
        w.newLap('Creating Suit')
        class Suit(Enum): pass
        w.newLap('Creating Suits')
        class Suits(EnumGroup):
            Hearts = Suit(description='A Heart')
            Spades = Suit(description='A Spade', label='Spades Of Fun')
            Clubs = Suit(description='A Club')
            Diamonds = Suit()
        w.stop()
        
        # Will output
            DEBUG (Low) : time:0.00041085440651 | EnumGroup Stopwatch
            ------------------------------------------
                lap: 3.5837767546e-05 | Creating Suit
                lap: 0.000343445272316 | Creating Suits
    
    Args:
        name (str): The name of the stopwatch used in the final output
        debugLevel (blurdev.debug.DebugLevel): Minimum debug level required to print this stopwatch
        useClock (bool): Uses datetime.datetime.now for timing by default, if set to True, use
                    time.clock. Use this if you need to time on smaller scales.
    """

    def __init__(self, name, debugLevel=1, useClock=False):
        super(Stopwatch, self).__init__()
        self._name = str(name)
        self._count = 0
        self._debugLevel = debugLevel
        self._lapStack = []
        self._now = time.clock if useClock else datetime.datetime.now
        self.reset()

    def newLap(self, message):
        """ Convenience method to stop the current lap and create a new lap """
        self.stopLap()
        self.startLap(message)

    def reset(self):
        self._starttime = self._now()
        self._laptime = None
        self._records = []
        self._laps = []

    def startLap(self, message):
        if _currentLevel < self._debugLevel:
            return False
        self._lapStack.append((message, self._now()))
        return True

    def stop(self):
        if _currentLevel < self._debugLevel:
            return False

        # pop all the laps
        while self._lapStack:
            self.stopLap()

        ttime = str(self._now() - self._starttime)

        # output the logs
        output = ['time:%s | %s Stopwatch' % (ttime, self._name)]
        output.append('------------------------------------------')
        output += self._records
        output.append('')
        debugMsg('\n'.join(output), self._debugLevel)
        return True

    def stopLap(self):
        if not self._lapStack:
            return False

        curr = self._now()
        message, sstart = self._lapStack.pop()
        # process the elapsed time
        elapsed = str(curr - sstart)
        if '.' not in elapsed:
            elapsed += '.'

        while len(elapsed) < 14:
            elapsed += '0'

        # record a lap
        self._records.append('\tlap: %s | %s' % (elapsed, message))


class AdditionalErrorInfo(object):
    def __init__(self, message):
        """
        If a error happens in this context include this message inside the error report email.
        :param message: the text string to include in the error email
        """
        super(AdditionalErrorInfo, self).__init__()
        self.message = message

    def __enter__(self):
        blurdev.core.logger().uiConsoleTXT.setAdditionalInfo(self.message)

    def __exit__(self, type, value, traceback):
        blurdev.core.logger().uiConsoleTXT.resetAdditionalInfo()


class FileLogger:
    def __init__(self, stdhandle, logfile, _print=True):
        self._stdhandle = stdhandle
        self._logfile = logfile
        self._print = _print
        # clear the log file
        open(logfile, 'w').close()

    def flush(self):
        self._stdhandle.flush()

    def write(self, msg):
        f = open(self._logfile, 'a')
        f.write(msg)
        f.close()
        if self._print:
            self._stdhandle.write(msg)


def logToFile(path, stdout=True, stderr=True, useOldStd=False):
    """ Redirect all stdout and/or stderr output to a log file.
    
    Creates a FileLogger class for stdout and stderr and installs itself in python.
    All output will be logged to the file path. Prints the current datetime and
    sys.version info when stdout is True.
    
    Args:
        path (str): File path to log output to.
        stdout (bool): If True(default) override sys.stdout.
        stderr (bool): If True(default) override sys.stderr.
        useOldStd (bool): If True, messages will be written to the FileLogger
            and the previous sys.stdout/sys.stderr.
    """
    if stderr:
        sys.stderr = FileLogger(sys.stderr, path, useOldStd)
    if stdout:
        sys.stdout = FileLogger(sys.stdout, path, useOldStd)
        print '--------- Date: %s Version: %s ---------' % (
            datetime.datetime.today(),
            sys.version,
        )


# --------------------------------------------------------------------------------
# A pdb that works inside qt and softwares we run qt inside, like 3ds Max
_blurPdb = None


def getPdb():
    """ Creates or returns a instance of pdb that works when normal pdb doesnt.
    
    The first time this is called it creates a pdb instance using PdbInput and PdbOutput for stdin 
    and stdout. Any future calls to getPdb will return this same pdb. If pdb is activated, it will
    open the blurdev logger in a new instance of python using blurdev.external, all pdb output will 
    be routed to this new logger. Commands typed in this logger will be passed back to this instance 
    of pdb.
    
    Returns:
        pdb.Pdb: Special instance of pdb.
    """
    global _blurPdb
    if not _blurPdb:
        from blurdev.utils.pdbio import PdbInput, PdbOutput, BlurPdb

        # Skip these modules because they are not being debugged. Generally this needs to
        # ignore the Logger Window modules because printing causes the next function to run
        # into these making debugging annoying to say the least.
        skip = os.environ['BDEV_PDB_SKIP'].split(',')
        _blurPdb = BlurPdb(stdin=PdbInput(), stdout=PdbOutput(), skip=skip)
    return _blurPdb


def set_trace():
    """ Call getPdb().set_trace().
    
    Enter the debugger at the calling stack frame. This is useful to hard-code a breakpoint at a 
    given point in a program, even if the code is not otherwise being debugged (e.g. when an 
    assertion fails).
    """
    bPdb = getPdb()
    # Use the autoUp feature to step above the call to bPdb.set_trace so the user is at the line
    # that called this function, not inside this function.
    bPdb.stdin.setAutoUp(True)
    bPdb.set_trace()


def post_mortem(t=None):
    """ Call getPdb().post_mortem().
    
    Enter post-mortem debugging of the given traceback object. If no traceback is given, it uses the 
    exception that is currently being handled (for the default to be used, this function must be
    called from within the except of a try/except statement.)
    
    See Also:
        blurdev.debug.pm()
    
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
    """ Calls blurdev.debug.post_mortem passing in sys.last_traceback.
    """
    post_mortem(sys.last_traceback)


# --------------------------------------------------------------------------------


def clearErrorReport():
    """Clears the current report"""
    global _errorReport
    _errorReport = []


def debugMsg(msg, level=2):
    """
    Prints out a debug message to the stdout if the inputed level is 
    greater than or equal to the current debugging level
    
    :param msg: message to output
    :param level: debugLevel
    :type msg: str
    :type level: :data:`DebugLevel`
    
    """
    if level <= debugLevel():
        if callable(msg):
            msg = msg()
        print 'DEBUG (%s) : %s' % (DebugLevel.keyByValue(level), msg)


def debugObject(object, msg, level=2):
    """
    Uses :func:`debugMsg` to output to the stdout a debug message 
    including the reference of where the object calling the method is located.

    :param object: the object to include in the output message
    :param msg: message to output
    :param level: debugLevel
    :type msg: str
    :type level: :data:`DebugLevel`
    
    """
    debugMsg(lambda: debugObjectString(object, msg), level)


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
    """
    Uses :func:`debugObject` to display that a stub method has not 
    been provided functionality.

    :param object: the object to include in the output message
    :param msg: message to output
    :param level: debugLevel
    :type msg: str
    :type level: :data:`DebugLevel`
    """
    debugObject(object, 'Missing Functionality: %s' % msg, level)


def debugVirtualMethod(cls, object):
    """
    Uses :func:`debugObject` to display that a virtual function has not 
    been overloaded

    :param cls: the class object where the "virtual" method is defined
    :param object: the "virtual" method include in the output message
    
    """
    debugObject(
        object, 'Virtual method has not been overloaded from %s class' % cls.__name__
    )


def debugLevel():
    """Returns the current debugging level"""
    return _currentLevel


def emailList():
    return blurdev.activeEnvironment().emailOnError()


def errorsReported():
    """
    Returns whether or not the error report is empty

    :rtype: bool
    
    """
    return len(_errorReport) > 0


def isDebugLevel(level):
    """
    Checks to see if the current debug level greater than or equal to 
    the inputed level

    :param level: debugLevel
    :type level: :data:`DebugLevel`
    :rtype: bool
    
    """
    if isinstance(level, (basestring, QString)):
        level = DebugLevel.value(str(level))
    return level <= debugLevel()


def printCallingFunction(compact=False):
    """
    Prints and returns info about the calling function

    :param compact: If set to True, prints a more compact printout
    
    """
    import inspect

    current = inspect.currentframe().f_back
    try:
        parent = current.f_back
    except:
        print 'No Calling function found'
        return
    currentInfo = inspect.getframeinfo(current)
    parentInfo = inspect.getframeinfo(parent)
    if parentInfo[3] != None:
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
    print output
    return output


def recycleGui(cls, *args, **kwargs):
    """ Closes the last gui of the provided class, suppressing any errors and returns a new instance of the class.
    :param cls: the class of the object to create
    :param *args: additional arguments passed to the class
    :param **kwargs: additional keyword arguments passed to the class
    :returns: A new instance of the class
    """
    try:
        recycleGui._stored_().close()
    except:
        pass
    out = cls(*args, **kwargs)
    recycleGui._stored_ = weakref.ref(out)
    return out


def reportError(msg, debugLevel=1):
    """
    Adds the inputed message to the debug report

    :param level: debugLevel
    :type msg: str
    :type level: :data:`DebugLevel`

    """
    if isDebugLevel(debugLevel):
        _errorReport.append(str(msg))


def showErrorReport(
    subject='Errors Occurred',
    message='There were errors that occurred.  Click the Details button for more info.',
):
    if not errorsReported():
        QMessageBox.critical(None, subject, message)
    else:
        from blurdev.gui.dialogs.detailreportdialog import DetailReportDialog

        DetailReportDialog.showReport(
            None, subject, message, '<br>'.join([str(r) for r in _errorReport])
        )
        return True


def setDebugLevel(level):
    """
    Sets the debug level for the blurdev system module

    :param level: debugLevel
    :type level: :data:`DebugLevel`

    """
    global _currentLevel

    # clear the debug level
    if not level:
        _currentLevel = 0
        if blurdev.core:
            blurdev.core.emitDebugLevelChanged()
        return True

    # check for the debug value if a string is passed in
    if isinstance(level, (basestring, QString)):
        level = DebugLevel.value(str(level))

    # assign the debug flag
    if DebugLevel.isValid(level):
        _currentLevel = level
        if blurdev.core:
            blurdev.core.emitDebugLevelChanged()
        return True
    else:
        debugObject(setDebugLevel, '%s is not a valid <DebugLevel> value' % level)
        return False
