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
import datetime
import inspect

from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QMessageBox

import blurdev
from .enum import enum

_currentLevel = int(os.environ.get('BDEV_DEBUG_LEVEL', '0'))
_debugLogger = None
_errorReport = []

DebugLevel = enum('Low', 'Mid', 'High')


class Stopwatch(object):
    def __init__(self, name, debugLevel=1):
        super(Stopwatch, self).__init__()
        self._name = str(name)
        self._count = 0
        self._debugLevel = debugLevel
        self._lapStack = []
        self.reset()

    def newLap(self, message):
        """ Convenience method to stop the current lap and create a new lap """
        self.stopLap()
        self.startLap(message)

    def reset(self):
        self._starttime = datetime.datetime.now()
        self._laptime = None
        self._records = []
        self._laps = []

    def startLap(self, message):
        if _currentLevel < self._debugLevel:
            return False
        self._lapStack.append((message, datetime.datetime.now()))
        return True

    def stop(self):
        if _currentLevel < self._debugLevel:
            return False

        # pop all the laps
        while self._lapStack:
            self.stopLap()

        ttime = str(datetime.datetime.now() - self._starttime)

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

        curr = datetime.datetime.now()
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
