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


## {{{ http://code.activestate.com/recipes/577817/ (r1)
"""
A profiler decorator.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""
import cProfile
import tempfile
import pstats


def profile(
    sort='cumulative', lines=50, strip_dirs=False, fileName=r'c:\temp\profile.profile'
):
    """A decorator which profiles a callable. This uses cProfile which is not in Python2.4.
    Example usage:

    >>> @profile
        def factorial(n):
            n = abs(int(n))
            if n < 1:
                    n = 1
            x = 1
            for i in range(1, n + 1):
                    x = i * x
            return x
    ...
    >>> factorial(5)
    Thu Jul 15 20:58:21 2010    c:\temp\profile.profile

             4 function calls in 0.000 CPU seconds

       Ordered by: internal time, call count

        ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            1    0.000    0.000    0.000    0.000 profiler.py:120(factorial)
            1    0.000    0.000    0.000    0.000 {range}
            1    0.000    0.000    0.000    0.000 {abs}

    120
    >>>
    """

    def outer(fun):
        def inner(*args, **kwargs):
            prof = cProfile.Profile()
            ret = prof.runcall(fun, *args, **kwargs)

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


## end of http://code.activestate.com/recipes/577817/ }}}


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
                    You can access the Stopwatch object by calling __stopwatch__ on the function object.
                    If you function is called slowFunction() inside the function you can call slowFunction.__stopwatch__
                    If your function is part of a class, make sure to call self(self.slowFunction.__stopwatch__)
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
            function.__stopwatch__ = debug.Stopwatch(nMsg, debugLevel)
            output = function(*args, **kwargs)
            function.__stopwatch__.stop()
            return output

        newFunction.__name__ = function.__name__
        newFunction.__doc__ = function.__doc__
        newFunction.__dict__ = function.__dict__
        return newFunction

    if hasattr(text, '__call__'):
        return deco(text)
    return deco
