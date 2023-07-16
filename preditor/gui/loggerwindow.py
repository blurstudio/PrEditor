from __future__ import absolute_import, print_function

import itertools
import json
import os
import re
import sys
import warnings
from builtins import bytes
from datetime import datetime, timedelta
from functools import partial

import __main__
import six
from Qt import QtCompat, QtCore, QtWidgets
from Qt.QtCore import QByteArray, Qt, QTimer, Signal, Slot
from Qt.QtGui import QCursor, QFont, QFontDatabase, QIcon, QTextCursor
from Qt.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QToolTip,
    QVBoxLayout,
)

from .. import (
    DEFAULT_CORE_NAME,
    about_preditor,
    core,
    debug,
    osystem,
    plugins,
    prefs,
    resourcePath,
)
from ..delayable_engine import DelayableEngine
from ..gui import Dialog, Window, loadUi
from ..logging_config import LoggingConfig
from ..utils import stylesheets
from .completer import CompleterMode
from .level_buttons import LoggingLevelButton
from .set_text_editor_path_dialog import SetTextEditorPathDialog


class WorkboxPages:
    """Nice names for the uiWorkboxSTACK indexes."""

    Options = 0
    Workboxes = 1


class LoggerWindow(Window):
    _instance = None
    styleSheetChanged = Signal(str)

    def __init__(self, parent, name=None, run_workbox=False):
        super(LoggerWindow, self).__init__(parent=parent)
        self.name = name if name else DEFAULT_CORE_NAME
        self.aboutToClearPathsEnabled = False
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
        self.uiConsoleTXT.reportExecutionTime = self.reportExecutionTime
        self.uiClearToLastPromptACT.triggered.connect(
            self.uiConsoleTXT.clearToLastPrompt
        )
        # If we don't disable this shortcut Qt won't respond to this classes or
        # the ConsolePrEdit's
        self.uiConsoleTXT.uiClearToLastPromptACT.setShortcut('')

        # create the status reporting label
        self.uiStatusLBL = QLabel(self)
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

        # Initial configuration of the logToFile feature
        self._logToFilePath = None
        self._stds = None
        self.uiLogToFileClearACT.setVisible(False)

        self.uiCloseLoggerACT.triggered.connect(self.closeLogger)

        self.uiRunAllACT.triggered.connect(self.execAll)
        self.uiRunSelectedACT.triggered.connect(self.execSelected)

        self.uiAutoCompleteEnabledACT.toggled.connect(self.setAutoCompleteEnabled)

        self.uiAutoCompleteCaseSensitiveACT.toggled.connect(self.setCaseSensitive)

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
        core.aboutToClearPaths.connect(self.pathsAboutToBeCleared)
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
        self.uiCloseLoggerACT.setIcon(QIcon(resourcePath('img/close-thick.png')))

        # Make action shortcuts available anywhere in the Logger
        self.addAction(self.uiClearLogACT)

        self.restorePrefs()

        # add font menu list
        curFamily = self.console().font().family()
        fontDB = QFontDatabase()
        fontFamilies = fontDB.families(QFontDatabase.Latin)
        monospaceFonts = [fam for fam in fontFamilies if fontDB.isFixedPitch(fam)]

        self.uiMonospaceFontMENU.clear()
        self.uiProportionalFontMENU.clear()

        for family in fontFamilies:
            if family in monospaceFonts:
                action = self.uiMonospaceFontMENU.addAction(family)
            else:
                action = self.uiProportionalFontMENU.addAction(family)
            action.setObjectName(u'ui{}FontACT'.format(family))
            action.setCheckable(True)
            action.setChecked(family == curFamily)
            action.triggered.connect(partial(self.selectFont, action))

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

        self.setup_run_workbox()

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
    def run_workbox(cls, indicator):
        """This is a function which will be added to __main__, and therefore
        available to PythonLogger users. It will accept a string matching the
        "{group}/{workbox}" format, or a boolean that will run the current tab
        to support the command line launching functionality which auto-runs the
        current workbox on launch.

        Args:
            indicator(str, boolean): Used to define which workbox to run.

        Raises:
            Exception: "Cannot call current workbox."

        Example Usages:
            run_workbox('group_a/test')
            run_workbox('some/stuff.py')
            (from command line): blurdev launch Python_Logger --run_workbox
        """
        logger = cls.instance()

        # Determine the workbox widget
        workbox = None

        # If indicator is True, run the current workbox
        if isinstance(indicator, bool):
            if indicator:
                workbox = logger.current_workbox()

        # If indicator is a string, find first tab with that name
        elif isinstance(indicator, six.string_types):
            group, editor = indicator.split('/', 1)
            index = logger.uiWorkboxTAB.index_for_text(group)
            if index != -1:
                tab_widget = logger.uiWorkboxTAB.widget(index)
                index = tab_widget.index_for_text(editor)
                if index != -1:
                    workbox = tab_widget.widget(index)

        if workbox is not None:
            # if indicator is True, its ok to run the workbox, this option
            # is passed by the cli to run the current tab
            if workbox.hasFocus() and indicator is not True:
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

        text = workbox.__selected_text__()
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
            delta = delta / abs(delta)
            minSize = 5
            maxSize = 50
            font = self.console().font()
            newSize = font.pointSize() + delta
            newSize = max(min(newSize, maxSize), minSize)

            font.setPointSize(newSize)
            self.console().setConsoleFont(font)

            for workbox in self.uiWorkboxTAB.all_widgets():
                marginsFont = workbox.__margins_font__()
                marginsFont.setPointSize(newSize)
                workbox.__set_margins_font__(marginsFont)

                workbox.__set_font__(font)
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

    def findCurrentFontAction(self):
        """Find and return current font's action"""
        actions = self.uiMonospaceFontMENU.actions()
        actions.extend(self.uiProportionalFontMENU.actions())

        action = None
        for act in actions:
            if act.isChecked():
                action = act
                break

        return action

    def selectFont(self, action):
        """Set console and workbox font to current font

        Args:
            action (QAction): menu action associated with chosen font
        """

        actions = self.uiMonospaceFontMENU.actions()
        actions.extend(self.uiProportionalFontMENU.actions())

        for act in actions:
            act.setChecked(act == action)

        family = action.text()
        font = self.console().font()
        font.setFamily(family)
        self.console().setConsoleFont(font)

        for workbox in self.uiWorkboxTAB.all_widgets():
            workbox.__set_margins_font__(font)
            workbox.__set_font__(font)

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

    def execSelected(self):
        """Clears the console before executing selected workbox code"""
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.current_workbox().__exec_selected__()

    def keyPressEvent(self, event):
        # Fix 'Maya : Qt tools lose focus' https://redmine.blur.com/issues/34430
        if event.modifiers() & (Qt.AltModifier | Qt.ControlModifier | Qt.ShiftModifier):
            pass
        else:
            super(LoggerWindow, self).keyPressEvent(event)

    def pathsAboutToBeCleared(self):
        if self.uiClearLogOnRefreshACT.isChecked():
            self.clearLog()

    def reportExecutionTime(self, seconds):
        """Update status text with seconds passed in."""
        self.setStatusText('Exec: {:0.04f} Seconds'.format(seconds))

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
                'hintingEnabled': self.uiAutoCompleteEnabledACT.isChecked(),
                'spellCheckEnabled': self.uiSpellCheckEnabledACT.isChecked(),
                'wordWrap': self.uiWordWrapACT.isChecked(),
                'clearBeforeRunning': self.uiClearBeforeRunningACT.isChecked(),
                'clearBeforeEnvRefresh': self.uiClearLogOnRefreshACT.isChecked(),
                'toolbarStates': six.text_type(self.saveState().toHex(), 'utf-8'),
                'consoleFont': self.console().font().toString(),
                'uiAutoSaveSettingssACT': self.uiAutoSaveSettingssACT.isChecked(),
                'uiAutoPromptACT': self.uiAutoPromptACT.isChecked(),
                'uiLinesInNewWorkboxACT': self.uiLinesInNewWorkboxACT.isChecked(),
                'uiErrorHyperlinksACT': self.uiErrorHyperlinksACT.isChecked(),
                'textEditorPath': self.textEditorPath,
                'textEditorCmdTempl': self.textEditorCmdTempl,
                'currentStyleSheet': self._stylesheet,
                'flash_time': self.uiConsoleTXT.flash_time,
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
        self.uiAutoCompleteEnabledACT.setChecked(pref.get('hintingEnabled', True))

        # completer settings
        self.setCaseSensitive(pref.get('caseSensitive', True))
        completerMode = CompleterMode(pref.get('completerMode', 0))
        self.cycleToCompleterMode(completerMode)
        self.setCompleterMode(completerMode)

        self.setSpellCheckEnabled(self.uiSpellCheckEnabledACT.isChecked())
        self.uiSpellCheckEnabledACT.setChecked(pref.get('spellCheckEnabled', False))
        self.uiSpellCheckEnabledACT.setDisabled(False)

        self.uiConsoleTXT.completer().setEnabled(
            self.uiAutoCompleteEnabledACT.isChecked()
        )
        self.uiAutoSaveSettingssACT.setChecked(pref.get('uiAutoSaveSettingssACT', True))

        self.uiAutoPromptACT.setChecked(pref.get('uiAutoPromptACT', False))
        self.uiLinesInNewWorkboxACT.setChecked(
            pref.get('uiLinesInNewWorkboxACT', False)
        )
        self.uiErrorHyperlinksACT.setChecked(pref.get('uiErrorHyperlinksACT', True))

        # External text editor filepath and command template
        defaultExePath = r"C:\Program Files\Sublime Text 3\sublime_text.exe"
        defaultCmd = r"{exePath} {modulePath}:{lineNum}"
        self.textEditorPath = pref.get('textEditorPath', defaultExePath)
        self.textEditorCmdTempl = pref.get('textEditorCmdTempl', defaultCmd)

        self.uiWordWrapACT.setChecked(pref.get('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(pref.get('clearBeforeRunning', False))
        self.uiClearLogOnRefreshACT.setChecked(pref.get('clearBeforeEnvRefresh', False))
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())

        self._stylesheet = pref.get('currentStyleSheet', 'Bright')
        if self._stylesheet == 'Custom':
            self.setStyleSheet(pref.get('styleSheet', ''))
        else:
            self.setStyleSheet(self._stylesheet)
        self.uiConsoleTXT.flash_time = pref.get('flash_time', 1.0)

        self.uiWorkboxTAB.restore_prefs(pref.get('workbox_prefs', {}))

        # Ensure the correct workbox stack page is shown
        self.update_workbox_stack()

        _font = pref.get('consoleFont', None)
        if _font:
            font = QFont()
            if font.fromString(_font):
                self.console().setConsoleFont(font)

    def restoreToolbars(self, pref=None):
        if pref is None:
            pref = self.load_prefs()

        state = pref.get('toolbarStates', None)
        if state:
            state = QByteArray.fromHex(bytes(state, 'utf-8'))
            self.restoreState(state)

    def setAutoCompleteEnabled(self, state):
        self.uiConsoleTXT.completer().setEnabled(state)
        for workbox in self.uiWorkboxTAB.all_widgets():
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
        self.uiStatusLBL.setText('')
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

    def updateCopyIndentsAsSpaces(self):
        for workbox in self.uiWorkboxTAB.all_widgets():
            workbox.__set_copy_indents_as_spaces__(
                self.uiCopyTabsToSpacesACT.isChecked()
            )

    def updateIndentationsUseTabs(self):
        for workbox in self.uiWorkboxTAB.all_widgets():
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
    def instance(parent=None, name=None, run_workbox=False, create=True):
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
        # create the instance for the logger
        if not LoggerWindow._instance:
            if not create:
                return None

            # create the logger instance
            inst = LoggerWindow(parent, name=name, run_workbox=run_workbox)

            # RV has a Unique window structure. It makes more sense to not parent a
            # singleton window than to parent it to a specific top level window.
            if core.objectName() == 'rv':
                inst.setParent(None)
                inst.setAttribute(Qt.WA_QuitOnClose, False)

            # protect the memory
            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            # cache the instance
            LoggerWindow._instance = inst

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
            cls._instance.shutdown()
            return True
        return False
