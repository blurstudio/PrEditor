from __future__ import absolute_import

import logging
import types
from functools import partial

from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction, QMenu, QToolButton

from .. import plugins, resourcePath
from ..enum import Enum, EnumGroup


class Level(Enum):

    """
    Custom `Enum` representing an information level.

    Attributes:
        cached_icon(None): Used to cache the created icon from `get_icon` for
            future use.
        icon_name(str): Name of source icon file to use when creating icon via
            `get_icon`.
    """

    cached_icon = None
    icon_name = "dot"

    @property
    def name(self):
        """
        Override of `name` property allowing for the return of a "friendly
        name" to be used in place of the inferred name from the `Enum` instance
        name.

        Returns:
            str: Name of `Enum` instance.
        """
        return getattr(self, "friendly_name", super(Level, self).name)

    @property
    def icon(self):
        """
        Icon representing the level. On first access, the icon is created via
        the `get_icon`-method and cached for later use.

        Returns:
            QIcon:
        """
        if not self.cached_icon:
            self.cached_icon = self.get_icon(self.icon_name, self.level)
        return self.cached_icon

    def get_icon(self, name, level):
        """
        Retrieves the icon of `name` and level.

        Args:
            name (str): Icon to retrieve QIcon for.
            level (str): Level name to apply.

        Returns:
            QIcon: Correct instantiated QIcon.
        """
        return QIcon(
            resourcePath('img/{name}_{level}.png'.format(name=name, level=level))
        )


class LoggerLevel(Level):
    """A Logger level `Enum` using the 'format_align_left' icon."""

    icon_name = "logging"

    def is_current(self, logger):
        """Returns if the current logging level matches this label."""
        return logging.getLevelName(logger.level) == self.label


class LoggerLevels(EnumGroup):
    """
    Logger levels with their implementation level name and number & custom
    icon level.
    """

    Disabled = LoggerLevel(
        friendly_name="Not Set / Inherited", label="NOTSET", number=0, level="not_set"
    )
    Critical = LoggerLevel(label="CRITICAL", number=50, level="critical")
    Error = LoggerLevel(label="ERROR", number=40, level="error")
    Warning = LoggerLevel(label="WARNING", number=30, level="warning")
    Info = LoggerLevel(label="INFO", number=20, level="info")
    Debug = LoggerLevel(label="DEBUG", number=10, level="debug")

    @classmethod
    def fromLabel(cls, label, default=None, logger=None):
        try:
            return super(LoggerLevels, cls).fromLabel(label, default=default)
        except ValueError:
            # This is not be a standard level, generate a custom level to use
            if logger is None:
                logger = logging.getLogger()
            effective_level = logger.getEffectiveLevel()
            effective_level_name = logging.getLevelName(effective_level)

            enum = LoggerLevel(
                label=effective_level_name,
                number=effective_level,
                level=effective_level_name,
            )
            # Force the custom icon as this enum's name won't match
            enum.cached_icon = enum.get_icon(enum.icon_name, "custom")
            # Add it to the enum
            LoggerLevels.append(enum)
            return enum


class LoggingLevelButton(QToolButton):

    """
    A drop down button to set logger levels for all loggers known to Python's
    native logging implementation.

    The logger menus present in the tool bar button have level-changing actions
    as well a sub-menus for any descendant loggers.
    """

    def __init__(self, parent=None):
        """
        Creates the root logger menu this button displays when clicked.
        Additionally, any pre-existing loggers and their menus are added.

        Args:
            parent (QWidget, optional): The parent widget for this button.
        """
        super(LoggingLevelButton, self).__init__(parent=parent)
        self.setPopupMode(QToolButton.InstantPopup)

        # create root logger menu
        root = logging.getLogger("")
        root_menu = LoggingLevelMenu(name="root", logger=root, parent=self)
        self.setMenu(root_menu)

        # TODO: Hook refresh up to a root logger signal
        # Monkey patch root.setLogger to emit signal we connect to
        root = self.patched_root_logger().level_changed.connect(self.refresh)

    @staticmethod
    def patched_root_logger():
        """Returns `logging.getLogger("")`. This will have the level_changed
        signal added if it wasn't already.

        The level_changed signal is emitted any time something changes the
        root logger level. PrEditor uses this to update the logging level button
        icon any time the root logger's level is changed. The rest of the loggers
        don't need this as the menu is built on demand with the correct icons indicated.
        """
        root = logging.getLogger("")
        if hasattr(root, "level_changed"):
            # Already patched, nothing to do
            return root

        # Need to patch the root logger
        from signalslot import Signal

        root.level_changed = Signal(args=["level"], name="level_changed")

        # Store the current setLevel, so we can call it in our method
        root._setLevel = root.setLevel

        def setLevel(self, level):
            """
            Sets the threshold for this logger to `level`. Also emits the
            instance's `level_changed`-signal with the level number as its payload.

            Args:
                level (int): Numeric level value.
            """
            # Call the original setLevel method
            self._setLevel(level)
            # Emit our signal
            self.level_changed.emit(level=level)

        root.setLevel = types.MethodType(setLevel, root)

        return root

    def refresh(self, **kwargs):
        effective_level = logging.getLogger("").getEffectiveLevel()
        effective_level_name = logging.getLevelName(effective_level)
        level_enum = LoggerLevels.fromLabel(effective_level_name)

        self.setIcon(level_enum.icon)
        self.setToolTip("Logger 'root' current level: {}".format(level_enum.name))


