"""Plugin used to enable access to python's stdout/stderr. Without this we have
no way to see python output on windows because its not a console app.

All output is written to $TEMP/preditor_qdesigner_plugins.log.
"""

import sys
import tempfile
import traceback
from pathlib import Path

from preditor.debug import logToFile

path = Path(tempfile.gettempdir()) / "preditor_qdesigner_plugins.log"
logToFile(path, useOldStd=False)


def no_crash_excepthook(exc_type, exc_value, tb):
    """This consumes the exception so Qt doesn't exit on un-handled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, tb)
        return

    print("--- Unhanded Exception Start ---")
    print(traceback.print_exception(exc_type, exc_value, tb))
    print("--- Unhanded Exception End   ---")


sys.excepthook = no_crash_excepthook
