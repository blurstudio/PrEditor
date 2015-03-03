"""
Defines some deocrators that are commonly useful


"""

import traceback
from blurdev import debug


def abstractmethod(function):
    """
        \remarks	This method should be overidden in a subclass. If it is not, a message will be printed in Medium debug, 
                    and a exception will be thrown in high debug.
    """

    def newFunction(*args, **kwargs):
        debug.debugObject(
            function, 'Abstract implementation is not implemented', debug.DebugLevel.Mid
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
try:
    import cProfile
    import tempfile
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
        :param strip_dirs: If False the full path to files will be shown. Defaults to False.
        :param fileName: The name of the temporary file used to store the output for sorting.
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

    ## end of http://code.activestate.com/recipes/577817/ }}}
except ImportError:

    def profile(
        sort='cumulative',
        lines=50,
        strip_dirs=False,
        fileName=r'c:\temp\profile.profile',
        acceptArgs=True,
    ):
        """
        A decorator which profiles a callable using profile. This is only used if cProfile is not available.
            
        :param sort: sort by this column. defaults to cumulative.
        :param lines: limit output to this number of lines. Defaults to 50.
        :param strip_dirs: If False the full path to files will be shown. Defaults to False.
        :param fileName: The name of the temporary file used to store the output for sorting.
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
                    'cProfile is unavailable in this version of python. Use Python 2.5 or later.'
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

    Args:
        text (str): Optional message text. If blank it will use the name of the function.
        debugLevel (blurdev.debug.DebugLevel): DebugLevel the stopwatch will use to print messages.
        acceptArgs (bool): Does the decorated function take args or kwargs? Mainly
                    used to fix issues with PyQt signals. Defaults to True.
        useClock (bool): Uses datetime.datetime.now for timing by default, if set to True, use
                    time.clock. Use this if you need to time on smaller scales.
    
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
            \Remarks	This decorator is used to warn that a api call will be depricated at a future date.
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
