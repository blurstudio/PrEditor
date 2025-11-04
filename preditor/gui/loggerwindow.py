from __future__ import absolute_import, print_function

import copy
import itertools
import json
import logging
import os
import re
import shutil
import sys
import warnings
from builtins import bytes
from datetime import datetime, timedelta
from enum import IntEnum
from functools import partial
from pathlib import Path

import __main__
import Qt as Qt_py
from Qt import QtCompat, QtCore, QtWidgets
from Qt.QtCore import QByteArray, QFileSystemWatcher, QObject, Qt, QTimer, Signal, Slot
from Qt.QtGui import QCursor, QFont, QIcon, QKeySequence, QTextCursor
from Qt.QtWidgets import (
    QApplication,
    QFontDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QToolTip,
    QVBoxLayout,
)

from .. import (
    DEFAULT_CORE_NAME,
    about_preditor,
    config,
    debug,
    get_core_name,
    osystem,
    plugins,
    prefs,
    resourcePath,
)
from ..delayable_engine import DelayableEngine
from ..gui import Dialog, Window, loadUi, tab_widget_for_tab
from ..gui.fuzzy_search.fuzzy_search import FuzzySearch
from ..gui.group_tab_widget.grouped_tab_models import GroupTabListItemModel
from ..logging_config import LoggingConfig
from ..utils import stylesheets
from .completer import CompleterMode
from .level_buttons import LoggingLevelButton
from .set_text_editor_path_dialog import SetTextEditorPathDialog
from .status_label import StatusLabel
from .workbox_mixin import WorkboxName

logger = logging.getLogger(__name__)

PRUNE_PATTERN = r"(?P<name>\w*)-{}\.".format(prefs.DATETIME_PATTERN.pattern)
PRUNE_PATTERN = re.compile(PRUNE_PATTERN)


class WorkboxPages(IntEnum):
    """Nice names for the uiWorkboxSTACK indexes."""

    Options = 0
    Workboxes = 1


