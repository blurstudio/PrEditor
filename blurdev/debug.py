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

from __future__ import print_function
from past.builtins import basestring
import datetime
import os
import sys
import time
import traceback
import weakref
import inspect

from collections import OrderedDict
from contextlib import contextmanager
from future.utils import with_metaclass

import blurdev
import blurdev.debug
from blurdev.contexts import ErrorReport
from deprecated import deprecated

from .enum import enum

_currentLevel = int(os.environ.get('BDEV_DEBUG_LEVEL', '0'))
_debugLogger = None
_errorReport = []

DebugLevel = enum('Low', 'Mid', 'High')


class _StopwatchMeta(type):

    """
    Metaclass that checks for passed Stopwatches and returns them if found,
    instead of creating a new one.
    """

    def __call__(cls, message, *args, **kwargs):
        """
        Check if a stopwatch has been passed and return it instead if found.

        Args:
            message (string): Name of stopwatch.
            *args:
            **kwargs:

        Returns:
            Stopwatch:
        """
        obj = kwargs.pop('obj', None)
        passed_only = kwargs.get('passed_only', False)

        # Try to get the calling object ourselves if not provided.
        if obj is None:
            fback = inspect.currentframe().f_back
            if fback is not None:
                flocals = fback.f_locals
                inst = flocals.get('self')
                name = fback.f_code.co_name
                if inst:
                    obj = getattr(inst, name)

        inst = None
        if obj:
            inst = cls._get_passed(obj)

        if not inst:
            kwargs['enabled'] = not passed_only and kwargs.get('enabled', True)
            inst = super(_StopwatchMeta, cls).__call__(message, *args, **kwargs)
        else:
            # Disable passed stopwatch lookup.
            kwargs['obj'] = 0

            inst = inst.new_lap(message, *args, **kwargs)

        return inst


