from __future__ import absolute_import, print_function

import logging

_LOGGER = logging.getLogger(__name__)


class ErrorReport(object):
    """Allows you to provide additional debug info if a error happens in this context.

    PrEditor can send a error email when any python error is raised.
    Sometimes just a traceback does not provide enough information to debug the
    traceback. This class allows you to provide additional information to the error
    report only if it is generated. For example if your treegrunt environment does not
    have a email setup, or the current debug level is not set to Disabled.

    ErrorReport can be used as a with context, or as a function decorator.

    Examples:
        This example shows a class using both the with context and a decorated method.

        from preditor.contexts import ErrorReport
        class Test(object):
            def __init__(self):
                self.value = None
            def errorInfo(self):
                # The text returned by this function will be included in the error email
                return 'Info about the Test class: {}'.format(self.value)
            def doStuff(self):
                with ErrorReport(self.errorInfo, 'Test.doStuff'):
                    self.value = 'doStuff'
                    raise RuntimeError("BILL")
            @ErrorReport(errorInfo, 'Test.doMoreStuff')
            def doMoreStuff(self):
                self.value = 'doMoreStuff'
                raise RuntimeError("BOB")

    Using this class does not initialize the Python Logger, so you don't need to worry
    if your class is running headless and not use this class. However unless you set up
    your own error reporting system the callbacks will not be called and nothing will be
    reported.

    If you want to set up your own error reporting system you need to set
    `ErrorReport.enabled = True`. Then you will need to call ErrorReport.clearReports()
    any time excepthook is called. This prevents a buildup of all error reports any time
    a exception occurs. It should always be in place when you set enabled == True to
    prevent wasting memory. Calling ErrorReport.generateReport() will return the info
    you should include in your report. Calling generateReport is optional, but must be
    called before calling clearReports.

    Args:
        callback (function): If a exception happens this function is called and its
            returned value is added to the error email if sent. No arguments are passed
            to this function and it is expected to only return a string.
        title (str, optional): This short string is added to the title of the
            ErrorReport.
    Attributes:
        enabled (bool): If False(the default), then all callbacks are cleared even if
            there is a exception. This is used to prevent these functions from leaking
            memory if there isn't a excepthook calling clearReports.
    """

    __reports__ = []
    enabled = False

    def __init__(self, callback, title=''):
        self._callback = callback
        self._title = title

    def __call__(self, funct):
        def wrapper(wrappedSelf, *args, **kwargs):
            unbound = self._callback
            self._callback = self._callback.__get__(wrappedSelf)
            try:
                with self:
                    return funct(wrappedSelf, *args, **kwargs)
            finally:
                self._callback = unbound

        return wrapper

    def __enter__(self):
        type(self).__reports__.append((self._title, self._callback))

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If exc_type is None, then no exception was raised, so we should remove the
        # callback. If cls.enabled is False, then nothing has set itself up to call
        # clearReports. We need to remove the callback so it doesn't stay in memory.
        if exc_type is None or not type(self).enabled:
            type(self).__reports__.remove((self._title, self._callback))

    @classmethod
    def clearReports(cls):
        """Removes all of the currently stored callbacks.

        This should be called after all error reporting is finished, or if a error
        happened and there is nothing to report it. If you set cls.enabled to True,
        something in excepthook should call this to prevent keeping refrences to
        functions from staying in memory.
        """
        cls.__reports__ = []

    @classmethod
    def generateReport(cls, fmt='{result}'):
        """Executes and returns all of the currently stored callbacks.
        Args:

            ftm (str, Optional): The results of the callbacks will be inserted into this
                string using str.format into {results}.
        Returns:
            list: A list of tuples for all active ErrorReport classes. The tuples
                contain two strings; the title string, and result of the passed in
                callback function.
        """
        ret = []
        for title, callback in cls.__reports__:
            result = callback()
            ret.append((title, fmt.format(result=result)))
        return ret
