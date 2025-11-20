import functools
import inspect
import logging
import threading

_logger = logging.getLogger(__name__)


class CallStack:
    """Decorator that logs the inputs and return of the decorated function.

    For most cases use `@preditor.utils.call_stack.log_calls`, but if you want
    to create a custom configured version you can create your own instance of
    `CallStack` to customize the output.

    Parameters:
        logger: A python logging instance to write log messages to.
        level: Write to logger using this debug level.
        print: If set to True use the print function instead of python logging.
        input_prefix: Text shown before the function name.
        return_prefix: Text shown before the return data.
    """

    def __init__(self, logger=None, level=logging.DEBUG, print=True):
        self._call_depth = threading.local()
        self.logger = _logger if logger is None else logger
        self.level = level
        self.print = print
        self.input_prefix = "\u2192"
        self.return_prefix = "\u2190"

    @property
    def indent(self):
        return getattr(self._call_depth, "indent", 0)

    @indent.setter
    def indent(self, indent):
        self._call_depth.indent = indent

    def log(self, msg):
        if self.print:
            print(msg)
        else:
            self.logger.log(self.level, msg, stacklevel=2)

    def log_calls(self, func):
        """Decorator that writes function input and return value.
        If another decorated function call is made during the first call it's
        output will be indented to reflect that.
        """
        # Check for and remove self and cls arguments once during decoration
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        slice_index = 1 if params and params[0].name in ("self", "cls") else 0

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # remove 'self' or 'cls' from positional display (but do NOT remove kwargs)
            # display_args = args[1:] if slice_index and args else args
            display_args = args[slice_index:]

            # Generate repr of the calling arguments
            parts = [repr(a) for a in display_args]
            parts += [f"{k}={v!r}" for k, v in kwargs.items()]
            arg_str = ", ".join(parts)

            indent = "  " * self.indent
            self.log(f"{indent}{self.input_prefix} {func.__qualname__}({arg_str})")

            self.indent += 1
            try:
                result = func(*args, **kwargs)
            finally:
                self.indent -= 1

            self.log(f"{indent}{self.return_prefix} {result!r}")
            return result

        return wrapper


call_stack = CallStack()
"""An shared instance for ease of use and configuration"""

log_calls = call_stack.log_calls
"""Use `from preditor.utils.call_stack import log_calls` as a shared decorator."""