class Stopwatch(with_metaclass(_StopwatchMeta, object)):

    """
    Tracks the total time from the creation of the Stopwatch till
    Stopwatch.stop is called.

    You can capture lap data as well, this allows you to time the total
    execution time but also check how long each section of code is taking.

    It also supports capturing lap data in loop structures, as well as the
    ability get either average, or total lap time. You can adjust how nested
    looped lap data is formated as well.

    Stopwatch also comes with convenience functions for managing start and stop
    of laps via decorators and contexts. You can also pass stopwatches around
    to allow for greater efficiency and cleaner results.

    While this class takes a blurdev.debug.DebugLevel param that prevent's the
    class from printing, and this class is designed to take as little time to
    run as possible, Stopwatch is a profiling class and should be removed from
    final code.

    Example::

        from blurdev.debug import Stopwatch


        class TestClass(object):

            # Decorating a method like this means that the stopwatch will be
            # started whenever the method is called, and stopped when it
            # returns. It also looks for any passed Stopwatches we want to use.
            @Stopwatch('TestClass.__init__', use_clock=True)
            def __init__(self, value):
                # This is how we access the decorator's stopwatch.
                sw = self.__init__.__stopwatch__

                # We create a new lap with a context. This way we are
                # guaranteed that any laps started in the loop will be
                # terminated on leaving the context.
                with sw.new_lap('Calculate total') as lap:
                    self.total = 0
                    for x in range(value):
                        # We create this lap to measure the average time of
                        # each loop. All children of this lap will also be
                        # averaged.
                        loop_lap = lap.new_lap('Iteration time')

                        loop_lap.new_lap('Print value')
                        print(x)

                        for y in range(5):
                            # We don't bother capturing the lap here.
                            loop_lap.start_lap('Multiply values')
                            self.total += x * y

            def get_total(self, *args):
                # We can define the stopwatch as a context.
                with Stopwatch("TestClass.get_total") as sw:
                    return self.total

            @classmethod
            def print_stuff(cls):
                # If we want to detect passed stopwatches in a classmethod,
                # staticmethod, or loose method, we must pass the object for
                # it to monitor for passed stopwatches.
                with Stopwatch("TestClass.print_stuff", obj=cls.print_stuff) as sw:
                    print("Bob")

        # Here is where we create our root Stopwatch. It will own all of our laps.
        sw = Stopwatch('Test watch')
        for x in range(100):
            lap = sw.new_lap('Loop init class')

            # We use a pass context to pass our lap to the TestClass's init method.
            with lap.pass_context(TestClass.__init__):
                t = TestClass(10)

            with lap.pass_context(t.get_total):
                print(t.get_total())

            with lap.pass_context(TestClass.print_stuff):
                t.print_stuff()

        sw.stop()

        # Will output (apart from the program's print statements):
        # DEBUG (Low) : time:0:00:03.371000 | Test watch Stopwatch
        # ------------------------------------------
        #   lap: 0:00:00.033670 | iterations: 100 | total: 0:00:03.367000 | Loop init
        #   class
        #   ------------------------------------------
        #     lap: 0:00:00.026820 | iterations: 100 | total: 0:00:02.682000 |
        #     TestClass.__init__
        #     ------------------------------------------
        #       lap: 0:00:00.026740 | iterations: 100 | total: 0:00:02.674000 |
        #       Calculate total
        #       ------------------------------------------
        #         lap: 0:00:00.002614 | iterations: 1000 | total: 0:00:02.614000 |
        #         Iteration time
        #         ------------------------------------------
        #           lap: 0:00:00.002602 | iterations: 1000 | total: 0:00:02.602000 |
        #           Print value
        #           lap: 0:00:00.000027 | iterations: 5000 | total: 0:00:00.135000 |
        #           Multiply values
        #     lap: 0:00:00.000030 | iterations: 100 | total: 0:00:00.003000 |
        #     TestClass.get_total
        #     lap: 0:00:00.002530 | iterations: 100 | total: 0:00:00.253000 |
        #     TestClass.print_stuff


    Attributes:
        message (string): Name of the stopwatch.
        indentation (int): How much to nested lap data will be indented.
    """

    def __init__(
        self,
        message,
        debug_level=1,
        use_clock=False,
        sstart=None,
        auto_start=True,
        indentation=2,
        obj=None,
        parent=None,
        stopwatch=None,
        passed_only=False,
        enabled=True,
        accept_args=True,
        **kwargs
    ):
        """
        Init method.

        Args:
            message (basestring): The log message related to this stopwatch.
            debug_level (blurdev.debug.DebugLevel: optional): Minimum debug
                level required to print this stopwatch
                Defaults to 1.
            use_clock (bool: optional): Uses datetime.datetime.now for timing
                by default, if set to True, use time.clock. Use this if you
                need to time on smaller scales.
            sstart (float, datetime.datetime, or None, optional): The timestamp
                to use as the start time. A value of None will result in the
                current time being used.
                Defaults to None.
            auto_start (bool, optional): Whether to start the Stopwatch
                immediately after initialization.
                Defaults to True.
            indentation (int, optional): How much to indent nested lap data.
                Defaults to 2.
            obj (callable, optional): Object to watch for for passed
                Stopwatches.
            parent (Stopwatch, optional): The stopwatch this belongs to.
                A value of None indicates that this is the root stopwatch.
                Defaults to None.
            stopwatch (Stopwatch, optional): The root stopwatch. Passing a
                value of None will result in the Stopwatch finding the root on
                its own.
                Defaults to None.
            passed_only (bool, optional): Whether the stopwatch should only run
                if a passed stopwatch was found.
                Defaults to False.
            enabled (bool, optional): Whether this stopwatch can run.
                Defaults to True.
            accept_args (bool, optional): Whether the function the stopwatch is
                decorating (if any) can accept kwargs.
            kwargs: Added to allow support for camelCase arguments. Remove when
                old methods are removed.
        """
        use_clock = kwargs.get('useClock', use_clock)
        debug_level = kwargs.get('debugLevel', debug_level)

        self.message = message
        self.indentation = indentation

        self._debug_level = debug_level
        self._parent = parent
        self._stopwatch = stopwatch
        self._use_clock = use_clock
        self._now = time.clock if use_clock else datetime.datetime.now
        self._useClock = use_clock
        self._enabled = enabled
        self._accept_args = accept_args

        self._iterations = []

        self._children = OrderedDict()
        self._running_children = OrderedDict()

        if self._stopwatch is None:
            stopwatch = self
            while stopwatch.parent():
                stopwatch = stopwatch.parent()

            self._stopwatch = stopwatch

        if auto_start:
            self.start(sstart)

    def __call__(self, func, accept_args=None):
        """
        Used to decorate methods, allowing the stopwatch to be started and
        stopped on method call and return.

        Args:
            func (callable): Function to decorate.
            accept_args (bool, optional): Whether the decorated function can
                take kwargs. If None is passed then uses the class's value.
                Defaults to None.

        Returns:
            object: Result of calling the decorated function.
        """
        accept_args = accept_args
        if accept_args is None:
            accept_args = self._accept_args
        is_classmethod = inspect.ismethod(func) and func.im_class is type

        def inner1(*args, **kwargs):
            stopwatch = self._get_passed(inner1)

            if inner1.__passed__:
                stopwatch = stopwatch.new_lap(self.message)
                inner1.__stopwatch__ = stopwatch
            else:
                stopwatch.start()

            try:
                output = self._inner(func, is_classmethod, accept_args, *args, **kwargs)
            finally:
                stopwatch.stop()

            return output

        # Stop the timer if autorun was on, and wait until the function is
        # actually called.
        self.reset()

        inner1.__stopwatch__ = self
        inner1.__passed__ = False
        orig_name = inner1.__name__
        inner1.__name__ = func.__name__
        inner1.__doc__ = func.__doc__
        inner1.__dict__.update(func.__dict__)
        inner1.__orig_func__ = func
        inner1.__orig_name__ = orig_name

        return inner1

    def __enter__(self):
        """
        Starts the stopwatch on enter.
        """
        if not self.running():
            self.start()
        return self

    def __exit__(self, type, value, traceback):
        """
        Stops the stopwatch on exit.
        """
        self.stop()

    def __str__(self):
        return self.format_lap()

    def average_elapsed(self):
        """
        Returns the average amount of time elapsed by the stopwatch over all
        iterations.

        If the timer was currently running, then stops the timer first.

        Returns:
            float or datetime.datetime:
        """
        total = self.total_elapsed()
        return total / len(self._iterations)

    def children(self):
        """
        Returns a list of all child Stopwatches.

        Returns:
            list:
        """
        return self._children.values()

    def debug_level(self):
        """
        Returns the minimum debug level.

        Returns:
            int: Debug level.
        """
        return self._debug_level

    def enabled(self, parent=None):
        """
        Returns whether this Stopwatch and it's children can run.

        Args:
            parent (Stopwatch or None, optional): Stopwatch to use as parent.
                If None is passed, then uses default parent.
                Defaults to None.

        Returns:
            bool:
        """
        if parent is None:
            parent = self.parent()

        self_enabled = self._enabled and _currentLevel >= self.debug_level()
        return self_enabled and (parent.enabled() if parent else True)

    def format_lap(self, depth=0, parent=None):
        """
        Formats and returns the stopwatch's time data as a string.

        Args:
            depth (int, optional): How many layers deep in the stopwatch
                heirarchy this is.
                Defaults to 0.

        Returns:
            string:
        """
        if not self.enabled():
            return ""

        total = self.total_elapsed()
        divisor = len(self._iterations)
        divisor = divisor if divisor else 1
        average = total / divisor
        elapsed = self._format_time(average)

        output = []
        tabbing = ' ' * depth * self.indentation
        message = self.message

        iter_info = ''
        if len(self._iterations) > 1:
            total_elapsed = self._format_time(total)
            iter_info = '| iterations: %s ' % (str(len(self._iterations)))
            iter_info += '| total: %s ' % (total_elapsed)

        # Stopwatch with no parent acts as the root stopwatch.
        if parent:
            msg = tabbing + 'lap: %s %s| %s' % (elapsed, iter_info, message)
            output.append(msg)
        else:
            msg = 'time:%s %s| %s Stopwatch' % (elapsed, iter_info, message)
            output.append(msg)

        # Include child stopwatches
        if self._children:
            msg = tabbing + '------------------------------------------'
            output.append(msg)
            for key, child in self._children.iteritems():
                output.append(child.format_lap(depth + 1, self))

        return '\n'.join(output)

    def new_lap(self, message, **kwargs):
        """
        Convenience method to stop the current child stopwatch and start a
        another child.

        Args:
            message (basestring): The log message related to the child.
            **kwargs: Keyword arguments to pass to new stopwatch.

        Returns:
            Stopwatch: Started child stopwatch.
        """
        sstart = kwargs.get('sstart')
        self.stop_lap(sstart)
        return self.start_lap(message, **kwargs)

    @deprecated(version='2.23.0', reason='Use new_lap instead.')
    def newLap(self, message):
        return self.new_lap(message)

    def parent(self):
        """
        Returns the parent stopwatch if any.

        Returns:
            Stopwatch or None:
        """
        return self._parent

    @contextmanager
    def pass_context(self, *args):
        """
        Context manager for managing the passing of a stopwatch to a function
        and handles the cleanup afterwards.

        Args:
            obj (object): Object that owns the function.
            func (string): Name of the function.

        Yields:
            callable: Original, unwrapped function.
        """
        if not self.enabled():
            yield args
            return

        orig_values = []
        for func in args:
            wrap_func = not hasattr(func, '__passed__')
            is_method = inspect.ismethod(func)

            if wrap_func and is_method:
                obj = func.__self__
                if obj is None:
                    obj = func.im_class
                setattr(obj, func.__name__, self.pass_to(func))
            elif not is_method:
                func.__dict__['__stopwatch__'] = self
            else:
                orig_values.append(
                    dict(
                        orig_passed=func.__dict__['__passed__'],
                        orig_stopwatch=func.__dict__['__stopwatch__'],
                    )
                )

                func.__dict__['__stopwatch__'] = self
                func.__dict__['__passed__'] = True

        try:
            yield args
        finally:
            for idx, func in enumerate(args):
                if wrap_func and is_method:
                    setattr(obj, func.__name__, func)
                elif not is_method:
                    del func.__dict__['__stopwatch__']
                else:
                    values = orig_values[idx]
                    func.__dict__['__passed__'] = values['orig_passed']
                    func.__dict__['__stopwatch__'] = values['orig_stopwatch']

    def pass_to(self, func, stopwatch=None, accept_args=None):
        """
        Wraps the function and passes it the stopwatch.

        Args:
            func (callable): Function to pass to.
            stopwatch (Stopwatch, optional): Stopwatch to pass. A value of None
                will result in this class being passed.
                Defaults to None.
            accept_args (bool, optional): Whether the decorated function can
                take kwargs. If None is passed then uses the class's value.
                Defaults to None.

        Returns:
            wrapped function:
        """
        accept_args = accept_args
        if accept_args is None:
            accept_args = self._accept_args
        is_classmethod = inspect.ismethod(func) and func.im_class is type

        def inner2(*args, **kwargs):
            return self._inner(func, is_classmethod, accept_args, *args, **kwargs)

        if stopwatch is None:
            stopwatch = self

        inner2.__stopwatch__ = stopwatch
        orig_name = inner2.__name__
        inner2.__name__ = func.__name__
        inner2.__doc__ = func.__doc__
        inner2.__dict__.update(func.__dict__)
        inner2.__orig_func__ = func
        inner2.__orig_name__ = orig_name

        return inner2

    def reset(self, sstart=None, auto_start=False):
        """
        Resets the stopwatch data to its initial values.

        Args:
            sstart (float, datetime.datetime, or None, optional): The timestamp
                to use as the start time. A value of None will result in the
                current time being used.
                Defaults to None.
            auto_start (bool, optional): Description
        """
        if self.running():
            self._add_end()

        self._iterations = []

        for child in self._children.values():
            child.reset()

        self._running_children = OrderedDict()

        if auto_start:
            self.start(sstart)

    def running(self):
        """
        Returns whether the stopwatch is currently running.

        Returns:
            bool:
        """
        if not self._iterations:
            return True

        iteration = self._iterations[-1]
        return 'end' not in iteration

    def running_laps(self):
        """
        Returns whether any child stopwatches are running.

        Returns:
            bool:
        """
        return len(self._running_children) > 0

    def set_enabled(self, state):
        """
        Sets whether this stopwatch and it's children can be run.

        Args:
            state (bool):
        """
        self._enabled = state

    def start(self, sstart=None):
        """
        Adds a start time to the lap. If the timer was currently running
        then it is ended and a new iteration begun.

        Args:
            sstart (float, datetime.datetime, or None, optional): The timestamp
                to use as the start time. A value of None will result in the
                current time being used.
                Defaults to None.
        """
        if not self.enabled():
            return

        if sstart is None:
            sstart = self._now()

        iteration = None
        if self._iterations:
            iteration = self._iterations[-1]

        if iteration and 'end' not in iteration:
            self._add_end(end=sstart, iteration=iteration)

        # Create new iteration
        iteration = {'start': sstart}
        self._iterations.append(iteration)

    def start_lap(self, message, **kwargs):
        """
        Starts and returns a child stopwatch. If this stopwatch is stopped, the
        child will be stopped as well.

        Args:
            message (basestring): The log message related to the child.
            kwargs: Keyword arguments to pass to new stopwatch.

        Returns:
            Stopwatch: Started child stopwatch.
        """
        if not self.running() and self.enabled():
            sstart = kwargs.get('sstart')
            self.start(sstart)

        if message not in self._children:

            kwargs['use_clock'] = kwargs.get('use_clock', self._useClock)
            kwargs['indentation'] = kwargs.get('indentation', self.indentation)
            kwargs['stopwatch'] = self._stopwatch
            kwargs['parent'] = self

            child = Stopwatch(message, **kwargs)
            self._children[message] = child
        else:
            sstart = kwargs.get('sstart')
            child = self._children[message]
            child.start(sstart)

        self._running_children[child.message] = child

        return child

    @deprecated(version='2.23.0', reason='Use start_lap instead.')
    def startLap(self, message):
        return self.start_lap(message)

    def stop(self, end=None):
        """
        Ends the stopwatch's timer. If this is the root stopwatch, then it also
        prints the debug.

        Args:
            end (float, datetime.datetime, or None, optional): The timestamp to
                use as the end time. A value of None will result in the current
                time being used.
                Defaults to None.

        Returns:
            bool: Whether the debug level was high enough to do anything.
        """
        if not self.enabled():
            return False

        self._add_end(end=end)

        if not self.parent():
            debugMsg(str(self) + '\n', self.debug_level())

        # Reset?

        return True

    def stop_lap(self, end=None):
        """
        Stops most recently running child stopwatch.

        Args:
            end (float, datetime.datetime, or None, optional): The timestamp to
                use as the end time. A value of None will result in the current
                time being used.
                Defaults to None.
        """
        if not self.enabled():
            return

        if not self._running_children:
            return

        while self._running_children:
            key = self._running_children.keys()[-1]
            child = self._running_children.pop(key)
            if child.running():
                child.stop(end)
                break

    @deprecated(version='2.23.0', reason='Use stop_lap instead.')
    def stopLap(self):
        return self.stop_lap()

    def stopwatch(self):
        """
        Returns the root stopwatch. Can be self.

        Returns:
            Stopwatch:
        """
        return self._stopwatch

    def total_elapsed(self):
        """
        Returns the total amount of time elapsed on the stopwatch over all
        iterations.

        If the timer was currently running, then stops the timer first.

        Returns:
            float or datetime.datetime:
        """
        # Stop timer if running.
        if self.running():
            self._add_end()

        # Calculate total from iterations.
        total = 0 if self._useClock else datetime.timedelta()
        for iteration in self._iterations:
            total += iteration['total']

        return total

    def _inner(self, func, is_classmethod, accept_args, *args, **kwargs):
        """
        Method used by class's decorator style functions.

        Args:
            func (callable): Function being decorated.
            is_classmethod (bool): Whether the function is a classmethod.
            accept_args (bool): Whether the function can accept kwargs.
            *args: Positional arguments to pass to function.
            **kwargs: Keyword arguments to pass to function.

        Returns:
            value: Result from calling decorated function.
        """
        if is_classmethod:
            args = list(args)[1:]

        if accept_args:
            return func(*args, **kwargs)
        else:
            return func(args[0])

    def _add_end(self, end=None, iteration=None):
        """
        If the lap is currently running, then stops it and adds the end
        time, otherwise nothing happens. Any children that are running will
        also be stopped.

        Args:
            end (float, datetime.datetime, or None, optional): The timestamp to
                use as the end time. A value of None will result in the current
                time being used.
                Defaults to None.
            iteration (dict, optional): Container for data about the current
                iteration. A value of None will result in the latest iteration
                being used.
                Defaults to None.
        """
        if end is None:
            end = self._now()

        # End children
        for key, child in self._running_children.iteritems():
            if child.running():
                child.stop(end)
        self._running_children = OrderedDict()

        if not self._iterations:
            return

        if iteration is None:
            iteration = self._iterations[-1]

        if 'end' in iteration:
            return

        start = iteration.get('start', end)
        iteration['start'] = start
        iteration['end'] = end
        iteration['total'] = end - start

    def _format_time(self, elapsed):
        """
        Converts the time into the proper string format.

        Args:
            elapsed (float, datetime.datetime): Time to format.

        Returns:
            string: Formatted time.
        """
        elapsed = str(elapsed)
        if '.' not in elapsed:
            elapsed += '.'

        while len(elapsed) < 14:
            elapsed += '0'

        return elapsed

    @classmethod
    def _get_passed(cls, obj):
        """
        Retrieves any passed stopwatch, else returns None.

        Args:
            obj (callable): Object the stopwatch was passed to.

        Returns:
            Stopwatch or None:
        """
        if obj is not None:
            if not hasattr(obj, '__orig_name__') and inspect.ismethod(obj):
                parent = obj.__self__
                if parent:
                    obj = getattr(obj.__self__, obj.__name__)

            if hasattr(obj, '__stopwatch__'):
                stopwatch = obj.__stopwatch__

                return stopwatch


