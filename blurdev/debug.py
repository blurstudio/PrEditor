##
# 	\namespace	blurdev.debug
#
# 	\remarks	Handles the debugging system for the blurdev package
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/09/10
#

from enum import enum

_currentLevel = 0

DebugLevel = enum('Low', 'Mid', 'High')


def debugMsg(msg, level=2):
    """
        \remarks	Prints out a debug message to the stdout if the inputed level is greater than or equal to the current debugging level
        \param		msg		<str>						message to output
        \param		level	<DebugLevel>				debug level
        \return		<void>
    """
    if level <= debugLevel():
        print 'DEBUG (L%i) : %s' % (level, msg)


def debugObject(object, msg, level=2):
    """
        \remarks	Usees the debugMsg function to output to the stdout a debug message including the reference of where the object calling the method is located
        
        \sa			debugMsg
        
        \param		object		<module> || <class> || <method> || <function>
        \param		msg			<str>
        \param		level		<DebugLevel>
        
        \return		<void>
    """
    import inspect

    # debug a module
    if inspect.ismodule(object):
        debugMsg('[%s module] :: %s' % (object.__name__, msg), level)

    # debug a class
    elif inspect.isclass(object):
        debugMsg(
            '[%s.%s class] :: %s' % (object.__module__, object.__name__, msg), level
        )

    # debug an instance method
    elif inspect.ismethod(object):
        debugMsg(
            '[%s.%s.%s method] :: %s'
            % (
                object.im_class.__module__,
                object.im_class.__name__,
                object.__name__,
                msg,
            ),
            level,
        )

    # debug a function
    elif inspect.isfunction(object):
        debugMsg(
            '[%s.%s function] :: %s' % (object.__module__, object.__name__, msg), level
        )


def debugStubMethod(object, msg, level=2):
    """
        \remarks	Uses the debugObject function to display that a stub method has not been provided functionality
        
        \sa			debugObject
        
        \param		object		<function> || <method>
        \param		msg			<str>
        \param		level		<DebugLevel>
        
        \return		<void>
    """
    debugObject(object, 'Missing Functionality: %s' % msg, level)


def debugVirtualMethod(cls, object):
    """
        \remarks	Uses the debugObject function to display that a virtual function has not been overloaded
        
        \sa			debugObject
        
        \param		cls			<class>						base class where the method is defined
        \param		object		<function> || <method>
    """
    debugObject(
        object, 'Virtual method has not been overloaded from %s class' % cls.__name__
    )


def debugLevel():
    return _currentLevel


def isDebugLevel(level):
    """
        \remarks	Checks to see if the current debug level greater than or equal to the inputed level
        \param		level		<DebugLevel> || <str> || <QString>
        \return		<boolean> success
    """
    from PyQt4.QtCore import Qt, QString

    if type(level) in (str, QString):
        level = DebugLevel.value(str(level))

    return level <= debugLevel()


def setDebugLevel(level):
    """
        \remarks	Sets the debug level for the blurdev system module
        \param		level		<DebugLevel> || <str> || <QString>
        \return		<bool> success
    """
    from PyQt4.QtCore import QString

    global _currentLevel

    # clear the debug level
    if not level:
        import blurdev

        blurdev.core.debugLevelChanged.emit()
        _currentLevel = 0
        return True

    # check for the debug value if a string is passed in
    if type(level) in (str, QString):
        level = DebugLevel.value(str(level))

    # assign the debug flag
    if DebugLevel.isValid(level):
        _currentLevel = level
        import blurdev

        blurdev.core.debugLevelChanged.emit()
        return True
    else:
        debugObject(setDebugLevel, '%s is not a valid <DebugLevel> value' % level)
        return False
