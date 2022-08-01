from __future__ import absolute_import, print_function

from . import logger

# Override the base logging class.
logger.patchLogger()

import logging  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

import sentry_bootstrap  # noqa: E402
from Qt.QtCore import Qt  # noqa: E402

from . import osystem  # noqa: E402
from .utils.error import sentry_before_send_callback  # noqa: E402
from .version import version as __version__  # noqa: E402,F401

core = None  # create a managed Core instance
"""
The blurdev managed :class:`Core` object from the :mod:`blurdev.cores` module.
"""

# Create the root blurdev module logging object.
_logger = logging.getLogger(__name__)

# Add a NullHandler to suppress the "No handlers could be found for _logger"
# warnings from being printed to stderr. Studiomax and possibly other DCC's
# tend to treat any text written to stderr as a error when running headless.
# We also don't want this warning showing up in production anyway.
_logger.addHandler(logging.NullHandler())


def init():
    os.environ['BDEV_EMAILINFO_PREDITOR_VERSION'] = __version__
    pythonw_print_bugfix()
    global core
    # create the core
    if not core:
        from .cores.core import Core

        objectName = None
        _exe = os.path.basename(sys.executable).lower()
        # Treat designer as a seperate core so it gets its own prefrences.
        if 'designer' in _exe:
            objectName = 'designer'
        elif 'assfreezer' in _exe:
            objectName = 'assfreezer'
        core = Core(objectName=objectName)

        # initialize sentry client
        # TODO: Move this to a plugin/remove it
        sentry_bootstrap.init_sentry(force=True)
        sentry_bootstrap.add_external_callback(sentry_before_send_callback)


def launch(modal=False, run_workbox=False, app_id=None):
    """Launches the preditor gui creating the QApplication instance if not
    already created.

    Args:
        modal (bool, optional): If True, preditor's gui will be created as a
            modal window (ie. blocks current code execution while its shown).
        run_workbox (bool, optional): After preditor's gui is shown, run its
            current workbox text.
        app_id (str, optional): Set the QApplication's applicationName to this
            value. This is normally only used when launching a standalone
            instance of the PrEditor gui.

    Returns:
        preditor.gui.loggerwindow.LoggerWindow: The instance of the PrEditor
            gui that was created.
    """
    from .gui.app import App
    from .gui.loggerwindow import LoggerWindow

    # Check if we can actually run the PrEditor gui and setup Qt if required
    app = App(name=app_id)
    widget = LoggerWindow.instance(run_workbox=run_workbox)

    # check to see if the tool is running modally and return the result
    if modal:
        widget.exec_()
    else:
        widget.show()
        # If the instance was already shown, raise it to the top and make
        # it regain focus.
        widget.raise_()
        widget.setWindowState(
            widget.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
        app.start()

    return widget


def prefPath(relpath, coreName=''):
    # use the core
    if not coreName and core:
        coreName = core.objectName()
    basepath = os.path.join(
        osystem.expandvars(os.environ['BDEV_PATH_PREFS']), 'app_%s/' % coreName
    )
    return os.path.normpath(os.path.join(basepath, relpath))


def pythonw_print_bugfix():
    """
    When running pythonw print statements and file handles tend to have problems
    so, if its pythonw and stderr and stdout haven't been redirected, redirect them
    to os.devnull.
    """
    if os.path.basename(sys.executable) == 'pythonw.exe':
        if sys.stdout == sys.__stdout__:
            sys.stdout = open(os.devnull, 'w')
        if sys.stderr == sys.__stderr__:
            sys.stderr = open(os.devnull, 'w')


def relativePath(path, additional=''):
    """
    Replaces the last element in the path with the passed in additional path.
    :param path: Source path. Generally a file name.
    :param additional: Additional folder/file path appended to the path.
    :return str: The modified path
    """
    return os.path.join(os.path.dirname(path), additional)


def resourcePath(relpath=''):
    """Returns the full path to the file inside the preditor/resource folder

    Args:
        relpath (str, optional): The additional path added to the
            preditor/resource folder path.

    Returns:
        str: The modified path
    """
    return os.path.join(relativePath(__file__), 'resource', relpath)


def signalInspector(item, prefix='----', ignore=None):
    """Connects to all signals of the provided item, and prints the name of
    each signal.  When that signal is activated it will print the prefix,
    the name of the signal, and any arguments passed. These connections
    will persist for the life of the object.

    Args:
        item (Qt.QtCore.QObject): QObject to inspect signals on.
        prefix (str, optional): The prefix to display when a signal is emitted.
        ignore (list, optional): A list of signal names to ignore
    """

    def create(attr):
        def handler(*args, **kwargs):
            print(prefix, 'Signal:', attr, 'ARGS:', args, kwargs)

        return handler

    if ignore is None:
        ignore = []

    for attr in dir(item):
        if (
            type(getattr(item, attr)).__name__ == 'pyqtBoundSignal'
            and attr not in ignore
        ):
            print(attr)
            getattr(item, attr).connect(create(attr))


# initialize the core
init()
