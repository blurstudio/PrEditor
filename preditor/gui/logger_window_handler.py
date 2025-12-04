from __future__ import absolute_import

import logging

from .. import instance
from ..constants import StreamType
from ..stream import Director, Manager


class LoggerWindowHandler(logging.Handler):
    """A logging handler that writes directly to the PrEditor instance.

    Args:
        formatter (str or logging.Formatter, optional): If specified,
            this is passed to setFormatter.
        stream (optional): If provided write to this stream instead of the
            main preditor instance's console.
        stream_type (StreamType, optional): If not None, pass this value to the
            write call's force kwarg.
    """

    default_format = (
        '%(levelname)s %(module)s.%(funcName)s line:%(lineno)d - %(message)s'
    )

    def __init__(
        self,
        formatter=default_format,
        stream=None,
        stream_type=StreamType.STDERR | StreamType.CONSOLE,
    ):
        super(LoggerWindowHandler, self).__init__()
        self.stream_type = stream_type
        self.stream = stream
        self.manager = Manager()
        self.director = Director(self.manager, StreamType.CONSOLE)

        if formatter is not None:
            if not isinstance(formatter, logging.Formatter):
                formatter = logging.Formatter(formatter)
            self.setFormatter(formatter)

    def emit(self, record):
        try:
            # If no gui has been created yet, or the `preditor.instance()` was
            # closed and garbage collected, there is nothing to do, simply exit
            stream = self.stream
            if not stream:
                return
            msg = self.format(record)
            kwargs = {}
            if self.stream_type is not None:
                kwargs["stream_type"] = self.stream_type
            stream.write(f'{msg}\n', **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)

    @property
    def stream(self):
        """The stream to write log messages to.

        If no stream is set then it returns `preditor.instance().console()`.
        """
        if self._stream is not None:
            return self._stream

        _instance = instance(create=False)
        if _instance is None:
            return None
        # Note: This does not handle if the instance has been closed
        return _instance.console()

    @stream.setter
    def stream(self, stream):
        self._stream = stream
