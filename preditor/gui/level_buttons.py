# standard library imports
from __future__ import absolute_import
from functools import partial
import logging

# third-party imports
from Qt.QtCore import QSignalMapper
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction, QMenu, QToolButton

# blur imports
from .. import resourcePath, debug
from ..enum import Enum, EnumGroup
from ..logger import LoggerWithSignals


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
            resourcePath('img/logger/{name}_{level}.png'.format(name=name, level=level))
        )


class LoggerLevel(Level):
    """A Logger level `Enum` using the 'format_align_left' icon."""

    icon_name = "logging"


class DebugLevel(Level):
    """A Debug level `Enum` using the 'bug_report' icon."""

    icon_name = "debug"


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


class DebugLevels(EnumGroup):
    """
    Debug levels with their implementation level name and number & custom
    icon level.
    """

    Disabled = DebugLevel(label="", number=0, level="disabled")
    Low = DebugLevel(label="Low", number=1, level="low")
    Mid = DebugLevel(label="Mid", number=2, level="mid")
    High = DebugLevel(label="High", number=4, level="high")


class DebugLevelButton(QToolButton):

    """
    A drop down button to set preditors's debug level.
    """

    def __init__(self, parent=None):
        """
        Creates the default debug level menu actions for updating preditors's
        debug level.

        Args:
            parent (QWidget, optional): The parent widget for this button.
        """
        super(QToolButton, self).__init__(parent=parent)
        self.setPopupMode(QToolButton.InstantPopup)

        # create & set menu
        self.setMenu(QMenu(parent=self))

        # `setLevel` signal mapper
        self._signal_mapper = QSignalMapper(self)
        self._signal_mapper.mapped[str].connect(self.setLevel)

        self._initializeDebugActions()

    def _initializeDebugActions(self):
        """
        Creates actions that control the preditors debug level.
        """
        for debug_level in DebugLevels:
            action = QAction(debug_level.icon, debug_level.name, self)
            action.setCheckable(True)

            # explain action in tooltip (ex: "Set debug level to Mid")
            action.setToolTip("Set debug level to {}".format(debug_level.name))

            # when clicked/activated set debug level
            self._signal_mapper.setMapping(action, debug_level.label)
            action.triggered.connect(self._signal_mapper.map)

            self.menu().addAction(action)

        self.refresh()

    def refresh(self):
        """
        Triggers an update of the debug tool bar button's various display
        elements so as to represent the current debug level. This includes the
        button's icon & tooltip, as well as the check-state of the debug level
        menu actions.
        """
        level = DebugLevels.fromValue(debug.debugLevel())

        self.setIcon(level)
        self.setCheckedAction(level)
        self.setToolTip(level)

    def setCheckedAction(self, level):
        """
        Updates the debug button's menu actions to check the currently active
        debug level.

        Args:
            level (DebugLevel): Debug level to check in debug menu.
        """
        for action in self.actions():
            action.setChecked(action.text() == level.name)

    def setIcon(self, level):
        """
        Updates the debug button's icon to display the current debug level
        preditor is set to.

        Args:
            level (DebugLevel): Debug level to change icon to represent.
        """
        super(QToolButton, self).setIcon(level.icon)

    def setLevel(self, level):
        """
        Sets preditor's debug level.

        Args:
            level (str): Name of debug level to set preditor to.
        """
        debug.setDebugLevel(level)
        self.refresh()

    def setToolTip(self, level):
        """
        Updates the debug menu's tooltip to explain what the current debug
        level is set to.

        Args:
            level (DebugLevel): Debug level to reflect in tooltip.
        """
        tool_tip = "Current debug level: {}".format(level.name)
        super(QToolButton, self).setToolTip(tool_tip)


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

        The `logger_created` signal emitted by the `LoggerWithSignals` is
        connected to the `createLoggerMenu`-method ensuring any newly
        initialized loggers have a menu created.

        Args:
            parent (QWidget, optional): The parent widget for this button.
        """
        super(QToolButton, self).__init__(parent=parent)
        self.setPopupMode(QToolButton.InstantPopup)

        # create root logger menu
        root = logging.getLogger("")
        root_menu = LoggingLevelMenu(name="", logger=root, parent=self)
        self.setMenu(root_menu)

        # track created logger menus; pre-populated with root logger menu
        self.loggerMenus = {"": root_menu}
        self._prexistingLoggerMenusInitialized = False

        # pre-spawn of the root menu, create logger menus & refresh tree
        root_menu.aboutToShow.connect(self.onMenuShow)

        # automatically create logger menu on logger init
        LoggerWithSignals.logger_created.connect(self.createLoggerMenu)

    def onMenuShow(self):
        """
        When the menu associated with this toolbar button is activated, the
        logger menus for any loggers that existed before the instantiation of
        this button will be created (once). The underlying the menu also be
        updated ensuring the logger menus within represent their current level
        state.

        Note: Triggering a refresh for every `aboutToShow` signal is necessary
            because when a logger is initialized via `logging.getLogger` the
            logger menu will be created as part of the overridden Logger class
            `__init__` method (from `LoggerWithSignals`), before the parent has
            been set. This results in an incorrect effective logging level as
            it cannot inherit the level of its ancestor (new loggers default to
            NOTSET).
        """
        if not self._prexistingLoggerMenusInitialized:
            self._initializeLoggerMenus()
            self._prexistingLoggerMenusInitialized = True

        self.menu().refresh()

    def _initializeLoggerMenus(self):
        """
        Creates logger menus for all loggers that currently exist.

        While looping through the logger dict, if the logger is merely a
        placeholder it will be initialized so it can be added to the menu
        hierarchy. This ensures all ancestors exist for appropriate parenting
        when descendants are added.

        Note: A logger present in the logger dict will be of class
            `logging.PlaceHolder` if the logger has not been initialized
            (accessed via `logging.getLogger`) and lies in-between an ancestor
            and one of its descendants that has been initialized.
        """
        logger_dict = list(logging.root.manager.loggerDict.items())
        for name, logger in sorted(logger_dict, key=lambda x: x[0].lower()):
            if isinstance(logger, logging.PlaceHolder):
                logger = logging.getLogger(name)
            self.createLoggerMenu(logger=logger)

    def createLoggerMenu(self, logger=None, **kwargs):
        """
        Creates a `LoggingLevelMenu` instance for the specified logger and adds
        it to the appropriate ancestor.

        During initialization each logger menu traverses its ancestry
        "top-down" ensuring menus exist for each ancestral logger. This ensures
        there are no parenting issues when adding the logger menu to the
        hierarchy.

        Args:
            logger (logging.Logger/LoggerWithSignals): Logger to create
                `LoggingLevelMenu` with. Present as a keyword argument due to
                requirement as slot a for signal to accept `**kwargs`.
            **kwargs: Unused. An implementation detail of `signalslot`, the
                keyword unpacking operator must be present in the signature of
                any slots connected to `signalslot` signals.
        """
        if not logger:
            return

        parent = self.menu()

        # iterate through parent logger names to ensure they exist
        split_name = logger.name.split(".")
        for index in range(1, len(split_name) + 1):
            logger_name = ".".join(split_name[0:index])

            # use pre-existing menu
            menu = self.loggerMenus.get(logger_name)
            if not menu:

                # create new menu & add to parent
                menu = LoggingLevelMenu(name=logger_name, logger=logger, parent=parent)
                parent.addChildMenu(menu)

                # track creation of menu
                self.loggerMenus[logger_name] = menu

            # set parent for subsequent loop iterations
            parent = menu


class LoggingLevelMenu(QMenu):

    """
    Custom menu for Python Loggers.

    Provides an interface for changing logger levels via menu actions. Also
    displays the presently set level by highlighting the relevant menu action
    and via the menu's icon (which displays the logger's effective level,
    potentially inherited from its ancestor).

    The display of the logger's current level remains accurate post-level
    change by connecting to signals present in the overridden Logger-class
    `LoggerWithSignals`.

    Descendant loggers' menus are also added and nested below the level menu
    actions, if present. If the level is updated in this or any ancestor menus,
    the descendant menus will have their `refresh` method executed.
    """

    def __init__(self, name="", logger=None, parent=None):
        """
        Creates the default level menu actions for updating the logger's level
        and, as long as the associated logger is of class type
        `LoggerWithSignals`, the `refresh` method is connected to the
        `level_changed` signal ensuring the present level is always correct.

        Args:
            name (str): Name of Logger this menu will represent.
            logger (logging.Logger/LoggerWithSignals): Logger this menu will
                represent and control via actions that modify the logger's
                set level.
            parent (QToolButton/QMenu): `QMenu` or `QToolButton` this menu will
                be parented to.
        """
        super(QMenu, self).__init__(title=name.split(".")[-1], parent=parent)

        self.name = name or "root"
        self.logger = logger

        self._initializeLevelActions()

        # refresh root at init to represent current level in toolbar
        if self.name == "root":
            self.refresh()

    def _initializeLevelActions(self):
        """
        Creates actions that control the logging level of the menu's associated
        logger.

        An invisible separator is appended to the end of the action list for
        future use in instances where descendant logger menus are added to the
        action list.
        """
        for logger_level in LoggerLevels:
            action = QAction(logger_level.icon, logger_level.name, self)
            action.setCheckable(True)

            # tooltip example: "Set 'preditor.debug' to level Warning")
            action.setToolTip(
                "Set '{}' to level {}".format(self.logger.name, logger_level.name)
            )

            # when clicked/activated set associated loggers level
            action.triggered.connect(
                partial(self.setLevel, getattr(logging, logger_level.label))
            )
            self.addAction(action)

        # append a separator to the end of the level action list to provide
        # visual distinction between level actions and descendant logger menus
        separator = QAction("Separator", self)
        separator.setSeparator(True)
        separator.setVisible(False)  # invisible until descendants added
        self.addAction(separator)

    def addChildMenu(self, menu):
        """
        Inserts the `LoggingLevelMenu` provided into the bottom section of the
        parent's action list, in alphabetical order.

        The list of logging level menus at the end of the instance's action
        list is preceded by a separator (as long as there are descendant menus
        present).

        Args:
            menu (LoggingLevelMenu): Logger QMenu to insert into action list.
        """
        current_actions = self.actions()
        current_names = list(map(lambda x: x.text(), current_actions))

        # ensure separator is visible
        separator_index = current_names.index("Separator")
        separator_action = current_actions[separator_index]
        separator_action.setVisible(True)

        child_menus_index_start = separator_index + 1
        child_menus = current_actions[child_menus_index_start:]

        # no children yet, add to bottom of menu
        if not child_menus:
            self.addMenu(menu)
            return

        # add new menu name to current list & sort
        child_menu_names = list(map(lambda x: x.text(), child_menus))
        child_menu_names.append(menu.title())
        sorted_child_names = sorted(child_menu_names, key=lambda x: x.lower())

        # find insert index in updated name list
        index = sorted_child_names.index(menu.title()) + child_menus_index_start

        # ensure we append to end if index greater than action list
        if index >= len(current_actions):
            self.addMenu(menu)

        # otherwise, add menu after preceding action/menu
        else:
            before_action = current_actions[index]
            self.insertMenu(before_action, menu)

    def childMenus(self):
        """
        Returns a list of descendant logger menus that may be present in the
        logger menu's action list. May return an empty list denoting no
        descendant menus exist.

        Returns:
            list: Descendant `LoggingLevelMenu`s.
        """
        child_menus = []
        current_actions = self.actions()
        current_names = list(map(lambda x: x.text(), current_actions))

        # determine start of child menus
        separator_index = current_names.index("Separator")
        child_menus_index_start = separator_index + 1

        child_menus = current_actions[child_menus_index_start:]

        return child_menus

    def refresh(self, **kwargs):
        """
        Triggers an update of the logger menu's various display elements so as
        to represent the logger's present level.

        The menu's icon is updated to reflected the effective logging level,
        inherited from the closest ancestor with a set level if the logger is
        set to `NOTSET`.

        The menu's tooltip and checked action in the action menu are derivative
        of the logger's native level.

        Any descendant logger menus are also refreshed so as to represent the
        most current logger state (such as level inheritance).

        Args:
            **kwargs: Unused. An implementation detail of `signalslot`, the
                keyword unpacking operator must be present in the signature of
                any slots connected to `signalslot` signals.
        """
        effective_level = self.logger.getEffectiveLevel()
        effective_level_name = logging.getLevelName(effective_level)

        level_num = self.logger.level
        level_name = logging.getLevelName(level_num)

        # icon represents the effective level
        self.setIcon(effective_level_name)

        # level actions & tooltip represent logger's level (or lack of)
        self.setCheckedAction(level_name)
        self.setToolTip(level_name)

        # refresh children
        for child_logger_menu in self.childMenus():
            child_logger_menu.menu().refresh()

    def setCheckedAction(self, level):
        """
        Updates the logger menu's actions to check the currently active logging
        level.

        Args:
            level (str): Logging level to check in logger action menu.
        """
        level_enum = LoggerLevels.fromLabel(level)
        for action in self.actions():
            action.setChecked(action.text() == level_enum.name)

    def setIcon(self, level):
        """
        Updates the logger menu's icon to display the current level the logger
        has is set to.

        If the updated logger is the root logger, the logging level toolbar
        button's icon is updated instead.

        Args:
            level (str): Logging level to change icon to represent.
        """
        level_enum = LoggerLevels.fromLabel(level)
        super(LoggingLevelMenu, self).setIcon(level_enum.icon)

        if self.name == "root":
            self.parent().setIcon(level_enum.icon)

    def setLevel(self, level):
        """
        Sets the logger this menu object represents to the level supplied.

        If the logger represented is not an instance of LoggerWithSignals,
        the refresh method is manually executed as the logger does not have
        signal necessary to automatically inform the menu to refresh.

        Args:
            level (str): Logging level to set logger to.
        """
        self.logger.setLevel(level)

        # non-overridden logger classes require manual refresh
        if not isinstance(self.logger, LoggerWithSignals):
            self.refresh()

    def setToolTip(self, level):
        """
        Updates the logger menu's tooltip to explain what the current level is
        set to.

        If the updated logger is the root logger, the logging level toolbar
        button's tooltip is updated instead.

        Args:
            level (str): Logging level to reflect in tooltip.
        """
        level_enum = LoggerLevels.fromLabel(level)

        tool_tip_text = "Logger '{}' current level: {}"
        tool_tip = tool_tip_text.format(self.logger.name, level_enum.name)

        if self.name == "root":
            self.parent().setToolTip(tool_tip)
        else:
            super(LoggingLevelMenu, self).setToolTip(tool_tip)