class FileLogger:
    def __init__(self, stdhandle, logfile, _print=True, clearLog=True):
        self._stdhandle = stdhandle
        self._logfile = logfile
        self._print = _print
        if clearLog:
            # clear the log file
            self.clear()

    def clear(self, stamp=False):
        """ Removes the contents of the log file.
        """
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


def logToFile(path, stdout=True, stderr=True, useOldStd=False, clearLog=True):
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

        clearLog (bool): If True(default) clear the log file when this command is
        called.
    """
    if stderr:
        sys.stderr = FileLogger(sys.stderr, path, useOldStd, clearLog=clearLog)
    if stdout:
        sys.stdout = FileLogger(sys.stdout, path, useOldStd, clearLog=False)
        if clearLog:
            sys.stdout.clear(stamp=True)


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

        - *`send_sentry_event`*
            reports exception to on-premise Sentry server for debug triage.

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
        self.actions = dict(email=True, prompt=not blurdev.core.headless, sentry=True)

    def __call__(self, *exc_info):
        """
        Executes overriden execpthook.

        Checks the results from the core's `shouldReportException` function as
        to if the current exception should be reported. (Why? Nuke, for
        example, uses exceptions to signal tradionally non-exception worthy
        events, such as when a user cancels an Open File dialog window.)
        """
        self.actions = blurdev.core.shouldReportException(
            *exc_info, actions=self.actions
        )

        self.call_base_excepthook(exc_info)
        if debugLevel() == 0:
            self.send_sentry_event(exc_info)
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

    def send_sentry_event(self, exc_info):
        """
        Sends error to Sentry.

        If there is any issue importing Sentry's SDK package, fail silently and
        disable future reporting to Sentry.
        """
        if not self.actions.get("sentry", False):
            return

        try:
            import sentry_sdk
            import urllib3
        except ImportError:
            self.actions["sentry"] = False
            return

        # ignore warnings emitted by urllib3 library
        urllib3.disable_warnings()
        sentry_sdk.capture_exception(exc_info)

    def send_exception_email(self, exc_info):
        """
        Conditionally sends an exception email.
        """
        if not self.actions.get("email", False):
            return

        from blurdev.tools import ToolsEnvironment
        from blurdev.utils.error import ErrorEmail

        email_addresses = ToolsEnvironment.activeEnvironment().emailOnError()
        if email_addresses:
            mailer = ErrorEmail(*exc_info)
            mailer.send(email_addresses)

    def send_logger_error(self, exc_info):
        """
        Shows logger prompt.
        """
        if not self.actions.get("prompt", False):
            return

        from blurdev.gui.windows.loggerwindow import LoggerWindow
        from blurdev.gui.windows.loggerwindow.console import ConsoleEdit
        from blurdev.gui.windows.loggerwindow.errordialog import ErrorDialog
        import sip

        instance = LoggerWindow.instance()

        # logger reference deleted, fallback and print to console
        if sip.isdeleted(instance):
            print("[LoggerWindow] LoggerWindow object has been deleted.")
            print(traceback)
            return

        # logger is visble
        if instance.isVisible():
            instance.console().startInputLine()
            return

        # quiet mode active
        if blurdev.core.quietMode():
            return

        # error already prompted
        if ConsoleEdit._errorPrompted:
            return

        # Preemptively marking error as "prompted" (handled) to avoid errors
        # from being raised multiple times due to C++ and/or threading error
        # processing.
        try:
            ConsoleEdit._errorPrompted = True
            errorDialog = ErrorDialog(blurdev.core.rootWindow())
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
    """ Creates or returns a instance of pdb that works when normal pdb doesnt.

    The first time this is called it creates a pdb instance using PdbInput and PdbOutput
    for stdin and stdout. Any future calls to getPdb will return this same pdb. If pdb
    is activated, it will open the blurdev logger in a new instance of python using
    blurdev.external, all pdb output will be routed to this new logger. Commands typed
    in this logger will be passed back to this instance of pdb.

    Returns:
        pdb.Pdb: Special instance of pdb.
    """
    global _blurPdb
    if not _blurPdb:
        from blurdev.utils.pdbio import PdbInput, PdbOutput, BlurPdb

        # Skip these modules because they are not being debugged. Generally this needs
        # to ignore the Logger Window modules because printing causes the next function
        # to run into these making debugging annoying to say the least.
        skip = os.environ['BDEV_PDB_SKIP'].split(',')
        _blurPdb = BlurPdb(stdin=PdbInput(), stdout=PdbOutput(), skip=skip)
    return _blurPdb


def set_trace():
    """ Call getPdb().set_trace().

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
    """ Call getPdb().post_mortem().

    Enter post-mortem debugging of the given traceback object. If no traceback is given,
    it uses the exception that is currently being handled (for the default to be used,
    this function must be called from within the except of a try/except statement.)

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


def debugMsg(msg, level=2, fmt=None):
    """Prints out a debug message to the stdout if the inputed level is
    greater than or equal to the current debugging level

    Args: msg (str): message to output level (blurdev.debug.DebugLevel, optional):
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
    """ Uses :func:`debugMsg` to output to the stdout a debug message
    including the reference of where the object calling the method is located.

    Args: object (object): the object to include in the output message. msg (str):
        message to output level (blurdev.debug.DebugLevel, optional): Minimum DebugLevel
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
    """ Uses :func:`debugObject` to display that a stub method has not been provided
    functionality.

    Args:
        object (object): the object to include in the output message

        msg (str): message to output

        level (blurdev.debug.DebugLevel, optional): Minimum DebugLevel msg should be
            printed. Defaults to DebugLevel.Mid.
    """
    debugObject(object, 'Missing Functionality: %s' % msg, level)


def debugVirtualMethod(cls, object):
    """ Uses :func:`debugObject` to display that a virtual function has not been overloaded

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


