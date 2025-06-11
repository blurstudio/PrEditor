from __future__ import absolute_import, print_function

import itertools
import json
import logging
import os
import re
import sys
import warnings
from builtins import bytes
from datetime import datetime, timedelta
from functools import partial

import __main__
from Qt import QtCompat, QtCore, QtWidgets
from Qt.QtCore import QByteArray, Qt, QTimer, Signal, Slot
from Qt.QtGui import QCursor, QFont, QIcon, QTextCursor
from Qt.QtWidgets import (
    QApplication,
    QFontDialog,
    QInputDialog,
    QMessageBox,
    QTextBrowser,
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

logger = logging.getLogger(__name__)


class WorkboxPages:
    """Nice names for the uiWorkboxSTACK indexes."""

    Options = 0
    Workboxes = 1


class WorkboxName(str):
    """The joined name of a workbox `group/workbox` with access to its parts.

    This subclass provides properties for the group and workbox values separately.
    """

    def __new__(cls, group, workbox):
        txt = "/".join((group, workbox))
        ret = super().__new__(cls, txt)
        # Preserve the imitable nature of str's by using properties without setters.
        ret._group = group
        ret._workbox = workbox
        return ret

    @property
    def group(self):
        """The tab name of the group tab that contains the workbox."""
        return self._group

    @property
    def workbox(self):
        """The workbox of the tab for this workbox inside of the group."""
        return self._workbox


class LoggerWindow(Window):
    _instance = None
    styleSheetChanged = Signal(str)

    def __init__(self, parent, name=None, run_workbox=False, standalone=False):
        super(LoggerWindow, self).__init__(parent=parent)
        self.name = name if name else get_core_name()
        self._stylesheet = 'Bright'

        # Create timer to autohide status messages
        self.statusTimer = QTimer()
        self.statusTimer.setSingleShot(True)

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
        self._reloadRequested = set()
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
            partial(self.selectFont, monospace=True)
        )
        self.uiSelectProportionalFontACT.triggered.connect(
            partial(self.selectFont, proportional=True)
        )
        self.uiSelectAllFontACT.triggered.connect(
            partial(self.selectFont, monospace=True, proportional=True)
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
        action.setShortcut(Qt.CTRL | Qt.Key_M)
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

        # Load any plugins that modify the LoggerWindow
        self.plugins = {}
        for name, plugin in plugins.loggerwindow():
            self.plugins[name] = plugin(self)

        self.restorePrefs()

        # add stylesheet menu options.
        for style_name in stylesheets.stylesheets():
            action = self.uiStyleMENU.addAction(style_name)
            action.setObjectName('ui{}ACT'.format(style_name))
            action.setCheckable(True)
            action.setChecked(self._stylesheet == style_name)
            action.triggered.connect(partial(self.setStyleSheet, style_name))

        self.uiConsoleTOOLBAR.show()
        loggerName = QApplication.instance().translate(
            'PrEditorWindow', DEFAULT_CORE_NAME
        )
        self.setWindowTitle(
            '{} - {} - {} {}-bit'.format(
                loggerName,
                self.name,
                '{}.{}.{}'.format(*sys.version_info[:3]),
                osystem.getPointerSize(),
            )
        )

        self.setWorkboxFontBasedOnConsole()
        self.setEditorChooserFontBasedOnConsole()

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
            return
        if editor_cls_name != self.editor_cls_name:
            self.editor_cls_name = editor_cls_name
            self.uiWorkboxTAB.editor_cls = editor_cls
            # We need to change the editor, save all prefs
            self.recordPrefs()
            # Clear the uiWorkboxTAB
            self.uiWorkboxTAB.clear()
            # Restore prefs to populate the tabs
            self.restorePrefs()

        self.update_workbox_stack()

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

    @classmethod
    def run_workbox(cls, name):
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

    def openSetPreferredTextEditorDialog(self):
        dlg = SetTextEditorPathDialog(parent=self)
        dlg.exec_()

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
            cursor.select(QTextCursor.LineUnderCursor)
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
        if event.modifiers() == Qt.ControlModifier:
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
                delta = event.angleDelta().y()

            # convert delta to +1 or -1, depending
            delta = delta // abs(delta)
            minSize = 5
            maxSize = 50
            font = self.console().font()
            newSize = font.pointSize() + delta
            newSize = max(min(newSize, maxSize), minSize)

            self.setFontSize(newSize)
        else:
            Window.wheelEvent(self, event)

    def handleMenuHovered(self, action):
        """Qt4 doesn't have a ToolTipsVisible method, so we fake it"""
        # Don't show if it's just the text of the action
        text = re.sub(r"(?<!&)&(?!&)", "", action.text())
        text = text.replace('...', '')

        if text == action.toolTip():
            text = ''
        else:
            text = action.toolTip()

        menu = action.parentWidget()
        QToolTip.showText(QCursor.pos(), text, menu)

    def selectFont(self, monospace=False, proportional=False):
        """Present a QFontChooser dialog, offering, monospace, proportional, or all
        fonts, based on user choice. If a font is chosen, set it on the console and
        workboxes.

        Args:
            action (QAction): menu action associated with chosen font
        """
        origFont = self.console().font()
        curFontFamily = origFont.family()

        if monospace and proportional:
            options = QFontDialog.MonospacedFonts | QFontDialog.ProportionalFonts
            kind = "monospace or proportional "
        elif monospace:
            options = QFontDialog.MonospacedFonts
            kind = "monospace "
        elif proportional:
            options = QFontDialog.ProportionalFonts
            kind = "proportional "

        # Present a QFontDialog for user to choose a font
        title = "Pick a {} font. Current font is: {}".format(kind, curFontFamily)
        newFont, okClicked = QFontDialog.getFont(origFont, self, title, options=options)

        if okClicked:
            self.console().setConsoleFont(newFont)
            self.setWorkboxFontBasedOnConsole()
            self.setEditorChooserFontBasedOnConsole()

    def setFontSize(self, newSize):
        """Update the font size in the console and current workbox.

        Args:
            newSize (int): The new size to set the font
        """
        font = self.console().font()
        font.setPointSize(newSize)
        self.console().setConsoleFont(font)

        self.setWorkboxFontBasedOnConsole()
        self.setEditorChooserFontBasedOnConsole()

    def setWorkboxFontBasedOnConsole(self):
        """If the current workbox's font is different to the console's font, set it to
        match.
        """
        font = self.console().font()

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
        font = self.console().font()
        for child in self.uiEditorChooserWGT.children():
            if hasattr(child, "font"):
                child.setFont(font)

    @classmethod
    def _genPrefName(cls, baseName, index):
        if index:
            baseName = '{name}{index}'.format(name=baseName, index=index)
        return baseName

    def adjustWorkboxOrientation(self, state):
        if state:
            self.uiSplitterSPLIT.setOrientation(Qt.Horizontal)
        else:
            self.uiSplitterSPLIT.setOrientation(Qt.Vertical)

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

    def keyPressEvent(self, event):
        # Fix 'Maya : Qt tools lose focus' https://redmine.blur.com/issues/34430
        if event.modifiers() & (Qt.AltModifier | Qt.ControlModifier | Qt.ShiftModifier):
            pass
        else:
            super(LoggerWindow, self).keyPressEvent(event)

    def clearExecutionTime(self):
        """Update status text with hyphens to indicate execution has begun."""
        self.setStatusText('Exec: -.- Seconds')
        QApplication.instance().processEvents()

    def reportExecutionTime(self, seconds):
        """Update status text with seconds passed in."""
        self.uiStatusLBL.showSeconds(seconds)
        self.uiMenuBar.adjustSize()

    def recordPrefs(self, manual=False):
        if not manual and not self.uiAutoSaveSettingssACT.isChecked():
            return

        pref = self.load_prefs()
        geo = self.geometry()
        pref.update(
            {
                'loggergeom': [geo.x(), geo.y(), geo.width(), geo.height()],
                'windowState': int(self.windowState()),
                'SplitterVertical': self.uiEditorVerticalACT.isChecked(),
                'SplitterSize': self.uiSplitterSPLIT.sizes(),
                'tabIndent': self.uiIndentationsTabsACT.isChecked(),
                'copyIndentsAsSpaces': self.uiCopyTabsToSpacesACT.isChecked(),
                'hintingEnabled': self.uiConsoleAutoCompleteEnabledACT.isChecked(),
                'workboxHintingEnabled': (
                    self.uiWorkboxAutoCompleteEnabledACT.isChecked()
                ),
                'spellCheckEnabled': self.uiSpellCheckEnabledACT.isChecked(),
                'wordWrap': self.uiWordWrapACT.isChecked(),
                'clearBeforeRunning': self.uiClearBeforeRunningACT.isChecked(),
                'uiSelectTextACT': self.uiSelectTextACT.isChecked(),
                'toolbarStates': str(self.saveState().toHex(), 'utf-8'),
                'consoleFont': self.console().font().toString(),
                'uiAutoSaveSettingssACT': self.uiAutoSaveSettingssACT.isChecked(),
                'uiAutoPromptACT': self.uiAutoPromptACT.isChecked(),
                'uiLinesInNewWorkboxACT': self.uiLinesInNewWorkboxACT.isChecked(),
                'uiErrorHyperlinksACT': self.uiErrorHyperlinksACT.isChecked(),
                'uiStatusLbl_limit': self.uiStatusLBL.limit(),
                'textEditorPath': self.textEditorPath,
                'textEditorCmdTempl': self.textEditorCmdTempl,
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

        self.save_prefs(pref)

    def load_prefs(self):
        filename = prefs.prefs_path('preditor_pref.json', core_name=self.name)
        if os.path.exists(filename):
            with open(filename) as fp:
                return json.load(fp)
        return {}

    def save_prefs(self, pref):
        # Save preferences to disk
        filename = prefs.prefs_path('preditor_pref.json', core_name=self.name)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'w') as fp:
            json.dump(pref, fp, indent=4)

    def maybeDisplayDialog(self, dialog):
        """If user hasn't previously opted to not show this particular dialog again,
        show it.
        """
        if dialog.objectName() in self.dont_ask_again:
            return

        dialog.exec_()

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

    def restorePrefs(self):
        pref = self.load_prefs()

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

        # Geometry
        if 'loggergeom' in pref:
            self.setGeometry(*pref['loggergeom'])
        self.uiEditorVerticalACT.setChecked(pref.get('SplitterVertical', False))
        self.adjustWorkboxOrientation(self.uiEditorVerticalACT.isChecked())

        sizes = pref.get('SplitterSize')
        if sizes:
            self.uiSplitterSPLIT.setSizes(sizes)
        self.setWindowState(Qt.WindowStates(pref.get('windowState', 0)))
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

        self.uiAutoSaveSettingssACT.setChecked(pref.get('uiAutoSaveSettingssACT', True))

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

        self.uiWordWrapACT.setChecked(pref.get('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(pref.get('clearBeforeRunning', False))
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())
        self.uiSelectTextACT.setChecked(pref.get('uiSelectTextACT', True))

        self._stylesheet = pref.get('currentStyleSheet', 'Bright')
        if self._stylesheet == 'Custom':
            self.setStyleSheet(pref.get('styleSheet', ''))
        else:
            self.setStyleSheet(self._stylesheet)
        self.uiConsoleTXT.flash_time = pref.get('flash_time', 1.0)

        self.uiWorkboxTAB.restore_prefs(pref.get('workbox_prefs', {}))

        hintingEnabled = pref.get('hintingEnabled', True)
        self.uiConsoleAutoCompleteEnabledACT.setChecked(hintingEnabled)
        self.setAutoCompleteEnabled(hintingEnabled, console=True)
        workboxHintingEnabled = pref.get('workboxHintingEnabled', True)
        self.uiWorkboxAutoCompleteEnabledACT.setChecked(workboxHintingEnabled)
        self.setAutoCompleteEnabled(workboxHintingEnabled, console=False)

        # Ensure the correct workbox stack page is shown
        self.update_workbox_stack()

        _font = pref.get('consoleFont', None)
        if _font:
            font = QFont()
            if font.fromString(_font):
                self.console().setConsoleFont(font)

        self.dont_ask_again = pref.get('dont_ask_again', [])

        # Allow any plugins to restore their own preferences
        for name, plugin in self.plugins.items():
            plugin.restore_prefs(name, pref.get("plugins", {}).get(name))

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

    def clearStatusText(self):
        """Clear any displayed status text"""
        self.uiStatusLBL.clear()
        self.uiMenuBar.adjustSize()

    def autoHideStatusText(self):
        """Set timer to automatically clear status text"""
        if self.statusTimer.isActive():
            self.statusTimer.stop()
        self.statusTimer.singleShot(2000, self.clearStatusText)
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
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.WidgetWidth)
        else:
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.NoWrap)

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
        self.restoreToolbars()
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

    def shutdown(self):
        # close out of the ide system

        # if this is the global instance, then allow it to be deleted on close
        if self == LoggerWindow._instance:
            self.setAttribute(Qt.WA_DeleteOnClose, True)
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
            inst.setAttribute(Qt.WA_DeleteOnClose, False)

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
