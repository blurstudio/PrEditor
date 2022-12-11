from __future__ import absolute_import, print_function

import logging  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

from Qt.QtCore import Qt  # noqa: E402

from . import osystem  # noqa: E402
from .plugins import Plugins  # noqa: E402
from .version import version as __version__  # noqa: E402,F401

DEFAULT_CORE_NAME = "PrEditor"
"""The default name to use for the core name."""

_global_config = {}

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

plugins = Plugins()


def about_preditor(instance=None):
    """Useful info about installed packages generated by plugins.

    Args:
        instance (LoggerWindow, optional): Used by the AboutModule plugins
            to access the current instance of a Preditor GUI.
    """
    from .about_module import AboutModule

    return AboutModule.generate(instance=instance)


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

    for plugin in plugins.initialize():
        plugin()


def configure(name, parent_callback=None, excepthook=True, logging=True, streams=True):
    """Global configuration of PrEditor. Nothing is done if called more than once.

    Args:
        name (str): The core_name to use for the global instance of PrEditor.
            Once this has been set, you can call `launch` without passing name
            to access the main instance.
        parent_callback (callable, optional): Callback that returns a QWidget
            to use as the parent of the LoggerWindow when its first created.
            This can be used by DCC's to set the parent to their main window.
        excepthook (bool, optional): Replaces `sys.excepthook` with a interactive
            exception handler that prompts the user to show PrEditor when an
            python exception is raised.
        logging (bool, optional): Restore the python logging configuration that
            was recorded the last time PrEditor prefs were saved.
        streams (bool, optional): Install the stream manager to capture any
            stdout/stderr text written. Later when calling launch, the
            LoggerWindow will show all of the captured text. This lets you only
            create the LoggerWindow IF you need to, but when you do it will have
            all of the std stream text written after this call.
    """
    # Once this has been set, configure should not do anything
    if 'core_name' in _global_config:
        return

    # Store the core_name,.
    _global_config['core_name'] = name
    if parent_callback:
        _global_config['parent_callback'] = parent_callback

    if streams:
        # Install the stream manager to capture output
        from preditor.stream import install_to_std

        install_to_std()

    if logging:
        from .logging_config import LoggingConfig

        cfg = LoggingConfig(core_name=name)
        cfg.load()

    if excepthook:
        import preditor.debug

        preditor.debug.BlurExcepthook.install()


def launch(run_workbox=False, app_id=None, name=None):
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
    if name is None:
        # If the name wasn't passed we will get it from the name stored when
        # configure was called.
        if 'core_name' not in _global_config:
            raise RuntimeError(
                "You call configure before calling launch if not passing name"
            )
        name = _global_config['core_name']
    else:
        # A name was provided, call configure to ensure it has been called
        configure(name=name)

    from .gui.app import App
    from .gui.loggerwindow import LoggerWindow

    # Check if we can actually run the PrEditor gui and setup Qt if required
    app = App(name=app_id)
    widget = LoggerWindow.instance(run_workbox=run_workbox, name=name)

    # Show the PrEditor instance and make sure it regains focus and visibility
    widget.show()
    # If the instance was already shown, raise it to the top and make
    # it regain focus.
    widget.activateWindow()
    widget.raise_()
    widget.setWindowState(widget.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    widget.console().setFocus()
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


def root_window():
    # If a parent widget callback was configured, use it
    if 'parent_callback' in _global_config:
        return _global_config['parent_callback']()

    # Otherwise, attempt to find the top level widget from Qt
    from .gui.app import App

    return App.root_window()


def connect_preditor(
    parent, sequence='F2', text='Show PrEditor', obj_name='uiShowPreditorACT', name=None
):
    """Creates a QAction that shows the PrEditor gui with a keyboard shortcut.
    This will automatically call `preditor.configure` if name is provided,
    capturing any `sys.stdout` and `sys.stderr` writes after this call. This does
    not initialize the PrEditor gui instance until the action is actually called.

    Args:
        parent: The parent widget, normally a window
        sequence (str, optional): A string representing the keyboard shortcut
            associated with the QAction.
        text (str, optional): The display text for the QAction.
        obj_name (str, optional): Set the QAction's objectName to this value.

    Returns:
        QAction: The created QAction
    """
    from Qt.QtGui import QKeySequence
    from Qt.QtWidgets import QAction

    if name:
        # Set the core_name if provided
        configure(name)

    # Create shortcut for launching the PrEditor gui.
    action = QAction(text, parent)
    action.setObjectName(obj_name)
    action.triggered.connect(launch)
    action.setShortcut(QKeySequence(sequence))
    parent.addAction(action)
    return action


def instance(parent=None, run_workbox=False, create=True):
    """Returns the existing instance of the PrEditor gui creating it on first call.

    Args:
        parent (QWidget, optional): If the instance hasn't been created yet, create
            it and parent it to this object.
        run_workbox (bool, optional): If the instance hasn't been created yet, this
            will execute the active workbox's code once fully initialized.
        create (bool, optional): Returns None if the instance has not been created.

    Returns:
        Returns a fully initialized instance of the PrEditor gui. If called more
        than once, the same instance will be returned. If create is False, it may
        return None.
    """
    from .gui.loggerwindow import LoggerWindow

    return LoggerWindow.instance(parent=parent, run_workbox=run_workbox, create=create)


def shutdown():
    """Fully close and cleanup the PrEditor gui if it was created.

    Call this when shutting down your application to ensure any unsaved changes
    to the PrEditor gui are saved and the instance is actually closed instead
    of just hidden.

    If the PrEditor gui was never created, this does nothing so its safe to call
    even if the user never showed the gui. It also won't add extra time creating
    the gui just so it can "save any changes".

    Returns:
        bool: If a shutdown was required
    """
    from .gui.loggerwindow import LoggerWindow

    return LoggerWindow.instance_shutdown()


# initialize the core
init()