def emailList():
    return blurdev.activeEnvironment().emailOnError()


def errorsReported():
    """ Returns whether or not the error report is empty

    Returns:
        bool:
    """
    return len(_errorReport) > 0


def isDebugLevel(level):
    """ Checks to see if the current debug level greater than or equal to the inputed level

    Args:
        level (blurdev.debug.DebugLevel):

    Returns
        bool: the current debug level is greater than or equal to level
    """
    if isinstance(level, basestring):
        level = DebugLevel.value(str(level))
    return level <= debugLevel()


def printCallingFunction(compact=False):
    """ Prints and returns info about the calling function

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
    """ Formats inspect.getmro into text.

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
    import inspect
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


def recycleGui(cls, *args, **kwargs):
    """ Closes the last gui of the provided class, suppressing any errors and returns
    a new instance of the class.

    Args:
        cls (class): the class of the object to create
        *args: additional arguments passed to the class
        **kwargs: additional keyword arguments passed to the class

    Returns:
        A new instance of the class
    """
    try:
        recycleGui._stored_().close()
    except Exception:
        pass
    out = cls(*args, **kwargs)
    recycleGui._stored_ = weakref.ref(out)
    return out


def reportError(msg, debugLevel=1):
    """ Adds the inputed message to the debug report

    Args:
        msg (str): the message to add to the debug report.

        debugLevel (blurdev.debug.DebugLevel, optional): Only adds msg to the debug
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
        from blurdev.gui.dialogs.detailreportdialog import DetailReportDialog

        DetailReportDialog.showReport(
            None, subject, message, '<br>'.join([str(r) for r in _errorReport])
        )
        return True


def setDebugLevel(level):
    """ Sets the debug level for the blurdev system module

    Args:
        level (blurdev.debug.DebugLevel): Value to set the debug level to.

    Returns:
        bool: The debug level was changed.
    """
    global _currentLevel

    # check for the debug value if a string is passed in
    if isinstance(level, basestring):
        try:
            # Check if a int value was passed as a string
            level = int(level)
        except ValueError:
            level = DebugLevel.value(str(level))

    # clear the debug level
    if not level:
        _currentLevel = 0
        if blurdev.core:
            blurdev.core.emitDebugLevelChanged()
        return True

    # assign the debug flag
    if DebugLevel.isValid(level):
        _currentLevel = level
        if blurdev.core:
            blurdev.core.emitDebugLevelChanged()
        return True
    else:
        debugObject(setDebugLevel, '%s is not a valid <DebugLevel> value' % level)
        return False
