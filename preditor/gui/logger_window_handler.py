from __future__ import absolute_import

import logging

from .. import instance


class LoggerWindowHandler(logging.Handler):
    """A logging handler that writes directly to the PrEditor instance.

    Args:
        error (bool, optional): Write the output as if it were written
            to sys.stderr and not sys.stdout. Ie in red text.
        formatter (str or logging.Formatter, optional): If specified,
            this is passed to setFormatter.
    """

    default_format = (
        '%(levelname)s %(module)s.%(funcName)s line:%(lineno)d - %(message)s'
    )

    def __init__(self, error=True, formatter=default_format):
        super(LoggerWindowHandler, self).__init__()
        self.error = error
        if formatter is not None:
            if not isinstance(formatter, logging.Formatter):
                formatter = logging.Formatter(formatter)
            self.setFormatter(formatter)

    def emit(self, record):
        _instance = instance(create=False)
        if _instance is None:
            # No gui has been created yet, so nothing to do
            return
        try:
            # If the python logger was closed and garbage collected,
            # there is nothing to do, simply exit the call
            console = _instance.console()
            if not console:
                return

            msg = self.format(record)
            msg = u'{}\n'.format(msg)
            console.write(msg, self.error)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