class LoggerWindow(Window):
    _instance = None
    styleSheetChanged = Signal(str)

    def __init__(self, parent, name=None, run_workbox=False, standalone=False):
        super(LoggerWindow, self).__init__(parent=parent)
        self.name = name if name else get_core_name()

        self._logToFilePath = None

        self._stylesheet = 'Bright'

        self.setupStatusTimer()

        # Define gui-resizing mods, which may need to be accessed by other modules.
        ctrl = Qt.KeyboardModifier.ControlModifier
        alt = Qt.KeyboardModifier.AltModifier
        self.gui_font_mod = ctrl | alt

        # Store the previous time a font-resize wheel event was triggered to prevent
        # rapid-fire WheelEvents. Initialize to the current time.
        self.previousFontResizeTime = datetime.now()

        self.setWindowIcon(QIcon(resourcePath('img/preditor.png')))
        loadUi(__file__, self)

        self.uiConsoleTXT.flash_window = self
        self.uiConsoleTXT.clearExecutionTime = self.clearExecutionTime
        self.uiConsoleTXT.reportExecutionTime = self.reportExecutionTime
        self.uiClearToLastPromptACT.triggered.connect(
            self.uiConsoleTXT.clearToLastPrompt
        )
        # If we don't disable this shortcut Qt won't respond to this classes or
        # the ConsolePrEdit's
        self.uiConsoleTXT.uiClearToLastPromptACT.setShortcut('')

        # create the status reporting label
        self.uiStatusLBL = StatusLabel(self)
        self.uiMenuBar.setCornerWidget(self.uiStatusLBL)

        # create the workbox tabs
        self._currentTab = -1

        # Setup delayable system
        self.delayable_engine = DelayableEngine.instance('logger', self)

        self.uiWorkboxTAB.editor_kwargs = dict(
            console=self.uiConsoleTXT, delayable_engine=self.delayable_engine.name
        )

        # Create additional buttons in toolbar.
        self.uiLoggingLevelBTN = LoggingLevelButton(self)
        self.uiConsoleTOOLBAR.insertWidget(
            self.uiRunSelectedACT,
            self.uiLoggingLevelBTN,
        )
        self.uiConsoleTOOLBAR.insertSeparator(self.uiRunSelectedACT)

        # Configure Find in Workboxes
        self.uiFindInWorkboxesWGT.hide()
        self.uiFindInWorkboxesWGT.managers.append(self.uiWorkboxTAB)
        self.uiFindInWorkboxesWGT.console = self.console()

        # Initial configuration of the logToFile feature
        self._logToFilePath = None
        self._stds = None
        self.uiLogToFileClearACT.setVisible(False)

        self.uiRestartACT.triggered.connect(self.restartLogger)
        self.uiCloseLoggerACT.triggered.connect(self.closeLogger)

        self.uiRunAllACT.triggered.connect(self.execAll)
        # Even though the RunSelected actions (with shortcuts) are connected
        # here, this only affects if the action is chosen from the menu. The
        # shortcuts are always intercepted by the workbox document editor. To
        # handle this, the workbox.keyPressEvent method will perceive the
        # shortcut press, and call .execSelected, which will then ultimately call
        # workbox.__exec_selected__
        self.uiRunSelectedACT.triggered.connect(
            partial(self.execSelected, truncate=True)
        )
        self.uiRunSelectedDontTruncateACT.triggered.connect(
            partial(self.execSelected, truncate=False)
        )

        self.uiConsoleAutoCompleteEnabledACT.toggled.connect(
            partial(self.setAutoCompleteEnabled, console=True)
        )
        self.uiWorkboxAutoCompleteEnabledACT.toggled.connect(
            partial(self.setAutoCompleteEnabled, console=False)
        )

        self.uiAutoCompleteCaseSensitiveACT.toggled.connect(self.setCaseSensitive)

        self.uiSelectMonospaceFontACT.triggered.connect(
            partial(self.selectFont, origFont=None, monospace=True)
        )
        self.uiSelectProportionalFontACT.triggered.connect(
            partial(self.selectFont, origFont=None, proportional=True)
        )
        self.uiSelectAllFontACT.triggered.connect(
            partial(self.selectFont, origFont=None, monospace=True, proportional=True)
        )
        self.uiSelectGuiFontsMENU.triggered.connect(
            partial(self.selectGuiFont, monospace=True, proportional=True)
        )

        self.uiDecreaseCodeFontSizeACT.triggered.connect(
            partial(self.adjustFontSize, "Code", -1)
        )
        self.uiIncreaseCodeFontSizeACT.triggered.connect(
            partial(self.adjustFontSize, "Code", 1)
        )
        self.uiDecreaseGuiFontSizeACT.triggered.connect(
            partial(self.adjustFontSize, "Gui", -1)
        )
        self.uiIncreaseGuiFontSizeACT.triggered.connect(
            partial(self.adjustFontSize, "Gui", 1)
        )

        # Setup ability to cycle completer mode, and create action for each mode
        self.completerModeCycle = itertools.cycle(CompleterMode)
        # create CompleterMode submenu
        defaultMode = next(self.completerModeCycle)
        for mode in CompleterMode:
            modeName = mode.displayName()
            action = self.uiCompleterModeMENU.addAction(modeName)
            action.setObjectName('ui{}ModeACT'.format(modeName))
            action.setData(mode)
            action.setCheckable(True)
            action.setChecked(mode == defaultMode)
            completerMode = CompleterMode(mode)
            action.setToolTip(completerMode.toolTip())
            action.triggered.connect(partial(self.selectCompleterMode, action))

        self.uiCompleterModeMENU.addSeparator()
        action = self.uiCompleterModeMENU.addAction('Cycle mode')
        action.setObjectName('uiCycleModeACT')
        action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_M))
        action.triggered.connect(self.cycleCompleterMode)
        self.uiCompleterModeMENU.hovered.connect(self.handleMenuHovered)

        # Workbox add/remove
        self.uiNewWorkboxACT.triggered.connect(
            lambda: self.uiWorkboxTAB.add_new_tab(group=True)
        )
        self.uiCloseWorkboxACT.triggered.connect(self.uiWorkboxTAB.close_current_tab)

        # Browse previous commands
        self.uiGetPrevCmdACT.triggered.connect(self.getPrevCommand)
        self.uiGetNextCmdACT.triggered.connect(self.getNextCommand)

        # Focus to console or to workbox, optionally copy seleciton or line
        self.uiFocusToConsoleACT.triggered.connect(self.focusToConsole)
        self.uiCopyToConsoleACT.triggered.connect(self.copyToConsole)
        self.uiFocusToWorkboxACT.triggered.connect(self.focusToWorkbox)
        self.uiCopyToWorkboxACT.triggered.connect(self.copyToWorkbox)

        # Navigate workbox tabs
        self.uiNextTabACT.triggered.connect(self.nextTab)
        self.uiPrevTabACT.triggered.connect(self.prevTab)

        # Navigate workbox versions
        self.uiTab1ACT.triggered.connect(partial(self.gotoTabByIndex, 1))
        self.uiTab2ACT.triggered.connect(partial(self.gotoTabByIndex, 2))
        self.uiTab3ACT.triggered.connect(partial(self.gotoTabByIndex, 3))
        self.uiTab4ACT.triggered.connect(partial(self.gotoTabByIndex, 4))
        self.uiTab5ACT.triggered.connect(partial(self.gotoTabByIndex, 5))
        self.uiTab6ACT.triggered.connect(partial(self.gotoTabByIndex, 6))
        self.uiTab7ACT.triggered.connect(partial(self.gotoTabByIndex, 7))
        self.uiTab8ACT.triggered.connect(partial(self.gotoTabByIndex, 8))
        self.uiTabLastACT.triggered.connect(partial(self.gotoTabByIndex, -1))

        self.uiGroup1ACT.triggered.connect(partial(self.gotoGroupByIndex, 1))
        self.uiGroup2ACT.triggered.connect(partial(self.gotoGroupByIndex, 2))
        self.uiGroup3ACT.triggered.connect(partial(self.gotoGroupByIndex, 3))
        self.uiGroup4ACT.triggered.connect(partial(self.gotoGroupByIndex, 4))
        self.uiGroup5ACT.triggered.connect(partial(self.gotoGroupByIndex, 5))
        self.uiGroup6ACT.triggered.connect(partial(self.gotoGroupByIndex, 6))
        self.uiGroup7ACT.triggered.connect(partial(self.gotoGroupByIndex, 7))
        self.uiGroup8ACT.triggered.connect(partial(self.gotoGroupByIndex, 8))
        self.uiGroupLastACT.triggered.connect(partial(self.gotoGroupByIndex, -1))

        self.uiRunFirstWorkboxACT.triggered.connect(self.run_first_workbox)

        self.latestTimeStrsForBoxesChangedViaInstance = {}
        self.boxesOrphanedViaInstance = {}

        self.uiFocusNameACT.triggered.connect(self.show_focus_name)

        self.uiCommentToggleACT.triggered.connect(self.comment_toggle)

        self.uiSpellCheckEnabledACT.toggled.connect(self.setSpellCheckEnabled)
        self.uiIndentationsTabsACT.toggled.connect(self.updateIndentationsUseTabs)
        self.uiCopyTabsToSpacesACT.toggled.connect(self.updateCopyIndentsAsSpaces)
        self.uiWordWrapACT.toggled.connect(self.setWordWrap)
        self.uiResetWarningFiltersACT.triggered.connect(warnings.resetwarnings)
        self.uiLogToFileACT.triggered.connect(self.installLogToFile)
        self.uiLogToFileClearACT.triggered.connect(self.clearLogToFile)
        self.uiClearLogACT.triggered.connect(self.clearLog)
        self.uiSaveConsoleSettingsACT.triggered.connect(
            lambda: self.recordPrefs(manual=True)
        )
        self.uiClearBeforeRunningACT.triggered.connect(self.setClearBeforeRunning)
        self.uiEditorVerticalACT.toggled.connect(self.adjustWorkboxOrientation)
        self.uiEnvironmentVarsACT.triggered.connect(self.showEnvironmentVars)
        self.uiBackupPreferencesACT.triggered.connect(self.backupPreferences)
        self.uiBrowsePreferencesACT.triggered.connect(self.browsePreferences)
        self.uiAboutPreditorACT.triggered.connect(self.show_about)
        self.uiSetFlashWindowIntervalACT.triggered.connect(self.setFlashWindowInterval)

        self.uiSetPreferredTextEditorPathACT.triggered.connect(
            self.openSetPreferredTextEditorDialog
        )

        # Tooltips - Qt4 doesn't have a ToolTipsVisible method, so we fake it
        regEx = ".*"
        menus = self.findChildren(QtWidgets.QMenu, QtCore.QRegExp(regEx))
        for menu in menus:
            menu.hovered.connect(self.handleMenuHovered)

        """Set various icons"""
        self.uiClearLogACT.setIcon(QIcon(resourcePath('img/close-thick.png')))
        self.uiNewWorkboxACT.setIcon(QIcon(resourcePath('img/file-plus.png')))
        self.uiCloseWorkboxACT.setIcon(QIcon(resourcePath('img/file-remove.png')))
        self.uiSaveConsoleSettingsACT.setIcon(
            QIcon(resourcePath('img/content-save.png'))
        )
        self.uiAboutPreditorACT.setIcon(QIcon(resourcePath('img/information.png')))
        self.uiRestartACT.setIcon(QIcon(resourcePath('img/restart.svg')))
        self.uiCloseLoggerACT.setIcon(QIcon(resourcePath('img/close-thick.png')))

        # Make action shortcuts available anywhere in the Logger
        self.addAction(self.uiClearLogACT)

        self.dont_ask_again = []

        # Load any plugins, and set window title
        self.loadPlugins()
        self.setWindowTitle(self.defineWindowTitle())

        # Start the filesystem monitor
        self.openFileMonitor = QFileSystemWatcher(self)
        self.openFileMonitor.fileChanged.connect(self.linkedFileChanged)
        self.setFileMonitoringEnabled(self.prefsPath(), True)

        self.restorePrefs()

        # add stylesheet menu options.
        for style_name in stylesheets.stylesheets():
            action = self.uiStyleMENU.addAction(style_name)
            action.setObjectName('ui{}ACT'.format(style_name))
            action.setCheckable(True)
            action.setChecked(self._stylesheet == style_name)
            action.triggered.connect(partial(self.setStyleSheet, style_name))

        self.uiConsoleTOOLBAR.show()

        self.setWorkboxFontBasedOnConsole()
        self.setEditorChooserFontBasedOnConsole()

        # Scroll thru workbox versions
        self.uiShowFirstWorkboxVersionACT.triggered.connect(
            partial(self.change_to_workbox_version_text, prefs.VersionTypes.First)
        )
        self.uiShowPreviousWorkboxVersionACT.triggered.connect(
            partial(self.change_to_workbox_version_text, prefs.VersionTypes.Previous)
        )
        self.uiShowNextWorkboxVersionACT.triggered.connect(
            partial(self.change_to_workbox_version_text, prefs.VersionTypes.Next)
        )
        self.uiShowLastWorkboxVersionACT.triggered.connect(
            partial(self.change_to_workbox_version_text, prefs.VersionTypes.Last)
        )

        self.setup_run_workbox()

        if not standalone:
            # This action only is valid when running in standalone mode
            self.uiRestartACT.setVisible(False)

        # Run the current workbox after the LoggerWindow is shown.
        if run_workbox:
            # By using two singleShot timers, we can show and draw the LoggerWindow,
            # then call execAll. This makes it easier to see what code you are running
            # before it has finished running completely.
            # QTimer.singleShot(0, lambda: QTimer.singleShot(0, self.execAll))
            QTimer.singleShot(
                0, lambda: QTimer.singleShot(0, lambda: self.run_workbox(run_workbox))
            )

    @Slot()
    def apply_options(self):
        """Apply editor options the user chose on the WorkboxPage.Options page."""
        editor_cls_name, editor_cls = plugins.editor(
            self.uiEditorChooserWGT.editor_name()
        )
        if editor_cls_name is None:
            self.update_workbox_stack()
            return
        if editor_cls_name != self.editor_cls_name:
            self.editor_cls_name = editor_cls_name
            self.uiWorkboxTAB.editor_cls = editor_cls
            # We need to change the editor, save all prefs
            self.recordPrefs(manual=True, disableFileMonitoring=True)
            # Clear the uiWorkboxTAB
            self.uiWorkboxTAB.clear()
            # Restore prefs to populate the tabs
            self.restorePrefs()

        self.update_workbox_stack()

    def autoSaveEnabled(self):
        """Whether or not AutoSave option is set

        Returns:
            bool: Whether AutoSave option is checked or not
        """
        return self.uiAutoSaveSettingssACT.isChecked()

    def setAutoSaveEnabled(self, state):
        """Set AutoSave option to state

        Args:
            state (bool): State to set AutoSave option
        """
        self.uiAutoSaveSettingssACT.setChecked(state)

    def loadPlugins(self):
        """Load any plugins that modify the LoggerWindow."""
        self.plugins = {}
        for name, plugin in plugins.loggerwindow():
            if name not in self.plugins:
                self.plugins[name] = plugin(self)

    def defineWindowTitle(self):
        """Define the window title, including and info plugins may add."""

        # Define the title
        loggerName = QApplication.instance().translate(
            'PrEditorWindow', DEFAULT_CORE_NAME
        )
        pyVersion = '{}.{}.{}'.format(*sys.version_info[:3])
        size = osystem.getPointerSize()
        title = f"{loggerName} - {self.name} - {pyVersion} {size}-bit"

        # Add any info plugins may add to title
        for _name, plugin in self.plugins.items():
            title = plugin.updateWindowTitle(title)
        return title

    def comment_toggle(self):
        self.current_workbox().__comment_toggle__()

    def current_workbox(self):
        """Returns the current workbox for the current tab group."""
        return self.uiWorkboxTAB.current_groups_widget()

    @classmethod
    def name_for_workbox(cls, workbox):
        """Returns the name for a given workbox or None if not valid.

        The name is a `WorkboxName` object showing the group and name joined by
        a `/`.

        Args:
            workbox: The workbox to get the name of. If None is passed then it
                will return the name of the current workbox.

        Returns:
            The name of the widget as a `WorkboxName` object showing the group
            and name joined by a `/`. If workbox is not valid for the LoggerWindow
            instance then None is returned.
        """

        if workbox is None:
            # if the workbox was not provided use the current workbox
            logger = cls.instance()
            index = logger.uiWorkboxTAB.currentIndex()
            group = logger.uiWorkboxTAB.tabText(index)
            group_widget = logger.uiWorkboxTAB.currentWidget()
            index = group_widget.currentIndex()
            name = group_widget.tabText(index)
            return WorkboxName(group, name)

        # Otherwise resolve from the parent widgets.
        # Get the parent QTabWidget of the workbox
        workbox_tab_widget = tab_widget_for_tab(workbox)
        if not workbox_tab_widget:
            return None
        # Get the group QTabWidget of the parent QTabWidget of the workbox
        group_widget = tab_widget_for_tab(workbox_tab_widget)
        if not group_widget:
            return None

        # Get the group name
        index = group_widget.indexOf(workbox_tab_widget)
        group = group_widget.tabText(index)

        index = workbox_tab_widget.indexOf(workbox)
        name = workbox_tab_widget.tabText(index)
        return WorkboxName(group, name)

    @classmethod
    def workbox_for_name(cls, name, show=False, visible=False):
        """Used to find a workbox for a given name. It accepts a string matching
        the "{group}/{workbox}" format, or if True, the current workbox.

        Args:
            name(str, boolean): Used to define which workbox to run.
            show (bool, optional): If a workbox is found, call `__show__` on it
                to ensure that it is initialized and its text is loaded.
            visible (bool, optional): Make the this workbox visible if found.
        """
        logger = cls.instance()

        workbox = None

        # If name is True, run the current workbox
        if isinstance(name, bool):
            if name:
                workbox = logger.current_workbox()

        # If name is a string, find first tab with that name
        elif isinstance(name, str):
            split = name.split('/', 1)
            if len(split) < 2:
                return None
            group, editor = split
            group_index = logger.uiWorkboxTAB.index_for_text(group)
            if group_index != -1:
                tab_widget = logger.uiWorkboxTAB.widget(group_index)
                index = tab_widget.index_for_text(editor)
                if index != -1:
                    workbox = tab_widget.widget(index)
                    if visible:
                        tab_widget.setCurrentIndex(index)
                        logger.uiWorkboxTAB.setCurrentIndex(group_index)

        if show and workbox:
            workbox.__show__()

        return workbox

    def workbox_for_id(self, workbox_id, show=False, visible=False):
        """Used to find a workbox for a given id.

        Args:
            workbox_id(str): The workbox id for which to match when searching
                for the workbox
            show (bool, optional): If a workbox is found, call `__show__` on it
                to ensure that it is initialized and its text is loaded.
            visible (bool, optional): Make the this workbox visible if found.
        """
        workbox = None
        for box_info in self.uiWorkboxTAB.all_widgets():
            temp_box = box_info[0]
            if temp_box.__workbox_id__() == workbox_id:
                workbox = temp_box
                break

        if workbox:
            if show:
                workbox.__show__()
            if visible:
                grp_idx, tab_idx = workbox.__group_tab_index__()
                self.uiWorkboxTAB.setCurrentIndex(grp_idx)
                group = self.uiWorkboxTAB.widget(grp_idx)
                group.setCurrentIndex(tab_idx)

        return workbox

    def run_first_workbox(self):
        workbox = self.uiWorkboxTAB.widget(0).widget(0)
        self.run_workbox("", workbox=workbox)

    @classmethod
    def run_workbox(cls, name, workbox=None):
        """This is a function which will be added to __main__, and therefore
        available to PythonLogger users. It will accept a string matching the
        "{group}/{workbox}" format, or a boolean that will run the current tab
        to support the command line launching functionality which auto-runs the
        current workbox on launch.

        Args:
            name(str, boolean): Used to define which workbox to run.

        Raises:
            Exception: "Cannot call current workbox."

        Example Usages:
            run_workbox('group_a/test')
            run_workbox('some/stuff.py')
            (from command line): blurdev launch Python_Logger --run_workbox
        """
        if workbox is None:
            workbox = cls.workbox_for_name(name)

        if workbox is not None:
            # if name is True, its ok to run the workbox, this option
            # is passed by the cli to run the current tab
            if workbox.hasFocus() and name is not True:
                raise Exception("Cannot call current workbox.")
            else:
                # Make sure the workbox text is loaded as it likely has not
                # been shown yet and each tab is now loaded only on demand.
                workbox.__show__()
                workbox.__exec_all__()

    def setup_run_workbox(self):
        """We will bind the runWordbox function on __main__, which makes is available to
        code running within PythonLogger.
        """
        __main__.run_workbox = self.run_workbox

    def change_to_workbox_version_text(self, versionType):
        """Change the current workbox's text to a previously saved version, based
        on versionType, which can be First, Previous, Next, SecondToLast, or Last.

        If we are already at the start or end of the stack of files, and trying
        to go further, do nothing.

        Args:
            versionType (prefs.VersionTypes): Enum describing which version to
                fetch

        """
        tab_group = self.uiWorkboxTAB.currentWidget()

        workbox_widget = tab_group.currentWidget()

        idx, count = prefs.get_backup_file_index_and_count(
            self.name,
            workbox_widget.__workbox_id__(),
            backup_file=workbox_widget.__backup_file__(),
        )

        # For ease of reading, set these variables.
        forFirst = versionType == prefs.VersionTypes.First
        forPrevious = versionType == prefs.VersionTypes.Previous
        forNext = versionType == prefs.VersionTypes.Next
        forLast = versionType == prefs.VersionTypes.Last
        isFirstWorkbox = idx is None or idx == 0
        isLastWorkbox = idx is None or idx + 1 == count
        isDirty = workbox_widget.__is_dirty__()

        # If we are on last workbox and it's dirty, do the user a solid, and
        # save any thing they've typed.
        if isLastWorkbox and isDirty:
            workbox_widget.__save_prefs__()
            isFirstWorkbox = False

        # If we are at either end of stack, and trying to go further, do nothing
        if isFirstWorkbox and (forFirst or forPrevious):
            return
        if isLastWorkbox and (forNext or forLast):
            return

        filename, idx, count = workbox_widget.__load_workbox_version_text__(versionType)

        # Get rid of the hash part of the filename
        match = prefs.DATETIME_PATTERN.search(filename)
        if match:
            filename = match.group()

        txt = "{} [{}/{}]".format(filename, idx, count)
        self.setStatusText(txt)
        self.autoHideStatusText()

    def openSetPreferredTextEditorDialog(self):
        dlg = SetTextEditorPathDialog(parent=self)
        self.setDialogFont(dlg)
        dlg.exec()

    def focusToConsole(self):
        """Move focus to the console"""
        self.console().setFocus()

    def focusToWorkbox(self):
        """Move focus to the current workbox"""
        self.current_workbox().setFocus()

    def copyToConsole(self):
        """Copy current selection or line from workbox to console"""
        workbox = self.current_workbox()
        if not workbox.hasFocus():
            return

        text, _line = workbox.__selected_text__(selectText=True)
        if not text:
            line, index = workbox.__cursor_position__()
            text = workbox.__text__(line)
        text = text.rstrip('\r\n')
        if not text:
            return

        cursor = self.console().textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()

        self.console().insertPlainText(text)
        self.focusToConsole()

    def copyToWorkbox(self):
        """Copy current selection or line from console to workbox"""
        console = self.console()
        if not console.hasFocus():
            return

        cursor = console.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        text = cursor.selectedText()
        prompt = console.prompt()
        if text.startswith(prompt):
            text = text[len(prompt) :]
        text = text.lstrip()

        outputPrompt = console.outputPrompt()
        outputPrompt = outputPrompt.rstrip()
        if text.startswith(outputPrompt):
            text = text[len(outputPrompt) :]
        text = text.lstrip()

        if not text:
            return

        workbox = self.current_workbox()
        workbox.__remove_selected_text__()
        workbox.__insert_text__(text)

        line, index = workbox.__cursor_position__()
        index += len(text)
        workbox.__set_cursor_position__(line, index)

        self.focusToWorkbox()

    def getNextCommand(self):
        if hasattr(self.console(), 'getNextCommand'):
            self.console().getNextCommand()

    def getPrevCommand(self):
        if hasattr(self.console(), 'getPrevCommand'):
            self.console().getPrevCommand()

    def wheelEvent(self, event):
        """adjust font size on ctrl+scrollWheel"""
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier
        shift = Qt.KeyboardModifier.ShiftModifier
        alt = Qt.KeyboardModifier.AltModifier

        ctrlAlt = ctrl | alt
        shiftAlt = shift | alt

        # Assign mods by functionality. Using shift | alt for gui, because just shift or
        # just alt has existing functionality which also processes.
        code_font_mod = ctrl

        if mods == code_font_mod or mods == self.gui_font_mod:
            # WheelEvents can be emitted in a cluster, but we only want one at a time
            # (ie to change font size by 1, rather than 2 or 3). Let's bail if previous
            # font-resize wheel event was within a certain threshhold.
            now = datetime.now()
            elapsed = now - self.previousFontResizeTime
            tolerance = timedelta(microseconds=100000)
            if elapsed < tolerance:
                return
            self.previousFontResizeTime = now

            # QT4 presents QWheelEvent.delta(), QT5 has QWheelEvent.angleDelta().y()
            if hasattr(event, 'delta'):  # Qt4
                delta = event.delta()
            else:  # QT5
                # Also holding alt reverses the data in angleDelta (!?), so transpose to
                # get correct value
                angleDelta = event.angleDelta()
                if mods == alt or mods == ctrlAlt or mods == shiftAlt:
                    angleDelta = angleDelta.transposed()
                delta = angleDelta.y()

            # convert delta to +1 or -1, depending
            delta = delta // abs(delta)
            minSize = 5
            maxSize = 50
            if mods == code_font_mod:
                font = self.console().font()
            elif mods == self.gui_font_mod:
                font = self.font()
            newSize = font.pointSize() + delta
            newSize = max(min(newSize, maxSize), minSize)

            # If only ctrl was pressed, adjust code font size, otherwise adjust gui font
            # size
            if mods == self.gui_font_mod:
                self.setGuiFont(newSize=newSize)
            elif mods == code_font_mod:
                self.setFontSize(newSize)
        else:
            Window.wheelEvent(self, event)

    def adjustFontSize(self, kind, delta):
        if kind == "Code":
            size = self.console().font().pointSize()
            size += delta
            self.setFontSize(size)
        else:
            size = self.font().pointSize()
            size += delta
            self.setGuiFont(newSize=size)

    def handleMenuHovered(self, action):
        """Qt4 doesn't have a ToolTipsVisible method, so we fake it"""
        # Don't show if it's just the text of the action
        text = re.sub(r"(?<!&)&(?!&)", "", action.text())
        text = text.replace('...', '')

        if text == action.toolTip():
            text = ''
        else:
            text = action.toolTip()

        if Qt_py.IsPyQt4:
            menu = action.parentWidget()
        else:
            menu = action.parent()
        QToolTip.showText(QCursor.pos(), text, menu)

    def selectFont(
        self, origFont=None, monospace=False, proportional=False, doGui=False
    ):
        """Present a QFontChooser dialog, offering, monospace, proportional, or all
        fonts, based on user choice. If a font is chosen, set it on the console and
        workboxes.

        Args:
            action (QAction): menu action associated with chosen font
        """
        if origFont is None:
            origFont = self.console().font()
        curFontFamily = origFont.family()

        if monospace and proportional:
            options = (
                QFontDialog.FontDialogOption.MonospacedFonts
                | QFontDialog.FontDialogOption.ProportionalFonts
            )
            kind = "monospace or proportional "
        elif monospace:
            options = QFontDialog.FontDialogOption.MonospacedFonts
            kind = "monospace "
        elif proportional:
            options = QFontDialog.FontDialogOption.ProportionalFonts
            kind = "proportional "

        # Present a QFontDialog for user to choose a font
        title = "Pick a {} font. Current font is: {}".format(kind, curFontFamily)
        newFont, okClicked = QFontDialog.getFont(origFont, self, title, options=options)

        if okClicked:
            if doGui:
                self.setGuiFont(newFont=newFont)
            else:
                self.console().setConsoleFont(newFont)
                self.setWorkboxFontBasedOnConsole()
                self.setEditorChooserFontBasedOnConsole()

    def selectGuiFont(self, monospace=True, proportional=True):
        font = self.font()
        self.selectFont(
            origFont=font, monospace=monospace, proportional=proportional, doGui=True
        )

    def setGuiFont(self, newSize=None, newFont=None):
        current = self.uiWorkboxTAB.currentWidget()
        if not current:
            return

        tabbar_class = current.tabBar().__class__
        menubar_class = self.menuBar().__class__
        label_class = self.uiStatusLBL.__class__
        children = self.findChildren(tabbar_class, None)
        children.extend(self.findChildren(menubar_class, None))
        children.extend(self.findChildren(label_class, None))
        children.extend(self.findChildren(QToolButton, None))
        children.extend(self.findChildren(QMenu, None))
        children.extend(self.findChildren(QToolTip, None))

        for child in children:
            if not hasattr(child, "setFont"):
                continue
            if newFont is None:
                newFont = child.font()
            if newSize is None:
                newSize = newFont.pointSize()
            newFont.setPointSize(newSize)
            child.setFont(newFont)
        self.setFont(newFont)
        QToolTip.setFont(newFont)

    def setFontSize(self, newSize):
        """Update the font size in the console and current workbox.

        Args:
            newSize (int): The new size to set the font
        """
        font = self.console().font()
        font.setPointSize(newSize)
        # Also setPointSizeF, which is what gets written to prefs, to prevent
        # needlessly writing prefs with only a change in pointSizeF precision.
        font.setPointSizeF(font.pointSize())

        self.console().setConsoleFont(font)

        self.setWorkboxFontBasedOnConsole()
        self.setEditorChooserFontBasedOnConsole()

    def setWorkboxFontBasedOnConsole(self, workbox=None):
        """If the current workbox's font is different to the console's font, set it to
        match.
        """
        font = self.console().font()

        if workbox is None:
            workboxGroup = self.uiWorkboxTAB.currentWidget()
            if workboxGroup is None:
                return
            workbox = workboxGroup.currentWidget()
        if workbox is None:
            return

        if workbox.__font__() != font:
            workbox.__set_margins_font__(font)
            workbox.__set_font__(font)

    def setEditorChooserFontBasedOnConsole(self):
        """Set the EditorChooser font to match console. This helps with legibility when
        using EditorChooser.
        """
        self.setDialogFont(self.uiEditorChooserWGT)

    def setDialogFont(self, dialog):
        """Helper for when creating a dialog to have the font match the PrEditor font

        Args:
            dialog (QDialog):  The dialog for which to set the font
        """
        for thing in dialog.findChildren(QObject):
            if hasattr(thing, "setFont"):
                thing.setFont(self.font())

    @classmethod
    def _genPrefName(cls, baseName, index):
        if index:
            baseName = '{name}{index}'.format(name=baseName, index=index)
        return baseName

    def adjustWorkboxOrientation(self, state):
        if state:
            self.uiSplitterSPLIT.setOrientation(Qt.Orientation.Horizontal)
        else:
            self.uiSplitterSPLIT.setOrientation(Qt.Orientation.Vertical)

    def backupPreferences(self):
        """Saves a copy of the current preferences to a zip archive."""
        zip_path = prefs.backup()
        print('PrEditor Preferences backed up to "{}"'.format(zip_path))
        return zip_path

    def browsePreferences(self):
        prefs.browse(core_name=self.name)

    def console(self):
        return self.uiConsoleTXT

    def clearLog(self):
        self.uiConsoleTXT.clear()

    def clearLogToFile(self):
        """If installLogToFile has been called, clear the stdout."""
        if self._stds:
            self._stds[0].clear(stamp=True)

    def prune_backup_files(self, sub_dir=None):
        """Prune the backup files to uiMaxNumBackupsSPIN value, per workbox

        Args:
            sub_dir (str, optional): The subdir to operate on.
        """
        if sub_dir is None:
            sub_dir = 'workboxes'

        directory = Path(prefs.prefs_path(sub_dir, core_name=self.name))
        files = list(directory.rglob("*.*"))

        files_by_name = {}
        for file in files:
            match = PRUNE_PATTERN.search(str(file))
            if not match:
                continue
            name = match.groupdict().get("name")

            parent = file.parent.name
            name = parent + "/" + name
            files_by_name.setdefault(name, []).append(file)

        for _name, files in files_by_name.items():
            files.sort(key=lambda f: str(f).lower())
            files.reverse()
            for file in files[self.max_num_backups :]:
                file.unlink()

        # Remove any empty directories
        for file in directory.iterdir():
            if not file.is_dir():
                continue

            # rmdir only operates on empty dirs. Try / except is faster than
            # getting number of files, ie len(list(file.iterdir()))
            try:
                file.rmdir()
            except OSError:
                pass

    def getBoxesChangedByInstance(self, timeOffset=0.05):
        """If a separate PrEditor instance has saved it's prefs, and we are now
        updating this instances, determine which workboxes have been changed.
        If we find some that are, save it, but fake the timestamp to be juuust
        before the new one. This way, the user retains unsaved work, and can
        still browse to the version the workbox contents.

        Args:
            timeOffset (float, optional): Description
        """
        self.latestTimeStrsForBoxesChangedViaInstance = {}

        for editor_info in self.uiWorkboxTAB.all_widgets():
            editor, group_name, tab_name, group_idx, tab_idx = editor_info
            if not editor.__is_dirty__():
                continue

            core_name = self.name
            workbox_id = editor.__workbox_id__()
            versionType = prefs.VersionTypes.Last
            latest_filepath, idx, count = prefs.get_backup_version_info(
                core_name, workbox_id, versionType
            )
            latest_filepath = prefs.get_relative_path(self.name, latest_filepath)

            if latest_filepath != editor.__backup_file__():
                stem = Path(latest_filepath).stem
                match = prefs.DATETIME_PATTERN.search(stem)
                if not match:
                    continue

                datetimeStr = match.group()
                origStamp = datetime.strptime(datetimeStr, prefs.DATETIME_FORMAT)

                newStamp = origStamp - timedelta(seconds=timeOffset)
                newStamp = newStamp.strftime(prefs.DATETIME_FORMAT)

                self.latestTimeStrsForBoxesChangedViaInstance[workbox_id] = newStamp
                editor.__set_changed_by_instance__(True)

    def setFileMonitoringEnabled(self, filename, state):
        """Enables/Disables open file change monitoring. If enabled, A dialog will pop
        up when ever the open file is changed externally. If file monitoring is
        disabled in the IDE settings it will be ignored.

        Returns:
            bool:
        """
        # if file monitoring is enabled and we have a file name then set up the file
        # monitoring
        if not filename:
            return

        if state:
            self.openFileMonitor.addPath(filename)
        else:
            self.openFileMonitor.removePath(filename)

    def fileMonitoringEnabled(self, filename):
        """Returns whether the provide filename is currently being watched, ie
        is listed in self.openFileMonitor.files()

        Args:
            filename (str): The filename to determine if being watched

        Returns:
            bool: Whether filename is being watched.
        """
        if not filename:
            return False

        watched_files = [Path(file) for file in self.openFileMonitor.files()]
        return Path(filename) in watched_files

    def prefsPath(self, name='preditor_pref.json'):
        """Get the path to this core's prefs, for the given name

        Args:
            name (str, optional): This name is appended to the found prefs path,
                defaults to 'preditor_pref.json'

        Returns:
            path (str): The determined filepath
        """
        path = prefs.prefs_path(name, core_name=self.name)
        return path

    def linkedFileChanged(self, filename):
        """Slot for responding to the file watcher's signal. Handle updating this
        PrEditor instance accordingly.

        Args:
            filename (str): The file which triggered the file changed signal
        """

        # Either handle prefs or workbox
        if Path(filename) == Path(self.prefsPath()):
            # First, save workbox prefs. Don't save preditor.prefs because that
            # would just overwrite whatever changes we are responding to.
            self.getBoxesChangedByInstance()
            self.recordWorkboxPrefs()
            # Now restore prefs, which will use the updated preditor prefs (from
            # another preditor instance)
            self.restorePrefs(skip_geom=True)
        else:
            for info in self.uiWorkboxTAB.all_widgets():
                editor, _, _, _, _ = info
                if not editor or not editor.__filename__():
                    continue
                if Path(editor.__filename__()) == Path(filename):
                    editor.__set_file_monitoring_enabled__(False)
                    choice = editor.__maybe_reload_file__()
                    if choice:
                        editor.__save_prefs__(saveLinkedFile=False, force=True)

                    filename = editor.__filename__()
                    if filename and Path(filename).is_file():
                        editor.__set_file_monitoring_enabled__(True)

    def closeEvent(self, event):
        self.recordPrefs()
        # Save the logger configuration
        lcfg = LoggingConfig(core_name=self.name)
        lcfg.build()
        lcfg.save()

        super(LoggerWindow, self).closeEvent(event)
        if self.uiConsoleTOOLBAR.isFloating():
            self.uiConsoleTOOLBAR.hide()

        # Handle any cleanup each workbox tab may need to do before closing
        for editor, _, _, _, _ in self.uiWorkboxTAB.all_widgets():
            editor.__close__()

    def closeLogger(self):
        self.close()

    def execAll(self):
        """Clears the console before executing all workbox code"""
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.current_workbox().__exec_all__()

        if self.uiAutoPromptACT.isChecked():
            console = self.console()
            prompt = console.prompt()
            console.startPrompt(prompt)

    def execSelected(self, truncate=True):
        """Clears the console before executing selected workbox code.

        NOTE! This method is not called when the uiRunSelectedACT is triggered,
        because the workbox will always intercept it. So instead, the workbox's
        keyPressEvent will notice the  shortcut and call this method.
        """

        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()

        self.current_workbox().__exec_selected__(truncate=truncate)

        if self.uiAutoPromptACT.isChecked():
            self.console().startInputLine()

    def clearExecutionTime(self):
        """Update status text with hyphens to indicate execution has begun."""
        self.setStatusText('Exec: -.- Seconds')
        QApplication.instance().processEvents()

    def reportExecutionTime(self, seconds):
        """Update status text with seconds passed in."""
        self.uiStatusLBL.showSeconds(seconds)
        self.uiMenuBar.adjustSize()

    def recordPrefs(self, manual=False, disableFileMonitoring=False):
        if not manual and not self.autoSaveEnabled():
            return

        # When applying a change to editor class, we may essentially auto-save
        # prefs, in order to reload on the next class. In doing so, we may be
        # changing workbox filename(s), if any, so let's remove them from file
        # monitoring. They will be re-added during restorePrefs.
        if disableFileMonitoring:
            for editor_info in self.uiWorkboxTAB.all_widgets():
                editor = editor_info[0]
                editor.__set_file_monitoring_enabled__(False)

        origPref = self.load_prefs()
        pref = copy.deepcopy(origPref)
        geo = self.geometry()
        pref.update(
            {
                'loggergeom': [geo.x(), geo.y(), geo.width(), geo.height()],
                'windowState': QtCompat.enumValue(self.windowState()),
                'splitterVertical': self.uiEditorVerticalACT.isChecked(),
                'splitterSize': self.uiSplitterSPLIT.sizes(),
                'tabIndent': self.uiIndentationsTabsACT.isChecked(),
                'copyIndentsAsSpaces': self.uiCopyTabsToSpacesACT.isChecked(),
                'hintingEnabled': self.uiConsoleAutoCompleteEnabledACT.isChecked(),
                'workboxHintingEnabled': (
                    self.uiWorkboxAutoCompleteEnabledACT.isChecked()
                ),
                'spellCheckEnabled': self.uiSpellCheckEnabledACT.isChecked(),
                'wordWrap': self.uiWordWrapACT.isChecked(),
                'clearBeforeRunning': self.uiClearBeforeRunningACT.isChecked(),
                'toolbarStates': str(self.saveState().toHex(), 'utf-8'),
                'guiFont': self.font().toString(),
                'consoleFont': self.console().font().toString(),
                'uiAutoSaveSettingssACT': self.autoSaveEnabled(),
                'uiAutoPromptACT': self.uiAutoPromptACT.isChecked(),
                'uiLinesInNewWorkboxACT': self.uiLinesInNewWorkboxACT.isChecked(),
                'uiErrorHyperlinksACT': self.uiErrorHyperlinksACT.isChecked(),
                'uiStatusLbl_limit': self.uiStatusLBL.limit(),
                'textEditorPath': self.textEditorPath,
                'textEditorCmdTempl': self.textEditorCmdTempl,
                'uiSeparateTracebackACT': self.uiSeparateTracebackACT.isChecked(),
                'currentStyleSheet': self._stylesheet,
                'flash_time': self.uiConsoleTXT.flash_time,
                'find_files_regex': self.uiFindInWorkboxesWGT.uiRegexBTN.isChecked(),
                'find_files_cs': (
                    self.uiFindInWorkboxesWGT.uiCaseSensitiveBTN.isChecked()
                ),
                'find_files_context': self.uiFindInWorkboxesWGT.uiContextSPN.value(),
                'find_files_text': self.uiFindInWorkboxesWGT.uiFindTXT.text(),
                'uiHighlightExactCompletionACT': (
                    self.uiHighlightExactCompletionACT.isChecked()
                ),
                'dont_ask_again': self.dont_ask_again,
                'max_num_backups': self.max_num_backups,
            }
        )

        # completer settings
        completer = self.console().completer()
        pref["caseSensitive"] = completer.caseSensitive()
        pref["completerMode"] = completer.completerMode().value

        if self._stylesheet == 'Custom':
            pref['styleSheet'] = self.styleSheet()

        workbox_prefs = self.uiWorkboxTAB.save_prefs()
        pref['workbox_prefs'] = workbox_prefs

        pref['editor_cls'] = self.editor_cls_name

        # Allow any plugins to add their own preferences dictionary
        pref["plugins"] = {}
        for name, plugin in self.plugins.items():
            plugin_pref = plugin.record_prefs(name)
            if plugin_pref:
                pref["plugins"][name] = plugin_pref

        # Only save if different from previous pref.
        if pref != origPref:
            self.save_prefs(pref)
            self.setStatusText("Prefs saved")
        else:
            self.setStatusText("No changed prefs to save")
        self.autoHideStatusText()

    def auto_backup_prefs(self, filename, onlyFirst=False):
        """Auto backup prefs for logger window itself.

        TODO: Implement method to easily scroll thru backups. Maybe difficult, due the
        myriad combinations of workboxes and workboxes version. Maybe ignore workboxes,
        and just to the dialog prefs and/or existing workbox names

        Args:
            filename (str): The filename to backup
            onlyFirst (bool, optional): Flag to create initial backup, and not
                subsequent ones. Used when dialog launched for the first time.
        """
        path = Path(filename)
        name = path.name
        stem = path.stem
        bak_path = prefs.create_stamped_path(self.name, name, sub_dir='prefs_bak')

        # If we are calling from load_prefs, onlyFirst will be True, so we can
        # autoBack the prefs the first time.
        existing = list(Path(bak_path).parent.glob("{}*.json".format(stem)))
        if onlyFirst and len(existing):
            return

        if path.is_file():
            shutil.copy(path, bak_path)

        self.setStatusText("Prefs saved")
        self.autoHideStatusText()

    def load_prefs(self):
        filename = self.prefsPath()
        self.setStatusText('Loaded Prefs: {} '.format(filename))
        self.autoHideStatusText()

        prefs_dict = {}
        self.auto_backup_prefs(filename, onlyFirst=True)
        if os.path.exists(filename):
            with open(filename) as fp:
                prefs_dict = json.load(fp)

        return prefs_dict

    def autoBackupForTransition(self, prefs_dict):
        """Since changing how workboxes are based to workbox_id is a major change,
        do a full prefs backup the first time. This is based on the prefs attr
        'prefs_version'. If less than 2.0, it will perform a full backup.

        Args:
            prefs_dict (dict): The (newly loaded) prefs.
        """
        prefs_version = prefs_dict.get("prefs_version", 1.0)
        if prefs_version < 2.0:
            self.backupPreferences()

    def transitionToNewPrefs(self, prefs_dict):
        """To facilitate renaming / changing prefs attrs, load a json dict which
        defines the changes, and then apply them. This can usually include a
        'prefs_version' attr associated with the changes.

        Args:
            prefs_dict (dict): The (newly loaded) prefs.

        Returns:
            new_prefs_dict (dict): The updated prefs dict
        """
        self.prefs_updates = prefs.get_prefs_updates()

        orig_prefs_dict = copy.deepcopy(prefs_dict)

        new_prefs_dict = prefs.update_prefs_args(
            self.name, prefs_dict, self.prefs_updates
        )

        if new_prefs_dict != orig_prefs_dict:
            self.save_prefs(new_prefs_dict, at_prefs_update=True)

        return new_prefs_dict

    def save_prefs(self, pref, at_prefs_update=False):
        # Save preferences to disk
        filename = self.prefsPath()
        path = Path(filename)
        path.parent.mkdir(exist_ok=True, parents=True)

        # Write to temp file first, then copy over, because we may have a
        # QFileSystemWatcher for the prefs file, and the 2 lines "with open"
        # and "json.dump" triggers 2 file changed signals.
        temp_stem = path.stem + "_TEMP"
        temp_name = temp_stem + path.suffix
        temp_path = path.with_name(temp_name)
        with open(temp_path, 'w') as fp:
            json.dump(pref, fp, indent=4, sort_keys=True)

        self.setFileMonitoringEnabled(self.prefsPath(), False)
        shutil.copy(temp_path, path)
        self.setFileMonitoringEnabled(self.prefsPath(), True)
        temp_path.unlink()

        self.auto_backup_prefs(filename)

        # We may have just updated prefs, and are saving that update. In this
        # case, do not prune or remove old folder, because we don't have the correct
        # max number values set yet spinner values.
        if not at_prefs_update:
            self.prune_backup_files(sub_dir='workboxes')
            self.prune_backup_files(sub_dir='prefs_bak')

    def maybeDisplayDialog(self, dialog):
        """If user hasn't previously opted to not show this particular dialog again,
        show it.
        """
        if dialog.objectName() in self.dont_ask_again:
            return

        dialog.exec()

    def restartLogger(self):
        """Closes this PrEditor instance and starts a new process with the same
        cli arguments.

        Note: This only works if PrEditor is running in standalone mode. It doesn't
        quit the QApplication or other host process. It simply closes this instance
        of PrEditor, saving its preferences, which should allow Qt to exit if no
        other windows are open.
        """
        self.close()

        # Get the current command and launch it as a new process. This handles
        # use of the preditor/preditor executable launchers.
        cmd = sys.argv[0]
        args = sys.argv[1:]

        if os.path.basename(cmd) == "__main__.py":
            # Handles using `python -m preditor` style launch.
            cmd = sys.executable
            args = ["-m", "preditor"] + args
        QtCore.QProcess.startDetached(cmd, args)

    def recordWorkboxPrefs(self):
        self.uiWorkboxTAB.save_prefs()

    def restoreWorkboxPrefs(self, pref):
        workbox_prefs = pref.get('workbox_prefs', {})
        try:
            self.uiWorkboxTAB.hide()
            self.uiWorkboxTAB.restore_prefs(workbox_prefs)
        finally:
            self.uiWorkboxTAB.show()

    def restorePrefs(self, skip_geom=False):
        pref = self.load_prefs()

        # Make changes to prefs attrs. Depending on the changes, perform a full
        # auto-backup first.
        self.autoBackupForTransition(pref)
        pref = self.transitionToNewPrefs(pref)

        workbox_path = self.prefsPath("workboxes")
        Path(workbox_path).mkdir(exist_ok=True)

        # Editor selection
        self.editor_cls_name = pref.get('editor_cls')
        if self.editor_cls_name:
            self.editor_cls_name, editor_cls = plugins.editor(self.editor_cls_name)
            self.uiWorkboxTAB.editor_cls = editor_cls
        else:
            self.uiWorkboxTAB.editor_cls = None
        # Set the workbox core_name so it reads/writes its tabs content into the
        # same core_name preference folder.
        self.uiWorkboxTAB.core_name = self.name
        self.uiEditorChooserWGT.set_editor_name(self.editor_cls_name)

        # Workboxes
        self.restoreWorkboxPrefs(pref)

        # Geometry
        if 'loggergeom' in pref and not skip_geom:
            self.setGeometry(*pref['loggergeom'])
        self.uiEditorVerticalACT.setChecked(pref.get('SplitterVertical', False))
        self.adjustWorkboxOrientation(self.uiEditorVerticalACT.isChecked())

        sizes = pref.get('SplitterSize')
        if sizes:
            self.uiSplitterSPLIT.setSizes(sizes)
        self.setWindowState(Qt.WindowState(pref.get('windowState', 0)))
        self.uiIndentationsTabsACT.setChecked(pref.get('tabIndent', True))
        self.uiCopyTabsToSpacesACT.setChecked(pref.get('copyIndentsAsSpaces', False))

        # completer settings
        self.setCaseSensitive(pref.get('caseSensitive', True))
        completerMode = CompleterMode(pref.get('completerMode', 0))
        self.cycleToCompleterMode(completerMode)
        self.setCompleterMode(completerMode)
        self.uiHighlightExactCompletionACT.setChecked(
            pref.get('uiHighlightExactCompletionACT', False)
        )

        self.setSpellCheckEnabled(self.uiSpellCheckEnabledACT.isChecked())
        self.uiSpellCheckEnabledACT.setChecked(pref.get('spellCheckEnabled', False))
        self.uiSpellCheckEnabledACT.setDisabled(False)

        self.setAutoSaveEnabled(pref.get('uiAutoSaveSettingssACT', True))

        self.uiAutoPromptACT.setChecked(pref.get('uiAutoPromptACT', False))
        self.uiLinesInNewWorkboxACT.setChecked(
            pref.get('uiLinesInNewWorkboxACT', False)
        )
        self.uiErrorHyperlinksACT.setChecked(pref.get('uiErrorHyperlinksACT', True))
        self.uiStatusLBL.setLimit(pref.get('uiStatusLbl_limit', 5))

        # Find Files settings
        self.uiFindInWorkboxesWGT.uiRegexBTN.setChecked(
            pref.get('find_files_regex', False)
        )
        self.uiFindInWorkboxesWGT.uiCaseSensitiveBTN.setChecked(
            pref.get('find_files_cs', False)
        )
        self.uiFindInWorkboxesWGT.uiContextSPN.setValue(
            pref.get('find_files_context', 3)
        )
        self.uiFindInWorkboxesWGT.uiFindTXT.setText(pref.get('find_files_text', ''))

        # External text editor filepath and command template
        defaultExePath = r"C:\Program Files\Sublime Text 3\sublime_text.exe"
        defaultCmd = r'"{exePath}" "{modulePath}":{lineNum}'
        self.textEditorPath = pref.get('textEditorPath', defaultExePath)
        self.textEditorCmdTempl = pref.get('textEditorCmdTempl', defaultCmd)

        self.uiSeparateTracebackACT.setChecked(pref.get('uiSeparateTracebackACT', True))

        self.uiWordWrapACT.setChecked(pref.get('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(pref.get('clearBeforeRunning', False))
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())

        self._stylesheet = pref.get('currentStyleSheet', 'Bright')
        if self._stylesheet == 'Custom':
            self.setStyleSheet(pref.get('styleSheet', ''))
        else:
            self.setStyleSheet(self._stylesheet)
        self.uiConsoleTXT.flash_time = pref.get('flash_time', 1.0)

        self.max_num_backups = pref.get('max_num_backups', 99)

        hintingEnabled = pref.get('hintingEnabled', True)
        self.uiConsoleAutoCompleteEnabledACT.setChecked(hintingEnabled)
        self.setAutoCompleteEnabled(hintingEnabled, console=True)
        workboxHintingEnabled = pref.get('workboxHintingEnabled', True)
        self.uiWorkboxAutoCompleteEnabledACT.setChecked(workboxHintingEnabled)
        self.setAutoCompleteEnabled(workboxHintingEnabled, console=False)

        # Ensure the correct workbox stack page is shown
        self.update_workbox_stack()

        fontStr = pref.get('consoleFont', None)
        if fontStr:
            font = QFont()
            if QtCompat.QFont.fromString(font, fontStr):
                self.console().setConsoleFont(font)

        guiFontStr = pref.get('guiFont', None)
        if guiFontStr:
            guiFont = QFont()
            if QtCompat.QFont.fromString(guiFont, guiFontStr):
                self.setGuiFont(newFont=guiFont)

        self.dont_ask_again = pref.get('dont_ask_again', [])

        # Allow any plugins to restore their own preferences
        for name, plugin in self.plugins.items():
            plugin.restore_prefs(name, pref.get("plugins", {}).get(name))

        self.restoreToolbars(pref=pref)

    def restoreToolbars(self, pref=None):
        if pref is None:
            pref = self.load_prefs()

        state = pref.get('toolbarStates', None)
        if state:
            state = QByteArray.fromHex(bytes(state, 'utf-8'))
            self.restoreState(state)

    def setAutoCompleteEnabled(self, state, console=True):
        if console:
            self.uiConsoleTXT.completer().setEnabled(state)
        else:
            for workbox, _, _, _, _ in self.uiWorkboxTAB.all_widgets():
                workbox.__set_auto_complete_enabled__(state)

    def setSpellCheckEnabled(self, state):
        try:
            self.delayable_engine.set_delayable_enabled('spell_check', state)
        except KeyError:
            # Spell check can not be enabled
            if self.isVisible():
                # Only show warning if Logger is visible and also disable the action
                self.uiSpellCheckEnabledACT.setDisabled(True)
                QMessageBox.warning(
                    self, "Spell-Check", 'Unable to activate spell check.'
                )

    def setStatusText(self, txt):
        """Set the text shown in the menu corner of the menu bar.

        Args:
            txt (str): The text to show in the status text label.
        """
        self.uiStatusLBL.setText(txt)
        self.uiMenuBar.adjustSize()

    def setupStatusTimer(self):
        # Create timer to autohide status messages
        self.statusTimer = QTimer()
        self.statusTimer.setSingleShot(True)
        self.statusTimer.setInterval(5000)
        self.statusTimer.timeout.connect(self.clearStatusText)

    def clearStatusText(self):
        """Clear any displayed status text"""
        self.uiStatusLBL.clear()
        self.uiMenuBar.adjustSize()

    def autoHideStatusText(self):
        """Set timer to automatically clear status text.

        If timer is already running, it will be automatically stopped first (We can't
        use static method QTimer.singleShot for this)
        """
        self.statusTimer.start()

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """Accepts the name of a stylesheet included with blurdev, or a full
        path to any stylesheet. If given None, it will default to Bright.
        """
        sheet = None
        if stylesheet is None:
            stylesheet = 'Bright'
        if os.path.isfile(stylesheet):
            # A path to a stylesheet was passed in
            with open(stylesheet) as f:
                sheet = f.read()
            self._stylesheet = stylesheet
        else:
            # Try to find an installed stylesheet with the given name
            sheet, valid = stylesheets.read_stylesheet(stylesheet)
            if valid:
                self._stylesheet = stylesheet
            else:
                # Assume the user passed the text of the stylesheet directly
                sheet = stylesheet
                self._stylesheet = 'Custom'

        # Load the stylesheet
        if sheet is not None:
            super(LoggerWindow, self).setStyleSheet(sheet)

        # Update the style menu
        for act in self.uiStyleMENU.actions():
            name = act.objectName()
            isCurrent = name == 'ui{}ACT'.format(self._stylesheet)
            act.setChecked(isCurrent)

        # Notify widgets that the styleSheet has changed
        self.styleSheetChanged.emit(stylesheet)

    def setCaseSensitive(self, state):
        """Set completer case-sensivity"""
        completer = self.console().completer()
        completer.setCaseSensitive(state)
        self.uiAutoCompleteCaseSensitiveACT.setChecked(state)
        self.reportCaseChange(state)
        completer.refreshList()

    def toggleCaseSensitive(self):
        """Toggle completer case-sensitivity"""
        state = self.console().completer().caseSensitive()
        self.reportCaseChange(state)
        self.setCaseSensitive(not state)

    # Completer Modes
    def cycleCompleterMode(self):
        """Cycle comleter mode"""
        completerMode = next(self.completerModeCycle)
        self.setCompleterMode(completerMode)
        self.reportCompleterModeChange(completerMode)

    def cycleToCompleterMode(self, completerMode):
        """
        Syncs the completerModeCycle iterator to currently chosen completerMode
        Args:
        completerMode: Chosen CompleterMode ENUM member
        """
        for _ in range(len(CompleterMode)):
            tempMode = next(self.completerModeCycle)
            if tempMode == completerMode:
                break

    def setCompleterMode(self, completerMode):
        """
        Set the completer mode to chosen mode
        Args:
        completerMode: Chosen CompleterMode ENUM member
        """
        completer = self.console().completer()

        completer.setCompleterMode(completerMode)
        completer.buildCompleter()

        for action in self.uiCompleterModeMENU.actions():
            action.setChecked(action.data() == completerMode)

    def selectCompleterMode(self, action):
        if not action.isChecked():
            action.setChecked(True)
            return
        """
        Handle when completer mode is chosen via menu
        Will sync mode iterator and set the completion mode
        Args:
        action: the menu action associated with the chosen mode
        """

        # update cycleToCompleterMode to current Mode
        mode = action.data()
        self.cycleToCompleterMode(mode)
        self.setCompleterMode(mode)

    def reportCaseChange(self, state):
        """Update status text with current Case Sensitivity Mode"""
        text = "Case Sensitive " if state else "Case Insensitive "
        self.setStatusText(text)
        self.autoHideStatusText()

    def reportCompleterModeChange(self, mode):
        """Update status text with current Completer Mode"""
        self.setStatusText('Completer Mode: {} '.format(mode.displayName()))
        self.autoHideStatusText()

    def setClearBeforeRunning(self, state):
        self.uiRunSelectedACT.setIcon(QIcon(resourcePath('img/playlist-play.png')))
        self.uiRunAllACT.setIcon(QIcon(resourcePath('img/play.png')))

    def setFlashWindowInterval(self):
        value = self.uiConsoleTXT.flash_time
        msg = (
            'If running code in the logger takes X seconds or longer,\n'
            'the window will flash if it is not in focus.\n'
            'Setting the value to zero will disable flashing.'
        )
        value, success = QInputDialog.getDouble(self, 'Set flash window', msg, value)
        if success:
            self.uiConsoleTXT.flash_time = value

    def setWordWrap(self, state):
        if state:
            self.uiConsoleTXT.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.uiConsoleTXT.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def show_about(self):
        """Shows `preditor.about_preditor()`'s output in a message box."""
        msg = about_preditor(instance=self)
        QMessageBox.information(self, 'About PrEditor', '<pre>{}</pre>'.format(msg))

    def showEnvironmentVars(self):
        dlg = Dialog(self)
        lyt = QVBoxLayout(dlg)
        lbl = QTextBrowser(dlg)
        lyt.addWidget(lbl)
        dlg.setWindowTitle('Blurdev Environment Variable Help')
        with open(resourcePath('environment_variables.html')) as f:
            lbl.setText(f.read().replace('\n', ''))
        dlg.setMinimumSize(600, 400)
        dlg.show()

    def showEvent(self, event):
        super(LoggerWindow, self).showEvent(event)
        self.updateIndentationsUseTabs()
        self.updateCopyIndentsAsSpaces()

        # Adjust the minimum height of the label so it's text is the same as
        # the action menu text
        height = self.uiMenuBar.actionGeometry(self.uiFileMENU.menuAction()).height()
        self.uiStatusLBL.setMinimumHeight(height)

    @Slot()
    def show_workbox_options(self):
        self.uiWorkboxSTACK.setCurrentIndex(WorkboxPages.Options)

    @Slot()
    def show_find_in_workboxes(self):
        """Ensure the find workboxes widget is visible and has focus."""
        self.uiFindInWorkboxesWGT.activate()

    @Slot()
    def show_focus_name(self):
        model = GroupTabListItemModel(manager=self.uiWorkboxTAB)
        model.process()

        def update_tab(index):
            group, tab = model.workbox_indexes_from_model_index(index)
            if group is not None:
                self.uiWorkboxTAB.set_current_groups_from_index(group, tab)

        w = FuzzySearch(model, parent=self)
        w.selected.connect(update_tab)
        w.canceled.connect(update_tab)
        w.highlighted.connect(update_tab)
        w.popup()

    def updateCopyIndentsAsSpaces(self):
        for workbox, _, _, _, _ in self.uiWorkboxTAB.all_widgets():
            workbox.__set_copy_indents_as_spaces__(
                self.uiCopyTabsToSpacesACT.isChecked()
            )

    def updateIndentationsUseTabs(self):
        for workbox, _, _, _, _ in self.uiWorkboxTAB.all_widgets():
            workbox.__set_indentations_use_tabs__(
                self.uiIndentationsTabsACT.isChecked()
            )

    @Slot()
    def update_workbox_stack(self):
        if self.uiWorkboxTAB.editor_cls:
            index = WorkboxPages.Workboxes
        else:
            index = WorkboxPages.Options

        self.uiWorkboxSTACK.setCurrentIndex(index)

    @Slot()
    def update_window_settings(self):
        self.buildClosedWorkBoxMenu()

    def shutdown(self):
        # close out of the ide system

        # if this is the global instance, then allow it to be deleted on close
        if self == LoggerWindow._instance:
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            LoggerWindow._instance = None

        # clear out the system
        self.close()

    def nextTab(self):
        """Move focus to next workbox tab"""
        tabWidget = self.uiWorkboxTAB.currentWidget()
        if not tabWidget.currentWidget().hasFocus():
            tabWidget.currentWidget().setFocus()

        index = tabWidget.currentIndex()
        if index == tabWidget.count() - 1:
            tabWidget.setCurrentIndex(0)
        else:
            tabWidget.setCurrentIndex(index + 1)

    def prevTab(self):
        """Move focus to previous workbox tab"""
        tabWidget = self.uiWorkboxTAB.currentWidget()
        if not tabWidget.currentWidget().hasFocus():
            tabWidget.currentWidget().setFocus()

        index = tabWidget.currentIndex()
        if index == 0:
            tabWidget.setCurrentIndex(tabWidget.count() - 1)
        else:
            tabWidget.setCurrentIndex(index - 1)

    def gotoGroupByIndex(self, index):
        """Generally to be used in conjunction with the Ctrl+Alt+<num> keyboard
        shortcuts, which allow user to jump directly to another tab, mimicking
        web browser functionality.
        """
        if index == -1:
            index = self.uiWorkboxTAB.count() - 1
        else:
            count = self.uiWorkboxTAB.count()
            index = min(index, count)
            index -= 1

        self.uiWorkboxTAB.setCurrentIndex(index)

    def gotoTabByIndex(self, index):
        """Generally to be used in conjunction with the Ctrl+<num> keyboard
        shortcuts, which allow user to jump directly to another tab, mimicking
        web browser functionality.
        """
        group_tab = self.uiWorkboxTAB.currentWidget()
        if index == -1:
            index = group_tab.count() - 1
        else:
            count = group_tab.count()
            index = min(index, count)
            index -= 1

        group_tab.setCurrentIndex(index)

    @staticmethod
    def instance(
        parent=None, name=None, run_workbox=False, create=True, standalone=False
    ):
        """Returns the existing instance of the PrEditor gui creating it on first call.

        Args:
            parent (QWidget, optional): If the instance hasn't been created yet, create
                it and parent it to this object.
            run_workbox (bool, optional): If the instance hasn't been created yet, this
                will execute the active workbox's code once fully initialized.
            create (bool, optional): Returns None if the instance has not been created.
            standalone (bool, optional): Launch PrEditor in standalone mode. This
                enables extra options that only make sense when it is running as
                its own app, not inside of another app.

        Returns:
            Returns a fully initialized instance of the PrEditor gui. If called more
            than once, the same instance will be returned. If create is False, it may
            return None.
        """
        # create the instance for the logger
        if not LoggerWindow._instance:
            if not create:
                return None

            # create the logger instance
            inst = LoggerWindow(
                parent, name=name, run_workbox=run_workbox, standalone=standalone
            )

            # protect the memory
            inst.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

            # cache the instance
            LoggerWindow._instance = inst

            # Allow customization when the instance is first created.
            if config.on_create_callback:
                config.on_create_callback(inst)

        return LoggerWindow._instance

    def installLogToFile(self):
        """All stdout/stderr output is also appended to this file.

        This uses preditor.debug.logToFile(path, useOldStd=True).
        """
        if self._logToFilePath is None:
            path = osystem.defaultLogFile()
            path, _ = QtCompat.QFileDialog.getSaveFileName(
                self, "Log Output to File", path
            )
            if not path:
                return
            path = os.path.normpath(path)
            print('Output logged to: "{}"'.format(path))
            debug.logToFile(path, useOldStd=True)
            # Store the std's so we can clear them later
            self._stds = (sys.stdout, sys.stderr)
            self.uiLogToFileACT.setText('Output Logged to File')
            self.uiLogToFileClearACT.setVisible(True)
            self._logToFilePath = path
        else:
            print('Output logged to: "{}"'.format(self._logToFilePath))

    @classmethod
    def instance_shutdown(cls):
        """Call shutdown the LoggerWindow instance only if it was instantiated.

        Returns:
            bool: If a shutdown was required
        """
        if cls._instance:
            try:
                cls._instance.shutdown()
            except RuntimeError as error:
                # If called after the host Qt application has been closed then
                # the instance has been deleted and we can't save preferences
                # without getting a RuntimeError about C/C++ being deleted.
                logger.warning(
                    f"instance_shutdown failed PrEditor prefs likely not saved: {error}"
                )
                return False

            return True
        return False
