##
# 	\namespace	python.blurdev.decorators
#
# 	\remarks	Defines some deocrators that are commonly useful
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		03/23/11
#

from blurdev import debug


def abstractmethod(function):
    """
        \remarks	This method should be overidden in a subclass. If it is not, a message will be printed in Medium debug, 
                    and a exception will be thrown in high debug.
    """

    def newFunction(*args, **kwargs):
        # when debugging, raise an error
        if debug.isDebugLevel(debug.DebugLevel.High):
            raise NotImplementedError(
                debug.debugObjectString(
                    function, 'Abstract implementation is not implemented.'
                )
            )
        else:
            debug.debugObject(
                function,
                'Abstract implementation is not implemented',
                debug.DebugLevel.Mid,
            )
        return function(*args, **kwargs)

    newFunction.__name__ = function.__name__
    newFunction.__doc__ = function.__doc__
    newFunction.__dict__ = function.__dict__
    return newFunction


def pendingdeprecation(args):
    msg = 'This method is depricated and will be removed in the future.'
    if isinstance(args, str):
        msg = '%s %s' % (msg, args)

    def deco(function):
        """
            \Remarks	This decorator is used to warn that a api call will be depricated at a future date.
        """

        def newFunction(*args, **kwargs):
            if debug.isDebugLevel(debug.DebugLevel.High):
                raise PendingDeprecationWarning(debug.debugObjectString(function, msg))
            else:
                debug.debugObject(function, msg, debug.DebugLevel.Low)
            return function(*args, **kwargs)

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        newFunction.__dict__ = function.__dict__
        return newFunction

    if not isinstance(args, str):
        return deco(args)

    return deco


def stopwatch(text='', debugLevel=debug.DebugLevel.Low):
    r"""
        \remarks	Generate a blurdev.debug.Stopwatch that tells how long it takes the decorated function to run.
        \param		text	<str>||<function>	Message text, or no arguments
        \param		debugLevel	<blurdev.debug.DebugLevel>
    """
    msg = text
    if hasattr(text, '__call__'):
        msg = ''

    def deco(function):
        """
            \Remarks	This decorator is used to warn that a api call will be depricated at a future date.
        """
        nMsg = function.__name__
        if debugLevel:
            nMsg = '[%s] %s' % (debug.DebugLevel.labelByValue(debugLevel), nMsg)
        if msg:
            nMsg += ' %s' % msg

        def newFunction(*args, **kwargs):
            watch = debug.Stopwatch(nMsg, debugLevel)
            output = function(*args, **kwargs)
            watch.stop()
            return output

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        newFunction.__dict__ = function.__dict__
        return newFunction

    if hasattr(text, '__call__'):
        return deco(text)
    return deco
