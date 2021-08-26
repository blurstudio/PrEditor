"""
Defines some deocrators that are commonly useful


"""

from __future__ import absolute_import
from blurdev import debug
from Qt.QtCore import QObject, QTimer
import os
from Qt import QtCompat


def abstractmethod(function):
    """
        \remarks    This method should be overidden in a subclass. If it is not, a
                    message will be printed in Medium debug, and a exception will be
                    thrown in high debug.
    """

    def newFunction(*args, **kwargs):
        debug.debugObject(
            function,
            'Abstract implementation is not implemented',
            debug.DebugLevel.High,
        )
        return function(*args, **kwargs)

    newFunction.__name__ = function.__name__
    newFunction.__doc__ = function.__doc__
    newFunction.__dict__ = function.__dict__
    return newFunction


class EnvironmentVariable(object):
    """ Update environment variable only while this context/decorator is active.

    Args:
        key (str): The environment variable key.
        value (str or None, optional): The value to store for key. If None,
            the variable is removed from os.environ
    """

    def __init__(self, key, value):
        self.current = None
        self.key = key
        self.value = value

    def __call__(self, function):
        def wrapper(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        wrapper.__dict__ = function.__dict__
        return wrapper

    def __enter__(self):
        self.current = os.environ.get(self.key)
        if self.value is None:
            if self.key in os.environ:
                del os.environ[self.key]
        else:
            os.environ[self.key] = self.value

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.current is None:
            if self.key in os.environ:
                del os.environ[self.key]
        else:
            os.environ[self.key] = self.current


# {{{ http://code.activestate.com/recipes/577817/ (r1)
"""
A profiler decorator.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""
try:
    import cProfile
    import pstats

    def profile(
        sort='cumulative',
        lines=50,
        strip_dirs=False,
        fileName=r'c:\temp\profile.profile',
        acceptArgs=True,
    ):
        """
        A decorator which profiles a callable using cProfile

        :param sort: sort by this column. defaults to cumulative.
        :param lines: limit output to this number of lines. Defaults to 50.
        :param strip_dirs: If False the full path to files will be shown. Defaults to
            False.
        :param fileName: The name of the temporary file used to store the output for
            sorting.
        :param acceptArgs: Does the decorated function take args or kwargs? Mainly
                        used to fix issues with PyQt signals.

        :type sort: str
        :type lines: int
        :type strip_dirs: bool
        :type fileName: str
        :type acceptArgs: bool
        """

        def outer(fun):
            def inner(*args, **kwargs):
                prof = cProfile.Profile()
                if acceptArgs:
                    ret = prof.runcall(fun, *args, **kwargs)
                else:
                    ret = prof.runcall(fun, args[0])

                prof.dump_stats(fileName)
                stats = pstats.Stats(fileName)
                if strip_dirs:
                    stats.strip_dirs()
                if isinstance(sort, (tuple, list)):
                    stats.sort_stats(*sort)
                else:
                    stats.sort_stats(sort)
                stats.print_stats(lines)
                return ret

            return inner

        # in case this is defined as "@profile" instead of "@profile()"
        if hasattr(sort, '__call__'):
            fun = sort
            sort = 'cumulative'
            outer = outer(fun)
        return outer

    # end of http://code.activestate.com/recipes/577817/ }}}
except ImportError:

    def profile(
        sort='cumulative',
        lines=50,
        strip_dirs=False,
        fileName=r'c:\temp\profile.profile',
        acceptArgs=True,
    ):
        """
        A decorator which profiles a callable using profile. This is only used if
        cProfile is not available.

        :param sort: sort by this column. defaults to cumulative.
        :param lines: limit output to this number of lines. Defaults to 50.
        :param strip_dirs: If False the full path to files will be shown. Defaults to
            False.
        :param fileName: The name of the temporary file used to store the output for
            sorting.
        :param acceptArgs: Does the decorated function take args or kwargs? Mainly
                        used to fix issues with PyQt signals.

        :type sort: str
        :type lines: int
        :type strip_dirs: bool
        :type fileName: str
        :type acceptArgs: bool
        """

        def outer(fun):
            def inner(*args, **kwargs):
                debug.debugMsg(
                    'cProfile is unavailable in this version of python. '
                    'Use Python 2.5 or later.'
                )
                if acceptArgs:
                    return fun(*args, **kwargs)
                else:
                    return fun(args[0])

            return inner

        # in case this is defined as "@profile" instead of "@profile()"
        if hasattr(sort, '__call__'):
            fun = sort
            sort = 'cumulative'
            outer = outer(fun)
        return outer


def pendingdeprecation(args):
    """
    Used to mark method or function as pending deprecation.  When the
    decorated object is called, it will generate a pending deprecation warning.

    :param message: optional message text
    :type message: str

    """
    msg = 'This method is depricated and will be removed in the future.'
    if isinstance(args, str):
        msg = '%s %s' % (msg, args)

    def deco(function):
        """This decorator is used to warn that a api call will be
        depricated at a future date.
        """

        def newFunction(*args, **kwargs):
            debug.debugObject(function, msg, debug.DebugLevel.Low)
            return function(*args, **kwargs)

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        newFunction.__dict__ = function.__dict__
        return newFunction

    if not isinstance(args, str):
        return deco(args)

    return deco


def stopwatch(
    text='', debugLevel=debug.DebugLevel.Low, acceptArgs=True, useClock=False
):
    """ Generate a stopwatch you can use to time code execution time.

    Generate a blurdev.debug.Stopwatch that tells how long it takes the
    decorated function to run.  You can access the Stopwatch object by calling
    __stopwatch__ on the function object.  If you function is called
    slowFunction() inside the function you can call slowFunction.__stopwatch__
    If your function is part of a class, make sure to call
    self(self.slowFunction.__stopwatch__).

    Args: text (str): Optional message text. If blank it will use the name of the
        function. debugLevel (blurdev.debug.DebugLevel): DebugLevel the stopwatch will
        use to print messages. acceptArgs (bool): Does the decorated function take args
        or kwargs? Mainly used to fix issues with PyQt signals. Defaults to True.
        useClock (bool): Uses datetime.datetime.now for timing by default, if set to
        True, use time.clock. Use this if you need to time on smaller scales.

    Example:
        from blurdev.decorators import stopwatch
        @stopwatch
        def something():
            something.__stopwatch__.newLap('a lap')
            import time
            time.sleep(1)
            something.__stopwatch__.newLap('B lap')
            time.sleep(1)
    """
    msg = text
    if hasattr(text, '__call__'):
        msg = ''

    def deco(function):
        """
            \Remarks    This decorator is used to warn that a api call will be
            depricated at a future date.
        """
        nMsg = function.__name__
        if debugLevel:
            nMsg = '[%s] %s' % (debug.DebugLevel.labelByValue(debugLevel), nMsg)
        if msg:
            nMsg += ' %s' % msg

        def newFunction(*args, **kwargs):
            function.__stopwatch__ = debug.Stopwatch(
                nMsg, debugLevel, useClock=useClock
            )
            if acceptArgs:
                output = function(*args, **kwargs)
            else:
                output = function(args[0])
            function.__stopwatch__.stop()
            return output

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        newFunction.__dict__ = function.__dict__
        return newFunction

    if hasattr(text, '__call__'):
        return deco(text)
    return deco


class singleShot(QObject):  # noqa: N801
    """ Decorator class used to implement a QTimer.singleShot(0, function)

    # TODO: Pascal case this class name.

    This is useful so your refresh function only gets called once even if
    its connected to a signal that gets emitted several times at once.

    Note:
        While this will pass the args and kwargs of the first call in a
        event loop, it discards the args and kwargs of any additional
        calls to this function while in the same event loop.

    From the Qt Docs:
        As a special case, a QTimer with a timeout of 0 will time out as
        soon as all the events in the window system's event queue have
        been processed. This can be used to do heavy work while providing
        a snappy user interface
    """

    def __init__(self):
        super(singleShot, self).__init__()
        self._function = None
        self._callScheduled = False
        self._args = []
        self._kwargs = {}

    def __call__(self, function):
        self._function = function

        def newFunction(*args, **kwargs):
            if not self._callScheduled:
                self._args = args
                self._kwargs = kwargs
                self._callScheduled = True
                QTimer.singleShot(0, self.callback)

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        return newFunction

    def callback(self):
        """
        Calls the decorated function and resets singleShot for the next group of calls
        """
        self._callScheduled = False
        # self._args and self._kwargs need to be cleared before we call self._function
        args = self._args
        kwargs = self._kwargs
        self._args = []
        self._kwargs = {}
        if args:
            if not QtCompat.isValid(args[0]):
                debug.debugMsg(
                    '@singleShot: Qt Object is deleted, not calling {}'.format(
                        self._function.__name__
                    ),
                    debug.DebugLevel.High,
                )
                return
        self._function(*args, **kwargs)


class recursionBlock(object):  # noqa: N801
    """ Decorator that only allows the function to be processed every other call.

    # TODO: Pascal case this class name.

    Functions decorated with this are intended to do something that will result in
    the calling of this function again in a way that doesn't block signals.

    For	example when you use the callback of blurdev.gui.pyqtProcessInit to call a
    function that updates the widget stylesheet which triggers your callback, etc.
    In this case your function will always be called twice and this prevents the
    second call from executing.

    Note if the function call is blocked, this will not return anything.
    """

    def __init__(self):
        super(recursionBlock, self).__init__()
        self._block = False

    def __call__(self, function):
        def newFunction(*args, **kwargs):
            if self._block:
                self._block = False
                return
            self._block = True
            return function(*args, **kwargs)

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        return newFunction
