from __future__ import absolute_import

import logging
import sys


class StreamHandlerHelper(object):
    """A collection of functions for manipulating ``logging.StreamHandler`` objects."""

    @classmethod
    def set_stream(cls, handler, stream):
        """For the given StreamHandler, set its stream. This works around
        python 2's lack of StreamHandler.setStream by replicating python 3.
        """
        # TODO: once python 2 is no longer supported, replace any uses of this
        # function with `handler.setStream(stream)`
        if sys.version_info[0] > 2:
            handler.setStream(stream)
        else:
            # Copied from python 3's logging's setStream to work in python 2
            handler.acquire()
            try:
                handler.flush()
                handler.stream = stream
            finally:
                handler.release()

    @classmethod
    def replace_stream(cls, old, new, logger=None):
        """Replaces the stream of StreamHandlers by checking all
        `logging.StreamHandler`'s attached to the provided logger. If any of them are
        using old for their stream, update that stream to new.

        Args:
            old (stream): Only StreamHandlers using this stream will be updated to new.
            new (stream): A file stream object like `sys.stderr` that will replace old.
            logger (logging.Logger, optional): The logger to update streams for. If
                None, the root logger(`logging.getLogger()`) will be used.
        """
        if logger is None:
            logger = logging.getLogger()

        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                if handler.stream == old:
                    cls.set_stream(handler, new)
