from __future__ import absolute_import

import logging
from functools import wraps

logger = logging.getLogger(__name__)


def set_if_unlocked(track_state=False):
    def _set_if_unlocked(func):
        """Decorate property setter functions to prevent editing after locking."""

        @wraps(func)
        def wrapper(self, value):
            if not self.is_locked(func.__name__, track_state=track_state):
                # logger.debug(f'"{func.__name__}" is unlocked and can be set: {value}')
                return func(self, value)
            # logger.info(
            #     f'"{func.__name__}" is locked and can no-longer be set: {value}'
            # )

        return wrapper

    return _set_if_unlocked


class PreditorConfig:
    """Global configuration of PrEditor's instance.

    When creating the main PrEditor instance it will use `preditor.config` to
    control how its initialized. That stores an instance of this class.

    Once `preditor.instance(create=True)` the properties on this class will then
    silently ignore any attempts to set most of its properties. Where noted in
    the property doc-strings, some properties are used to install a setting that
    can't be automatically undone, so they will stop responding after the first
    setting.

    While this class does not force a singleton pattern, it is expected in normal
    operation that there will only ever be a single instance made and it is stored
    on `preditor.config` when first imported. Things like excepthook and streams
    modify python's state which could lead to duplicate outputs, multiple error
    prompts or other undesirable behavior.
    """

    def __init__(self):
        self._locks = {}
        self._name = None
        self._logging = False
        self._headless_callback = None
        self._on_create_callback = None
        self._parent_callback = None
        self._error_dialog_class = True
        self._excepthooks = []

    def dump(self, indent=0):
        """A convenient way to inspect the current configuration."""
        ret = [
            f"{' ' * indent}name: {self.name}",
            f"{' ' * indent}streams: {self.streams}",
            f"{' ' * indent}excepthook: {self.excepthook!r}",
            f"{' ' * indent}excepthooks: {self.excepthooks!r}",
            f"{' ' * indent}error_dialog_class: {self.error_dialog_class!r}",
            f"{' ' * indent}logging: {self.logging}",
            f"{' ' * indent}headless_callback: {self.headless_callback!r}",
            f"{' ' * indent}parent_callback: {self.parent_callback!r}",
            f"{' ' * indent}on_create_callback: {self.on_create_callback!r}",
        ]
        return '\n'.join(ret)

    def is_locked(self, value, track_state=False):
        """Returns if value is locked and can not be updated.

        Once `preditor.instance` returns a value this will always return False.
        The config settings should not be modified once the instance is created.

        Args:
            value (str): The name of the value to check. Should match a property
                name on this class.
            track_state (bool, optional): If True then also check if value has
                been flagged as locked. This indicates that it was already set
                by a previous call and can no longer be modified even if instance
                is False.
        """
        if self.instance(create=False):
            # if the instance is created all items are locked
            return True
        if track_state:
            return self._locks.get(value, False)
        return False

    @property
    def error_dialog_class(self):
        """Dialog class shown if PrEditor isn't visible and a error happens.

        This dialog is used to prompt the user to show PrEditor and can be
        sub-classed to add extra functionality. This is called by
        `PreditorExceptHook.ask_to_show_logger` method when added to
        `preditor.config.excepthooks`.

        If set to `True` then `blurdev.gui.errordialog.ErrorDialog` is used. When
        replacing this, it should be a sub-class of that class or re-implement
        its api.

        You can use an EntryPoint string like `preditor.gui.errordialog:ErrorDialog`
        instead of passing the actual class object. This lets you delay the import
        until actually needed.
        """
        return self._error_dialog_class

    @error_dialog_class.setter
    def error_dialog_class(self, cls):
        self._error_dialog_class = cls

    @property
    def excepthook(self):
        """Installs a `sys.excepthook` handler when first set to True.

        Replaces `sys.excepthook` with a interactive exception handler that
        prompts the user to show PrEditor when an python exception is raised.
        It is recommended that you only add the excepthook once the Qt UI is
        initialized. See: :py:class:`preditor.excepthooks.PreditorExceptHook`.
        """
        return self._locks.get("excepthook", False)

    @excepthook.setter
    @set_if_unlocked(track_state=True)
    def excepthook(self, value):
        if not value:
            return

        # Install the excepthook:
        import preditor.excepthooks

        # Note: install checks if the current excepthook is a instance of this
        # class and prevents installing a second time.
        preditor.excepthooks.PreditorExceptHook.install()

        # Disable future setting via `set_if_unlocked`, the `PreditorExceptHook`
        # is a chaining except hook that calls the previous excepthook when called.
        # We don't want to install multiple automatically, the user can define that
        # logic if required.
        self._locks["excepthook"] = True

    @property
    def excepthooks(self):
        """A list of callables that are called when an exception is handled.

        If `excepthook` is enabled installing `PreditorExceptHook` then it will
        call each item in this list. The signature of the function should be
        `callable(*args)`. If not configured it will automatically install default
        callables. You can add `None` to disable this.
        """
        return self._excepthooks

    @property
    def headless_callback(self):
        """A pointer to a method that is called by `is_headless`.

        This callback returns a bool indicating if PrEditor should attempt to
        create GUI elements. Application integrations can set this callback to
        give them control over what PrEditor gets parent to.
        """
        return self._headless_callback

    @headless_callback.setter
    @set_if_unlocked()
    def headless_callback(self, cb):
        self._headless_callback = cb

    @classmethod
    def instance(cls, parent=None, run_workbox=False, create=True):
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

        return LoggerWindow.instance(
            parent=parent, run_workbox=run_workbox, create=create
        )

    def is_headless(self):
        """Returns True if PrEditor should not create GUI items.

        Returns None if the `headless_callback` has not been configured. Otherwise
        returns the result of calling `headless_callback()` which should return a bool.
        """
        if not self.headless_callback:
            return None
        return self.headless_callback()

    @property
    def logging(self):
        """Restore the python logging configuration settings that were recorded
        the last time PrEditor prefs were saved.

        If called multiple times with different name's before the instance is
        created, this will reset the logging configuration from the previous
        name if logging prefs exist.
        """
        return self._logging

    @logging.setter
    def logging(self, state):
        self._logging = state
        self.update_logging()

    @property
    def name(self):
        """The name to use for the global instance of PrEditor.

        Once this has been set, you can call `preditor.launch` without passing
        name to access the main instance. The name controls what preferences
        are loaded and used by PrEditor including the workbox tabs."""
        return self._name

    @name.setter
    @set_if_unlocked()
    def name(self, name):
        changed = self.name != name
        self._name = name

        if changed:
            # If the core name was changed attempt to update the logging config.
            self.update_logging()

    @property
    def on_create_callback(self):
        """A pointer to a method that is called on LoggerWindow instance create.

        This callback accepts the instance and can be used to customize the
        LoggerWindow instance when it is first created.
        """
        return self._on_create_callback

    @on_create_callback.setter
    @set_if_unlocked()
    def on_create_callback(self, cb):
        self._on_create_callback = cb

    @property
    def parent_callback(self):
        """A pointer to a method that is called by `self.root_window`.

        This callback returns a QWidget to use as the parent of the LoggerWindow
        when the instance is first created. This can be used by DCC's to set the
        parent to their main window."""
        return self._parent_callback

    @parent_callback.setter
    @set_if_unlocked()
    def parent_callback(self, cb):
        self._parent_callback = cb

    def root_window(self):
        """The QWidget to use as the parent of PrEditor widgets."""
        # If a parent widget callback was configured, use it
        if self.parent_callback is not None:
            return self.parent_callback()

        # Otherwise, attempt to find the top level widget from Qt
        from .gui.app import App

        return App.root_window()

    @property
    def streams(self):
        """Installs the stream managers when first set to True.

        Install the stream manager to capture any stdout/stderr text written.
        Later when calling launch, the LoggerWindow will show all of the captured
        text. This lets you only create the LoggerWindow IF you need to show it,
        but when you do it will have all of the std stream text written after
        this is enabled."""
        return self._locks.get("streams", False)

    @streams.setter
    @set_if_unlocked(track_state=True)
    def streams(self, value):
        if not value:
            return

        # Install the stream manager to capture output
        from .stream import install_to_std

        install_to_std()

        # Disable re-installing streams.
        self._locks["streams"] = True

    def update_logging(self):
        """Install/replace the logging config.

        This does nothing unless `logging` is set to True and `name` is set.

        Note: When called repeatedly, this won't remove old logger's added by
        previous calls so you may see some loggers added that were never
        actually added by code other than the LoggingConfig.
        """

        if not (self.logging and self.name):
            return

        from .logging_config import LoggingConfig

        cfg = LoggingConfig(core_name=self.name)
        cfg.load()
