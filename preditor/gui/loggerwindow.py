from __future__ import absolute_import, print_function

import itertools
import json
import os
import re
import sys
import time
import warnings
from datetime import datetime, timedelta
from functools import partial

import __main__
import six
from Qt import QtCompat, QtCore, QtWidgets
from Qt.QtCore import (
    QByteArray,
    QFileInfo,
    QFileSystemWatcher,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from Qt.QtGui import QCursor, QFont, QFontDatabase, QIcon, QTextCursor
from Qt.QtWidgets import (
    QApplication,
    QFileIconProvider,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QSpinBox,
    QTextBrowser,
    QToolTip,
    QVBoxLayout,
)

from .. import core, debug, osystem, resourcePath
from ..gui import Dialog, Window, loadUi
from ..logger import saveLoggerConfiguration
from ..prefs import prefs_path
from ..scintilla.delayable_engine import DelayableEngine
from ..utils import stylesheets
from .completer import CompleterMode
from .level_buttons import DebugLevelButton, LoggingLevelButton
from .set_text_editor_path_dialog import SetTextEditorPathDialog
from .workboxwidget import WorkboxWidget


class LoggerWindow(Window):
    _instance = None
    styleSheetChanged = Signal(str)

    def __init__(self, parent, runWorkbox=False):
        super(LoggerWindow, self).__init__(parent=parent)
        self.aboutToClearPathsEnabled = False
        self._stylesheet = 'Bright'

        # Create timer to autohide status messages
        self.statusTimer = QTimer()
        self.statusTimer.setSingleShot(True)

        # Store the previous time a font-resize wheel event was triggered to prevent
        # rapid-fire WheelEvents. Initialize to the current time.
        self.previousFontResizeTime = datetime.now()

        self.setWindowIcon(QIcon(resourcePath('img/python_logger.png')))
        loadUi(__file__, self)

        self.uiConsoleTXT.flash_window = self
        self.uiConsoleTXT.pdbModeAction = self.uiPdbModeACT
        self.uiConsoleTXT.pdbUpdateVisibility = self.updatePdbVisibility
        self.updatePdbVisibility(False)
        self.uiConsoleTXT.reportExecutionTime = self.reportExecutionTime
        self.uiClearToLastPromptACT.triggered.connect(
            self.uiConsoleTXT.clearToLastPrompt
        )
        # If we don't disable this shortcut Qt won't respond to this classes or the
        # ConsoleEdit's
        self.uiConsoleTXT.uiClearToLastPromptACT.setShortcut('')

        # create the status reporting label
        self.uiStatusLBL = QLabel(self)
        self.uiMenuBar.setCornerWidget(self.uiStatusLBL)

        # create the workbox tabs
        self._currentTab = -1
        self._reloadRequested = set()
        # Setup delayable system
        self.delayable_engine = DelayableEngine.instance('logger', self)
        self.delayable_engine.set_delayable_enabled('smart_highlight', True)
        # Connect the tab widget signals
        self.uiWorkboxTAB.addTabClicked.connect(self.addWorkbox)
        self.uiWorkboxTAB.tabCloseRequested.connect(self.removeWorkbox)
        self.uiWorkboxTAB.currentChanged.connect(self.currentChanged)
        self.uiWorkboxTAB.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.uiWorkboxTAB.tabBar().customContextMenuRequested.connect(
            self.workboxTabRightClick
        )
        # create the default workbox
        self.uiWorkboxWGT = self.addWorkbox(self.uiWorkboxTAB)

        # Create additional buttons in toolbar.
        self.uiDebugLevelBTN = DebugLevelButton(self)
        self.uiConsoleTOOLBAR.insertWidget(
            self.uiRunSelectedACT,
            self.uiDebugLevelBTN,
        )
        self.uiLoggingLevelBTN = LoggingLevelButton(self)
        self.uiConsoleTOOLBAR.insertWidget(
            self.uiRunSelectedACT,
            self.uiLoggingLevelBTN,
        )
        self.uiConsoleTOOLBAR.insertSeparator(self.uiRunSelectedACT)

        # create the pdb count widget
        self._pdbContinue = None
        self.uiPdbExecuteCountLBL = QLabel('x', self.uiPdbTOOLBAR)
        self.uiPdbExecuteCountLBL.setObjectName('uiPdbExecuteCountLBL')
        self.uiPdbTOOLBAR.addWidget(self.uiPdbExecuteCountLBL)
        self.uiPdbExecuteCountDDL = QSpinBox(self.uiPdbTOOLBAR)
        self.uiPdbExecuteCountDDL.setObjectName('uiPdbExecuteCountDDL')
        self.uiPdbExecuteCountDDL.setValue(1)
        self.uiPdbExecuteCountDDL.setRange(1, 10000)
        msg = (
            'When the "next" and "step" buttons are pressed call them this many times.'
        )
        self.uiPdbExecuteCountDDL.setToolTip(msg)
        self.uiPdbTOOLBAR.addWidget(self.uiPdbExecuteCountDDL)

        # Initial configuration of the logToFile feature
        self._logToFilePath = None
        self._stds = None
        self.uiLogToFileClearACT.setVisible(False)

        self.uiCloseLoggerACT.triggered.connect(self.closeLogger)

        self.uiRunAllACT.triggered.connect(self.execAll)
        self.uiRunSelectedACT.triggered.connect(self.execSelected)
        self.uiPdbModeACT.triggered.connect(self.uiConsoleTXT.setPdbMode)

        self.uiPdbContinueACT.triggered.connect(self.uiConsoleTXT.pdbContinue)
        self.uiPdbStepACT.triggered.connect(partial(self.pdbRepeat, 'next'))
        self.uiPdbNextACT.triggered.connect(partial(self.pdbRepeat, 'step'))
        self.uiPdbUpACT.triggered.connect(self.uiConsoleTXT.pdbUp)
        self.uiPdbDownACT.triggered.connect(self.uiConsoleTXT.pdbDown)

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
        self.uiNewWorkboxACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_N)
        self.uiNewWorkboxACT.triggered.connect(lambda: self.addWorkbox())
        self.uiCloseWorkboxACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_W)
        self.uiCloseWorkboxACT.triggered.connect(
            lambda: self.removeWorkbox(self.uiWorkboxTAB.currentIndex())
        )

        # Browse previous commands
        self.uiGetPrevCmdACT.setShortcut(Qt.ALT | Qt.Key_Up)
        self.uiGetPrevCmdACT.triggered.connect(self.getPrevCommand)
        self.uiGetNextCmdACT.setShortcut(Qt.ALT | Qt.Key_Down)
        self.uiGetNextCmdACT.triggered.connect(self.getNextCommand)

        # Focus to console or to workbox, optionally copy seleciton or line
        self.uiFocusToConsoleACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_PageUp)
        self.uiFocusToConsoleACT.triggered.connect(self.focusToConsole)
        self.uiCopyToConsoleACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.ALT | Qt.Key_PageUp)
        self.uiCopyToConsoleACT.triggered.connect(self.copyToConsole)
        self.uiFocusToWorkboxACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_PageDown)
        self.uiFocusToWorkboxACT.triggered.connect(self.focusToWorkbox)
        self.uiCopyToWorkboxACT.setShortcut(
            Qt.CTRL | Qt.SHIFT | Qt.ALT | Qt.Key_PageDown
        )
        self.uiCopyToWorkboxACT.triggered.connect(self.copyToWorkbox)

        # Navigate workbox tabs
        self.uiNextTabACT.setShortcut(Qt.CTRL | Qt.Key_Tab)
        self.uiNextTabACT.triggered.connect(self.nextTab)
        self.uiPrevTabACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_Tab)
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

        self.uiTab1ACT.setShortcut(Qt.CTRL | Qt.Key_1)
        self.uiTab2ACT.setShortcut(Qt.CTRL | Qt.Key_2)
        self.uiTab3ACT.setShortcut(Qt.CTRL | Qt.Key_3)
        self.uiTab4ACT.setShortcut(Qt.CTRL | Qt.Key_4)
        self.uiTab5ACT.setShortcut(Qt.CTRL | Qt.Key_5)
        self.uiTab6ACT.setShortcut(Qt.CTRL | Qt.Key_6)
        self.uiTab7ACT.setShortcut(Qt.CTRL | Qt.Key_7)
        self.uiTab8ACT.setShortcut(Qt.CTRL | Qt.Key_8)
        self.uiTabLastACT.setShortcut(Qt.CTRL | Qt.Key_9)

        self.uiCommentToggleACT.setShortcut(Qt.CTRL | Qt.Key_Slash)
        self.uiCommentToggleACT.triggered.connect(self.commentToggle)

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
        self.uiBrowsePreferencesACT.triggered.connect(self.browsePreferences)
        self.uiAboutBlurdevACT.triggered.connect(self.showAbout)
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

        self.uiClearLogACT.setIcon(QIcon(resourcePath('img/logger/clear.png')))
        self.uiSaveConsoleSettingsACT.setIcon(
            QIcon(resourcePath('img/logger/save.png'))
        )
        self.uiAboutBlurdevACT.setIcon(QIcon(resourcePath('img/logger/about.png')))
        self.uiCloseLoggerACT.setIcon(QIcon(resourcePath('img/logger/close.png')))

        self.uiPdbContinueACT.setIcon(QIcon(resourcePath('img/logger/play.png')))
        self.uiPdbStepACT.setIcon(QIcon(resourcePath('img/logger/arrow_forward.png')))
        self.uiPdbNextACT.setIcon(
            QIcon(resourcePath('img/logger/subdirectory_arrow_right.png'))
        )
        self.uiPdbUpACT.setIcon(QIcon(resourcePath('img/logger/up.png')))
        self.uiPdbDownACT.setIcon(QIcon(resourcePath('img/logger/down.png')))

        # Setting toolbar icon size.

        self.uiConsoleTOOLBAR.setIconSize(QSize(18, 18))

        # Start the filesystem monitor
        self._openFileMonitor = QFileSystemWatcher(self)
        self._openFileMonitor.fileChanged.connect(self.linkedFileChanged)

        # Make action shortcuts available anywhere in the Logger
        self.addAction(self.uiClearLogACT)

        # calling setLanguage resets this value to False
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
        for style_name in stylesheets.stylesheets('logger'):
            action = self.uiStyleMENU.addAction(style_name)
            action.setObjectName('ui{}ACT'.format(style_name))
            action.setCheckable(True)
            action.setChecked(self._stylesheet == style_name)
            action.triggered.connect(partial(self.setStyleSheet, style_name))

        self.uiConsoleTOOLBAR.show()
        loggerName = QApplication.instance().translate('PrEditorWindow', 'PrEditor')
        self.setWindowTitle(
            '%s - %s - %s %i-bit'
            % (
                loggerName,
                core.objectName().capitalize(),
                '%i.%i.%i' % sys.version_info[:3],
                osystem.getPointerSize(),
            )
        )

        self.setupRunWorkbox()

        # Run the current workbox after the LoggerWindow is shown.
        if runWorkbox:
            # By using two singleShot timers, we can show and draw the LoggerWindow,
            # then call execAll. This makes it easier to see what code you are running
            # before it has finished running completely.
            # QTimer.singleShot(0, lambda: QTimer.singleShot(0, self.execAll))
            QTimer.singleShot(
                0, lambda: QTimer.singleShot(0, lambda: self.runWorkbox(runWorkbox))
            )

    def commentToggle(self):
        self.uiWorkboxTAB.currentWidget().commentToggle()

    def runWorkbox(self, indicator):
        """This is a function which will be added to __main__, and therefore available
        to PythonLogger users. It will accept a python-like index (positive or
        negative), a string representing the name of the chosen Workbox, or a boolean
        which support existing command line launching functionality which will auto-run
        the last workbox up launch.

        Args:
            indicator(int, str, boolean): Used to define which workbox to run.

        Raises:
            Exception: "Cannot call current workbox."

        Example Usages:
            runWorkbox(3)
            runWorkbox(-2)
            runWorkbox('test')
            runWorkbox('stuff.py')

            (from command line): blurdev launch Python_Logger --run_workbox

        """
        pyLogger = core.logger()
        workboxTab = pyLogger.uiWorkboxTAB
        workboxCount = workboxTab.count()

        # Determine workbox index
        index = None

        # If indicator is True, run the current workbox
        if isinstance(indicator, bool):
            if indicator:
                index = workboxCount - 1
        # If indicator is an int, use as normal python index
        elif isinstance(indicator, int):
            if indicator < 0:
                num = workboxCount + indicator
            else:
                num = indicator
            if num >= 0 and num < workboxCount:
                index = num
        # If indicator is a string, find first tab with that name
        elif isinstance(indicator, six.string_types):
            for i in range(workboxCount):
                if workboxTab.tabText(i) == indicator:
                    index = i
                    break
        if index is not None:
            workbox = workboxTab.widget(index)
            # if indicator is True, its ok to run the workbox, this option
            # is passed by the cli to run the current tab
            if workbox.hasFocus() and indicator is not True:
                raise Exception("Cannot call current workbox.")
            else:
                workbox.execAll()

    def setupRunWorkbox(self):
        """We will bind the runWordbox function on __main__, which makes is available to
        code running within PythonLogger.
        """
        __main__.runWorkbox = self.runWorkbox

    def openSetPreferredTextEditorDialog(self):
        dlg = SetTextEditorPathDialog(parent=self)
        dlg.exec_()

    def focusToConsole(self):
        """Move focus to the console"""
        self.console().setFocus()

    def focusToWorkbox(self):
        """Move focus to the current workbox"""
        self.uiWorkboxTAB.currentWidget().setFocus()

    def copyToConsole(self):
        """Copy current selection or line from workbox to console"""
        workbox = self.uiWorkboxTAB.currentWidget()
        if not workbox.hasFocus():
            return

        text = workbox.selectedText()
        if not text:
            line, index = workbox.getCursorPosition()
            text = workbox.text(line)
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

        workbox = self.uiWorkboxTAB.currentWidget()
        workbox.removeSelectedText()
        workbox.insert(text)

        line, index = workbox.getCursorPosition()
        index += len(text)
        workbox.setCursorPosition(line, index)

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

            for index in range(self.uiWorkboxTAB.count()):
                workbox = self.uiWorkboxTAB.widget(index)

                marginsFont = workbox.marginsFont()
                marginsFont.setPointSize(newSize)
                workbox.setMarginsFont(marginsFont)

                workbox.setWorkboxFont(font)
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
        """
        Set console and workbox font to current font
        Args:
        action: menu action associated with chosen font
        """

        actions = self.uiMonospaceFontMENU.actions()
        actions.extend(self.uiProportionalFontMENU.actions())

        for act in actions:
            act.setChecked(act == action)

        family = action.text()
        font = self.console().font()
        font.setFamily(family)
        self.console().setConsoleFont(font)

        for index in range(self.uiWorkboxTAB.count()):
            workbox = self.uiWorkboxTAB.widget(index)

            workbox.documentFont = font
            workbox.setMarginsFont(font)
            workbox.setWorkboxFont(font)

    @classmethod
    def _genPrefName(cls, baseName, index):
        if index:
            baseName = '{name}{index}'.format(name=baseName, index=index)
        return baseName

    def addWorkbox(self, tabWidget=None, title='Workbox', closable=True):
        if tabWidget is None:
            tabWidget = self.uiWorkboxTAB
        workbox = WorkboxWidget(tabWidget, delayable_engine=self.delayable_engine.name)
        workbox.setConsole(self.uiConsoleTXT)
        workbox.setMinimumHeight(1)
        index = tabWidget.addTab(workbox, title)
        workbox.setLanguage('Python')

        # update the lexer
        fontAction = self.findCurrentFontAction()
        if fontAction is not None:
            self.selectFont(fontAction)
        else:
            workbox.setMarginsFont(workbox.font())

        if closable:
            # If only one tab is visible, don't show the close tab button
            tabWidget.setTabsClosable(tabWidget.count() != 1)
        tabWidget.setCurrentIndex(index)
        workbox.setIndentationsUseTabs(self.uiIndentationsTabsACT.isChecked())
        workbox.copyIndentsAsSpaces = self.uiCopyTabsToSpacesACT.isChecked()

        workbox.setFocus()
        if self.uiLinesInNewWorkboxACT.isChecked():
            workbox.setText("\n" * 19)

        return workbox

    def adjustWorkboxOrientation(self, state):
        if state:
            self.uiSplitterSPLIT.setOrientation(Qt.Horizontal)
        else:
            self.uiSplitterSPLIT.setOrientation(Qt.Vertical)

    def browsePreferences(self):
        path = prefs_path()
        osystem.explore(path)

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
        saveLoggerConfiguration()

        Window.closeEvent(self, event)
        if self.uiConsoleTOOLBAR.isFloating():
            self.uiConsoleTOOLBAR.hide()

    def closeLogger(self):
        self.close()

    def execAll(self):
        """Clears the console before executing all workbox code"""
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execAll()

        if self.uiAutoPromptACT.isChecked():
            console = self.console()
            prompt = console.prompt()
            console.startPrompt(prompt)

    def execSelected(self):
        """Clears the console before executing selected workbox code"""
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execSelected()

    def keyPressEvent(self, event):
        # Fix 'Maya : Qt tools lose focus' https://redmine.blur.com/issues/34430
        if event.modifiers() & (Qt.AltModifier | Qt.ControlModifier | Qt.ShiftModifier):
            pass
        else:
            super(LoggerWindow, self).keyPressEvent(event)

    def pdbRepeat(self, commandText):
        # If we need to repeat the command store that info
        value = self.uiPdbExecuteCountDDL.value()
        if value > 1:
            # The first request is triggered at the end of this function, so we need to
            # store one less than requested
            self._pdbContinue = (value - 1, commandText)
        else:
            self._pdbContinue = None
        # Send the first command
        self.uiConsoleTXT.pdbSendCommand(commandText)

    def pathsAboutToBeCleared(self):
        if self.uiClearLogOnRefreshACT.isChecked():
            self.clearLog()

    def reportExecutionTime(self, seconds):
        """Update status text with seconds passed in."""
        self.setStatusText('Exec: {:0.04f} Seconds'.format(seconds))

    def recordPrefs(self, manual=False):
        if not manual and not self.uiAutoSaveSettingssACT.isChecked():
            return

        _prefs = self.load_prefs()
        geo = self.geometry()
        _prefs.update(
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
                'toolbarStates': str(self.saveState().toHex(), 'utf-8'),
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
        _prefs["caseSensitive"] = completer.caseSensitive()
        _prefs["completerMode"] = completer.completerMode().value

        for index in range(self.uiWorkboxTAB.count()):
            workbox = self.uiWorkboxTAB.widget(index)
            _prefs[self._genPrefName('WorkboxText', index)] = workbox.text()
            lexer = workbox.lexer()
            if lexer:
                font = lexer.font(0)
            else:
                font = workbox.font()
            _prefs[self._genPrefName('workboxFont', index)] = font.toString()
            _prefs[
                self._genPrefName('workboxMarginFont', index)
            ] = workbox.marginsFont().toString()
            _prefs[
                self._genPrefName('workboxTabTitle', index)
            ] = self.uiWorkboxTAB.tabBar().tabText(index)

            linkPath = ''
            if workbox._fileMonitoringActive:
                linkPath = workbox.filename()
                if os.path.isfile(linkPath):
                    workbox.save()
                else:
                    self.unlinkTab(index)

            _prefs[self._genPrefName('workboxPath', index)] = linkPath

        _prefs['WorkboxCount'] = self.uiWorkboxTAB.count()
        _prefs['WorkboxCurrentIndex'] = self.uiWorkboxTAB.currentIndex()

        if self._stylesheet == 'Custom':
            _prefs['styleSheet'] = self.styleSheet()

        self.save_prefs(_prefs)

    def load_prefs(self):
        filename = prefs_path('logger_pref.json')
        if os.path.exists(filename):
            with open(filename) as fp:
                return json.load(fp)
        return {}

    def save_prefs(self, _prefs):
        # Save preferences to disk
        filename = prefs_path('logger_pref.json')
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'w') as fp:
            json.dump(_prefs, fp, indent=4)

    def restorePrefs(self):
        prefs = self.load_prefs()

        if 'loggergeom' in prefs:
            self.setGeometry(*prefs['loggergeom'])
        self.uiEditorVerticalACT.setChecked(prefs.get('SplitterVertical', False))
        self.adjustWorkboxOrientation(self.uiEditorVerticalACT.isChecked())

        sizes = prefs.get('SplitterSize')
        if sizes:
            self.uiSplitterSPLIT.setSizes(sizes)
        self.setWindowState(Qt.WindowStates(prefs.get('windowState', 0)))
        self.uiIndentationsTabsACT.setChecked(prefs.get('tabIndent', True))
        self.uiCopyTabsToSpacesACT.setChecked(prefs.get('copyIndentsAsSpaces', False))
        self.uiAutoCompleteEnabledACT.setChecked(prefs.get('hintingEnabled', True))

        # completer settings
        self.setCaseSensitive(prefs.get('caseSensitive', True))
        completerMode = CompleterMode(prefs.get('completerMode', 0))
        self.cycleToCompleterMode(completerMode)
        self.setCompleterMode(completerMode)

        self.setSpellCheckEnabled(self.uiSpellCheckEnabledACT.isChecked())
        self.uiSpellCheckEnabledACT.setChecked(prefs.get('spellCheckEnabled', False))
        self.uiConsoleTXT.completer().setEnabled(
            self.uiAutoCompleteEnabledACT.isChecked()
        )
        self.uiAutoSaveSettingssACT.setChecked(
            prefs.get('uiAutoSaveSettingssACT', True)
        )

        self.uiAutoPromptACT.setChecked(prefs.get('uiAutoPromptACT', False))
        self.uiLinesInNewWorkboxACT.setChecked(
            prefs.get('uiLinesInNewWorkboxACT', False)
        )
        self.uiErrorHyperlinksACT.setChecked(prefs.get('uiErrorHyperlinksACT', True))

        # External text editor filepath and command template
        defaultExePath = r"C:\Program Files\Sublime Text 3\sublime_text.exe"
        defaultCmd = r"{exePath} {modulePath}:{lineNum}"
        self.textEditorPath = prefs.get('textEditorPath', defaultExePath)
        self.textEditorCmdTempl = prefs.get('textEditorCmdTempl', defaultCmd)

        self.uiWordWrapACT.setChecked(prefs.get('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(prefs.get('clearBeforeRunning', False))
        self.uiClearLogOnRefreshACT.setChecked(
            prefs.get('clearBeforeEnvRefresh', False)
        )
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())

        _font = prefs.get('consoleFont', None)
        if _font:
            font = QFont()
            if font.fromString(_font):
                self.console().setConsoleFont(font)

        # Restore the workboxes
        count = prefs.get('WorkboxCount', 1)
        for _ in range(count - self.uiWorkboxTAB.count()):
            # create each of the workbox tabs
            self.addWorkbox(self.uiWorkboxTAB)
        for index in range(count):
            workbox = self.uiWorkboxTAB.widget(index)
            workbox.setText(prefs.get(self._genPrefName('WorkboxText', index), ''))

            workboxPath = prefs.get(self._genPrefName('workboxPath', index), '')
            if os.path.isfile(workboxPath):
                self.linkTab(index, workboxPath)

            _font = prefs.get(self._genPrefName('workboxFont', index), None)
            if _font:
                font = QFont()
                if font.fromString(_font):
                    lexer = workbox.lexer()
                    if lexer:
                        font = lexer.setFont(font)
                    else:
                        font = workbox.setFont(font)
            _font = prefs.get(self._genPrefName('workboxMarginFont', index), None)
            if _font:
                font = QFont()
                if font.fromString(_font):
                    workbox.setMarginsFont(font)
            tabText = prefs.get(self._genPrefName('workboxTabTitle', index), 'Workbox')
            self.uiWorkboxTAB.tabBar().setTabText(index, tabText)

        self.uiWorkboxTAB.setCurrentIndex(prefs.get('WorkboxCurrentIndex', 0))

        self._stylesheet = prefs.get('currentStyleSheet', 'Bright')
        if self._stylesheet == 'Custom':
            self.setStyleSheet(prefs.get('styleSheet', ''))
        else:
            self.setStyleSheet(self._stylesheet)
        self.uiConsoleTXT.flash_time = prefs.get('flash_time', 1.0)

        self.restoreToolbars(prefs=prefs)

    def restoreToolbars(self, prefs=None):
        if prefs is None:
            prefs = self.load_prefs()

        state = prefs.get('toolbarStates', None)
        if state:
            state = QByteArray.fromHex(bytes(state, 'utf-8'))
            self.restoreState(state)
            # Ensure uiPdbTOOLBAR respects the current pdb mode
            self.uiConsoleTXT.setPdbMode(self.uiConsoleTXT.pdbMode())

    def removeWorkbox(self, index):
        if self.uiWorkboxTAB.count() == 1:
            msg = "You have to leave at least one tab open."
            QMessageBox.critical(self, 'Tab can not be closed.', msg, QMessageBox.Ok)
            return
        msg = (
            "Would you like to donate this tabs contents to the "
            "/dev/null fund for wayward code?"
        )
        if (
            QMessageBox.question(
                self, 'Donate to the cause?', msg, QMessageBox.Yes | QMessageBox.Cancel
            )
            == QMessageBox.Yes
        ):
            self.uiWorkboxTAB.removeTab(index)
        self.uiWorkboxTAB.setTabsClosable(self.uiWorkboxTAB.count() != 1)

    def setAutoCompleteEnabled(self, state):
        self.uiConsoleTXT.completer().setEnabled(state)
        for index in range(self.uiWorkboxTAB.count()):
            tab = self.uiWorkboxTAB.widget(index)
            if state:
                tab.setAutoCompletionSource(tab.AcsAll)
            else:
                tab.setAutoCompletionSource(tab.AcsNone)

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
            sheet, valid = stylesheets.read_stylesheet('logger/{}'.format(stylesheet))
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
        self.uiRunSelectedACT.setIcon(
            QIcon(resourcePath('img/logger/playlist_play.png'))
        )
        self.uiRunAllACT.setIcon(QIcon(resourcePath('img/logger/play.png')))

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

    def showAbout(self):
        msg = core.aboutBlurdev()
        QMessageBox.information(self, 'About blurdev', msg)

    def showEnvironmentVars(self):
        dlg = Dialog(core.logger())
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

    def updateCopyIndentsAsSpaces(self):
        for index in range(self.uiWorkboxTAB.count()):
            tab = self.uiWorkboxTAB.widget(index)
            tab.copyIndentsAsSpaces = self.uiCopyTabsToSpacesACT.isChecked()

    def updateIndentationsUseTabs(self):
        for index in range(self.uiWorkboxTAB.count()):
            tab = self.uiWorkboxTAB.widget(index)
            tab.setIndentationsUseTabs(self.uiIndentationsTabsACT.isChecked())

    def updatePdbVisibility(self, state):
        self.uiPdbMENU.menuAction().setVisible(state)
        self.uiPdbTOOLBAR.setVisible(state)
        self.uiWorkboxSTACK.setCurrentIndex(1 if state else 0)

    def shutdown(self):
        # close out of the ide system

        # if this is the global instance, then allow it to be deleted on close
        if self == LoggerWindow._instance:
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            LoggerWindow._instance = None

        # clear out the system
        self.close()

    def workboxTabRightClick(self, pos):
        self._currentTab = self.uiWorkboxTAB.tabBar().tabAt(pos)
        if self._currentTab == -1:
            return
        menu = QMenu(self.uiWorkboxTAB.tabBar())
        act = menu.addAction('Rename')
        act.triggered.connect(self.renameTab)
        act = menu.addAction('Link')
        act.triggered.connect(self.linkCurrentTab)
        act = menu.addAction('Un-Link')
        act.triggered.connect(self.unlinkCurrentTab)

        menu.popup(QCursor.pos())

    def nextTab(self):
        """Move focus to next workbox tab"""
        tabWidget = self.uiWorkboxTAB
        if not tabWidget.currentWidget().hasFocus():
            tabWidget.currentWidget().setFocus()

        index = tabWidget.currentIndex()
        if index == tabWidget.count() - 1:
            tabWidget.setCurrentIndex(0)
        else:
            tabWidget.setCurrentIndex(index + 1)

    def prevTab(self):
        """Move focus to previous workbox tab"""
        tabWidget = self.uiWorkboxTAB
        if not tabWidget.currentWidget().hasFocus():
            tabWidget.currentWidget().setFocus()

        index = tabWidget.currentIndex()
        if index == 0:
            tabWidget.setCurrentIndex(tabWidget.count() - 1)
        else:
            tabWidget.setCurrentIndex(index - 1)

    def gotoTabByIndex(self, index):
        """Generally to be used in conjunction with the Ctrl+<num> keyboard shortcuts,
        which allow user to jump directly to another tab, mimicing we browser
        functionality.
        """
        if index == -1:
            index = self.uiWorkboxTAB.count() - 1
        else:
            count = self.uiWorkboxTAB.count()
            index = min(index, count)
            index -= 1

        self.uiWorkboxTAB.setCurrentIndex(index)

    def renameTab(self):
        if self._currentTab != -1:
            current = self.uiWorkboxTAB.tabBar().tabText(self._currentTab)
            msg = 'Rename the {} tab to:'.format(current)
            name, success = QInputDialog.getText(None, 'Rename Tab', msg, text=current)
            if success:
                self.uiWorkboxTAB.tabBar().setTabText(self._currentTab, name)

    def linkCurrentTab(self):
        if self._currentTab != -1:
            # get the previous path
            pref = self.load_prefs()
            prevPath = pref.get('linkFolder', os.path.join(os.path.expanduser('~')))

            # Handle the file dialog
            filters = "Python Files (*.py);;All Files (*.*)"
            path, _ = QtCompat.QFileDialog.getOpenFileName(
                self, "Link File", prevPath, filters
            )
            if not path:
                return

            pref['linkFolder'] = os.path.dirname(path)
            self.save_prefs(pref)

            self.linkTab(self._currentTab, path)

    def linkTab(self, tabIdx, path):
        wid = self.uiWorkboxTAB.widget(tabIdx)
        tab = self.uiWorkboxTAB.tabBar()

        wid.load(path)
        wid.setAutoReloadOnChange(True)
        tab.setTabText(tabIdx, os.path.basename(path))
        tab.setTabToolTip(tabIdx, path)
        iconprovider = QFileIconProvider()
        tab.setTabIcon(tabIdx, iconprovider.icon(QFileInfo(path)))

        font = self.console().font()
        wid.setWorkboxFont(font)

    def unlinkCurrentTab(self):
        if self._currentTab != -1:
            self.unlinkTab(self._currentTab)

    def unlinkTab(self, tabIdx):
        wid = self.uiWorkboxTAB.currentWidget()
        tab = self.uiWorkboxTAB.tabBar()

        wid.enableFileWatching(False)
        wid.setAutoReloadOnChange(False)
        tab.setTabToolTip(tabIdx, '')
        tab.setTabIcon(tabIdx, QIcon())

    def linkedFileChanged(self, filename):
        font = self.console().font()
        for tabIndex in range(self.uiWorkboxTAB.count()):
            workbox = self.uiWorkboxTAB.widget(tabIndex)
            if workbox.filename() == filename:
                self._reloadRequested.add(tabIndex)
                self.uiWorkboxTAB.currentWidget().setFont(font)

        newIdx = self.uiWorkboxTAB.currentIndex()
        self.updateLink(newIdx)

    def currentChanged(self):
        newIdx = self.uiWorkboxTAB.currentIndex()
        self.updateLink(newIdx)

    def updateLink(self, tabIdx):
        if tabIdx in self._reloadRequested:
            fn = self.uiWorkboxTAB.currentWidget().filename()
            if not os.path.isfile(fn):
                self.unlinkTab(tabIdx)
            else:
                # Only reload the current widget if requested
                time.sleep(0.1)  # loading the file too quickly misses any changes
                self.uiWorkboxTAB.currentWidget().reloadChange()
                font = self.console().font()
                self.uiWorkboxTAB.currentWidget().setFont(font)
            self._reloadRequested.remove(tabIdx)

    def openFileMonitor(self):
        return self._openFileMonitor

    @staticmethod
    def instance(parent=None, runWorkbox=False, create=True):
        """Returns the existing instance of the python logger creating it on first call.

        Args:
            parent (QWidget, optional): If the instance hasn't been created yet, create
                it and parent it to this object.
            runWorkbox (bool, optional): If the instance hasn't been created yet, this
                will execute the active workbox's code once fully initialized.
            create (bool, optional): Returns None if the instance has not been created.

        Returns:
            Returns a fully initialized instance of the Python Logger. If called more
            than once, the same instance will be returned. If create is False, it may
            return None.
        """
        # create the instance for the logger
        if not LoggerWindow._instance:
            if not create:
                return None

            # create the logger instance
            inst = LoggerWindow(parent, runWorkbox=runWorkbox)

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
    def instanceSetPdbMode(cls, mode, msg=''):
        """Sets the instance of LoggerWindow to pdb mode if the logger instance has
        been created.

        Args:
            mode (bool): The mode to set it to
        """
        if cls._instance:
            inst = cls._instance
            if inst.uiConsoleTXT.pdbMode() != mode:
                inst.uiConsoleTXT.setPdbMode(mode)
                from .. import external

                external.External(
                    ['pdb', '', {'msg': 'preditor.debug.getPdb().currentLine()'}]
                )
            # Pdb returns its prompt automatically. If we detect the pdb prompt and
            # _pdbContinue is set re-run the command until it's count reaches zero.
            if inst._pdbContinue and msg == '(Pdb) ':
                if inst._pdbContinue[0]:
                    count = inst._pdbContinue[0] - 1
                    if count > 0:
                        # Decrease the count.
                        inst._pdbContinue = (count, inst._pdbContinue[1])
                        # Resend the requested message
                        inst.uiConsoleTXT.pdbSendCommand(inst._pdbContinue[1])
                    else:
                        # We are done refreshing so nothing to do.
                        inst._pdbContinue = None

    @classmethod
    def instancePdbResult(cls, data):
        if cls._instance:
            if data.get('msg') == 'pdb_currentLine':
                filename = data.get('filename')
                lineNo = data.get('lineNo')
                doc = cls._instance.uiPdbTAB.currentWidget()
                if not isinstance(doc, WorkboxWidget):
                    doc = cls._instance.addWorkbox(
                        cls._instance.uiPdbTAB, closable=False
                    )
                    cls._instance._pdb_marker = doc.markerDefine(doc.Circle)
                cls._instance.uiPdbTAB.setTabText(
                    cls._instance.uiPdbTAB.currentIndex(), filename
                )
                doc.markerDeleteAll(cls._instance._pdb_marker)
                if os.path.exists(filename):
                    doc.load(filename)
                    doc.goToLine(lineNo)
                    doc.markerAdd(lineNo, cls._instance._pdb_marker)
                else:
                    doc.clear()
                    doc._filename = ''

    @classmethod
    def instanceShutdown(cls):
        """Faster way to shutdown the instance of LoggerWindow if it possibly was not used.

        Returns:
            bool: If a shutdown was required
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False