class LazyMenu(QMenu):
    """A menu class that only calls self.refresh when it is about to be shown."""

    def __init__(self, *args, **kwargs):
        super(LazyMenu, self).__init__(*args, **kwargs)
        self.aboutToShow.connect(self.refresh)


class HandlerMenu(LazyMenu):
    def __init__(self, logger, parent=None):
        super(HandlerMenu, self).__init__(title="Handlers", parent=parent)
        self.logger = logger

    def install_handler(self, name):
        plugins.add_logging_handler(self.logger, name)

    def refresh(self):
        self.clear()
        # Add the Install sub menu showing all logging_handler plugins
        handler_install = self.addMenu('Install')
        for name, cls in plugins.logging_handlers():
            act = handler_install.addAction(name)
            act.triggered.connect(partial(self.install_handler, name))
            for h in self.logger.handlers:
                if type(h) is cls:
                    act.setEnabled(False)
                    act.setToolTip('Already installed for this logger.')
                    break

        # Add a visual indication of all of the existing handlers
        # TODO: Add ability to modify the formatters and auto-creation on startup
        self.addSeparator()
        for handler in self.logger.handlers:
            act = self.addAction(repr(handler))
            act.setEnabled(False)


class LoggingLevelMenu(LazyMenu):

    """
    Custom menu for Python Loggers.

    Provides an interface for changing logger levels via menu actions. Also
    displays the presently set level by highlighting the relevant menu action
    and via the menu's icon (which displays the logger's effective level,
    potentially inherited from its ancestor).
    """

    def __init__(self, name, logger, parent=None):
        """
        Creates the default level menu actions for updating the logger's level.

        Args:
            name (str): Name of Logger this menu will represent.
            logger (logging.Logger): Logger this menu will represent and control
                via actions that modify the logger's set level.
            parent (QToolButton/QMenu): `QMenu` or `QToolButton` this menu will
                be parented to.

        Note: If the logger is merely a placeholder it will be initialized so
            it can be added to the menu hierarchy. This ensures all ancestors
            exist for appropriate parenting when descendants are added.
        """
        super(LoggingLevelMenu, self).__init__(title=name.split(".")[-1], parent=parent)

        if isinstance(logger, logging.PlaceHolder):
            logger = logging.getLogger(name)

        self.logger = logger
        self.name = name
        self.update_ui()

    def children(self):
        """The direct sub-loggers of this logging object."""
        parent = self.name
        if parent == "root":
            parent = ""
        for name, logger in sorted(
            logging.root.manager.loggerDict.items(), key=lambda x: x[0].lower()
        ):
            if name.startswith(parent):
                remaining = name.lstrip(parent).lstrip(".")
                if remaining and "." not in remaining:
                    yield name, logger

    def level(self):
        """Returns the current effective LoggerLevel for self.logger."""
        effective_level = self.logger.getEffectiveLevel()
        effective_level_name = logging.getLevelName(effective_level)
        return LoggerLevels.fromLabel(effective_level_name, logger=self.logger)

    def refresh(self):
        self.clear()

        self.addMenu(HandlerMenu(self.logger, self))
        self.addSeparator()

        for logger_level in LoggerLevels:
            is_current = logger_level.is_current(self.logger)

            action = QAction(logger_level.icon, logger_level.name, self)
            action.setCheckable(True)
            action.setChecked(is_current)

            # tooltip example: "Set 'preditor.debug' to level Warning")
            action.setToolTip(
                "Set '{}' to level {}".format(self.name, logger_level.name)
            )

            # when clicked/activated set associated loggers level
            action.triggered.connect(partial(self.setLevel, logger_level.number))
            self.addAction(action)

        self.addSeparator()

        for name, child in self.children():
            self.addMenu(LoggingLevelMenu(name, child, self))

    def setLevel(self, level):
        """
        Sets the logger this menu object represents to the level supplied.

        Args:
            level (str): Logging level to set logger to.
        """
        self.logger.setLevel(level)
        self.update_ui()

    def update_ui(self):
        """Set the menu icon to this LoggerLevel's icon.

        If the updated logger is the root logger, the logging level toolbar
        button's icon is updated instead.

        Args:
            level (LoggerLevel): Logging level to change icon to represent.
        """

        level_enum = self.level()
        act = self.menuAction()
        act.setIcon(level_enum.icon)
        act.setToolTip(
            "Logger '{}' current level: {}".format(self.logger.name, level_enum.name)
        )

        if self.name == "root":
            self.parent().refresh()
