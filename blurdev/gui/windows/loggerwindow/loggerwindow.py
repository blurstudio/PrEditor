##
#   \namespace  blurdev.gui.windows.loggerwindow.loggerwindow
#
#   \remarks    LoggerWindow class is an overloaded python interpreter for blurdev
#
#   \author     beta@blur.com
#   \author     Blur Studio
#   \date       01/15/08
#

import os
import re
import sys
import time
import warnings

import blurdev

from functools import partial

from Qt.QtCore import Qt, QFileSystemWatcher, QFileInfo, QTimer, QSize
from Qt.QtGui import QColor, QCursor, QIcon, QKeySequence
from Qt.QtWidgets import (
    QApplication,
    QFileIconProvider,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
    QTabBar,
)
from Qt import QtCompat

from blurdev import prefs

from blurdev.gui import Window
from blurdev.gui.widgets.dragspinbox import DragSpinBox

from .icons import iconFactory
from .workboxwidget import WorkboxWidget


class LoggerWindow(Window):
    _instance = None

    def __init__(self, parent, runWorkbox=False):
        Window.__init__(self, parent=parent)
        self.aboutToClearPathsEnabled = False
        self._stylesheet = 'Bright'

        import blurdev.gui

        self.setWindowIcon(QIcon(blurdev.findTool('Python_Logger').icon()))
        blurdev.gui.loadUi(__file__, self)
        blurdev.setAppUserModelID('PythonLogger')

        self.uiConsoleTXT.pdbModeAction = self.uiPdbModeACT
        self.uiConsoleTXT.pdbUpdateVisibility = self.updatePdbVisibility
        self.updatePdbVisibility(False)
        self.uiConsoleTXT.reportExecutionTime = self.reportExecutionTime
        self.uiClearToLastPromptACT.triggered.connect(
            self.uiConsoleTXT.clearToLastPrompt
        )
        # If we don't disable this shortcut Qt won't respond to this classes or the ConsoleEdit's
        self.uiConsoleTXT.uiClearToLastPromptACT.setShortcut('')

        # create the status reporting label
        self.uiStatusLBL = QLabel(self)
        self.uiMenuBar.setCornerWidget(self.uiStatusLBL)

        # create the workbox tabs
        self._currentTab = -1
        self._reloadRequested = set()
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

        # create the pdb count widget
        self._pdbContinue = None
        self.uiPdbExecuteCountLBL = QLabel('x', self.uiPdbTOOLBAR)
        self.uiPdbExecuteCountLBL.setObjectName('uiPdbExecuteCountLBL')
        self.uiPdbTOOLBAR.addWidget(self.uiPdbExecuteCountLBL)
        self.uiPdbExecuteCountDDL = DragSpinBox(self.uiPdbTOOLBAR)
        self.uiPdbExecuteCountDDL.setObjectName('uiPdbExecuteCountDDL')
        self.uiPdbExecuteCountDDL.setValue(1)
        self.uiPdbExecuteCountDDL.setDefaultValue(1)
        self.uiPdbExecuteCountDDL.setRange(1, 10000)
        msg = (
            'When the "next" and "step" buttons are pressed call them this many times.'
        )
        self.uiPdbExecuteCountDDL.setToolTip(msg)
        self.uiPdbTOOLBAR.addWidget(self.uiPdbExecuteCountDDL)

        # Store the software name so we can handle custom keyboard shortcuts based on software
        self._software = blurdev.core.objectName()

        # Initial configuration of the logToFile feature
        self._logToFilePath = None
        self._stds = None
        self.uiLogToFileClearACT.setVisible(False)

        # create the connections
        blurdev.core.debugLevelChanged.connect(self.refreshDebugLevels)

        self.uiCloseLoggerACT.triggered.connect(self.closeLogger)

        self.uiNewScriptACT.triggered.connect(blurdev.core.newScript)
        self.uiOpenScriptACT.triggered.connect(blurdev.core.openScript)
        self.uiOpenIdeACT.triggered.connect(blurdev.core.showIdeEditor)
        self.uiRunScriptACT.triggered.connect(blurdev.core.runScript)
        self.uiGotoErrorACT.triggered.connect(self.gotoError)

        self.uiNoDebugACT.triggered.connect(self.setNoDebug)
        self.uiDebugLowACT.triggered.connect(self.setLowDebug)
        self.uiDebugMidACT.triggered.connect(self.setMidDebug)
        self.uiDebugHighACT.triggered.connect(self.setHighDebug)

        self.uiRunAllACT.triggered.connect(self.execAll)
        self.uiRunSelectedACT.triggered.connect(self.execSelected)
        self.uiPdbModeACT.triggered.connect(self.uiConsoleTXT.setPdbMode)

        self.uiPdbContinueACT.triggered.connect(self.uiConsoleTXT.pdbContinue)
        self.uiPdbStepACT.triggered.connect(partial(self.pdbRepeat, 'next'))
        self.uiPdbNextACT.triggered.connect(partial(self.pdbRepeat, 'step'))
        self.uiPdbUpACT.triggered.connect(self.uiConsoleTXT.pdbUp)
        self.uiPdbDownACT.triggered.connect(self.uiConsoleTXT.pdbDown)

        self.uiAutoCompleteEnabledACT.toggled.connect(self.setAutoCompleteEnabled)
        self.uiSpellCheckEnabledACT.toggled.connect(self.setSpellCheckEnabled)
        self.uiIndentationsTabsACT.toggled.connect(self.updateIndentationsUseTabs)
        self.uiCopyTabsToSpacesACT.toggled.connect(self.updateCopyIndentsAsSpaces)
        self.uiWordWrapACT.toggled.connect(self.setWordWrap)
        self.uiResetPathsACT.triggered.connect(self.resetPaths)
        self.uiResetWarningFiltersACT.triggered.connect(warnings.resetwarnings)
        self.uiLogToFileACT.triggered.connect(self.installLogToFile)
        self.uiLogToFileClearACT.triggered.connect(self.clearLogToFile)
        self.uiClearLogACT.triggered.connect(self.clearLog)
        self.uiSaveConsoleSettingsACT.triggered.connect(self.recordPrefs)
        self.uiClearBeforeRunningACT.triggered.connect(self.setClearBeforeRunning)
        self.uiEditorVerticalACT.toggled.connect(self.adjustWorkboxOrientation)
        self.uiEnvironmentVarsACT.triggered.connect(self.showEnvironmentVars)
        self.uiAboutBlurdevACT.triggered.connect(self.showAbout)
        blurdev.core.aboutToClearPaths.connect(self.pathsAboutToBeCleared)
        self.uiSetFlashWindowIntervalACT.triggered.connect(self.setFlashWindowInterval)

        if blurdev.settings.OS_TYPE == 'Windows':
            self.uiBlurIdeShortcutACT.triggered.connect(self.createShortcutBlurIDE)
            self.uiPythonLoggerShortcutACT.triggered.connect(
                self.createShortcutPythonLogger
            )
            self.uiTreegruntShortcutACT.triggered.connect(self.createShortcutTreegrunt)
        else:
            # We can't currently create desktop shortcuts on posix systems.
            self.uiShortcutsMENU.menuAction().setVisible(False)

        self.uiNewScriptACT.setIcon(iconFactory.getIcon('insert_drive_file'))
        self.uiOpenScriptACT.setIcon(iconFactory.getIcon('open'))
        self.uiOpenIdeACT.setIcon(iconFactory.getIcon('edit'))
        self.uiRunScriptACT.setIcon(iconFactory.getIcon('run'))
        self.uiNoDebugACT.setIcon(
            self._getDebugIcon(iconFactory.getIconPath('level'), QColor('#70C159'))
        )
        self.uiDebugLowACT.setIcon(
            self._getDebugIcon(iconFactory.getIconPath('level'), QColor('#EEC041'))
        )
        self.uiDebugMidACT.setIcon(
            self._getDebugIcon(iconFactory.getIconPath('level'), QColor('#EF8341'))
        )
        self.uiDebugHighACT.setIcon(
            self._getDebugIcon(iconFactory.getIconPath('level'), QColor('#E74C46'))
        )
        self.uiResetPathsACT.setIcon(iconFactory.getIcon('reset'))
        self.uiClearLogACT.setIcon(iconFactory.getIcon('clear'))
        self.uiSaveConsoleSettingsACT.setIcon(iconFactory.getIcon('save'))
        self.uiAboutBlurdevACT.setIcon(iconFactory.getIcon('about'))
        self.uiCloseLoggerACT.setIcon(iconFactory.getIcon('close'))

        self.uiPdbContinueACT.setIcon(iconFactory.getIcon('continue'))
        self.uiPdbStepACT.setIcon(iconFactory.getIcon('step'))
        self.uiPdbNextACT.setIcon(iconFactory.getIcon('next'))
        self.uiPdbUpACT.setIcon(iconFactory.getIcon('up'))
        self.uiPdbDownACT.setIcon(iconFactory.getIcon('down'))

        # Setting toolbar icon size.
        from Qt.QtCore import QSize

        self.uiConsoleTOOLBAR.setIconSize(QSize(18, 18))

        # Start the filesystem monitor
        self._openFileMonitor = QFileSystemWatcher(self)
        self._openFileMonitor.fileChanged.connect(self.linkedFileChanged)

        # Make action shortcuts available anywhere in the Logger
        self.addAction(self.uiClearLogACT)

        # refresh the ui
        self.refreshDebugLevels()

        # calling setLanguage resets this value to False
        self.restorePrefs()

        # add stylesheet menu options.
        for style_name in blurdev.core.styleSheets('logger'):
            action = self.uiStyleMENU.addAction(style_name)
            action.setObjectName('ui{}ACT'.format(style_name))
            action.setCheckable(True)
            action.setChecked(self._stylesheet == style_name)
            action.triggered.connect(partial(self.setStyleSheet, style_name))

        self.overrideKeyboardShortcuts()
        self.uiConsoleTOOLBAR.show()
        loggerName = QApplication.instance().translate(
            'PythonLoggerWindow', 'Python Logger'
        )
        self.setWindowTitle(
            '%s - %s - %s %i-bit'
            % (
                loggerName,
                blurdev.core.objectName().capitalize(),
                '%i.%i.%i' % sys.version_info[:3],
                blurdev.osystem.getPointerSize(),
            )
        )

        # Run the current workbox after the LoggerWindow is shown.
        if runWorkbox:
            # By using two singleShot timers, we can show and draw the LoggerWindow,
            # then call execAll. This makes it easier to see what code you are running
            # before it has finished running completely.
            QTimer.singleShot(0, lambda: QTimer.singleShot(0, self.execAll))

    def _getDebugIcon(self, filepath, color):
        icf = iconFactory.customize(
            iconClass='StyledIcon',
            baseColor=color,
            activeColor=color,
            activeContrast=1,
            highlightColor=color,
            highlightContrast=1,
        )
        return icf.getIcon(path=filepath)

    @classmethod
    def _genPrefName(cls, baseName, index):
        if index:
            baseName = '{name}{index}'.format(name=baseName, index=index)
        return baseName

    def addWorkbox(self, tabWidget=None, title='Workbox', closable=True):
        if tabWidget is None:
            tabWidget = self.uiWorkboxTAB
        workbox = WorkboxWidget(tabWidget)
        workbox.setConsole(self.uiConsoleTXT)
        workbox.setMinimumHeight(1)
        index = tabWidget.addTab(workbox, title)
        workbox.setLanguage('Python')
        workbox.setShowSmartHighlighting(True)
        # update the lexer
        workbox.setMarginsFont(workbox.font())
        if closable:
            # If only one tab is visible, don't show the close tab button
            tabWidget.setTabsClosable(tabWidget.count() != 1)
        tabWidget.setCurrentIndex(index)
        workbox.setIndentationsUseTabs(self.uiIndentationsTabsACT.isChecked())
        workbox.copyIndentsAsSpaces = self.uiCopyTabsToSpacesACT.isChecked()

        # tabButton = self.uiWorkboxTAB.tabBar().tabButton(index, QTabBar.RightSide)
        # if tabButton:
        #     tabButton.setIcon(QIcon(r'K:\library\icons\fugue\16\acorn.png'))
        #     self.uiWorkboxTAB.tabBar().setTabButton(index, QTabBar.RightSide, tabButton)
        #     print tabButton
        # tabWidget.tabBar().tabButton(index, QTabBar.RightSide).setIcon(r'K:\library\icons\fugue\16\acorn.png')
        # Setting close icon.
        # closeButton = self.uiWorkboxTAB.tabBar().tabButton(index, QTabBar.RightSide)
        # if closeButton:
        #     closeButton.setIcon(iconFactory.getIcon(size=18, name='close'))
        #     closeButton.setIcon(QIcon(r'K:\library\icons\fugue\16\acorn.png'))
        #     closeButton.setIconSize(QSize(16, 16))
        #     closeButton.setStyleSheet('''
        #         QToolButton {
        #             border: none;
        #             margin: 0px;
        #             padding: 0px;
        #         }
        #     ''')
        #     self.uiWorkboxTAB.tabBar().setTabButton(index, QTabBar.RightSide, closeButton)

        return workbox

    def adjustWorkboxOrientation(self, state):
        if state:
            self.uiSplitterSPLIT.setOrientation(Qt.Horizontal)
        else:
            self.uiSplitterSPLIT.setOrientation(Qt.Vertical)

    def console(self):
        return self.uiConsoleTXT

    def clearLog(self):
        self.uiConsoleTXT.clear()

    def clearLogToFile(self):
        """ If installLogToFile has been called, clear the stdout.
        """
        if self._stds:
            self._stds[0].clear(stamp=True)

    def closeEvent(self, event):
        self.recordPrefs()
        Window.closeEvent(self, event)
        if self.uiConsoleTOOLBAR.isFloating():
            self.uiConsoleTOOLBAR.hide()

    def closeLogger(self):
        self.close()

    def createShortcut(self, function):
        msg = (
            'Do you want to create a public shortcut? If not it will be '
            'created on your user desktop.'
        )
        result = QMessageBox.question(
            self,
            'Create On Public?',
            msg,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if result != QMessageBox.Cancel:
            public = result == QMessageBox.Yes
            function(common=int(public))

    def createShortcutBlurIDE(self):
        from blurdev.utils import shortcut

        self.createShortcut(shortcut.createShortcutBlurIDE)

    def createShortcutPythonLogger(self):
        from blurdev.utils import shortcut

        self.createShortcut(shortcut.createShortcutPythonLogger)

    def createShortcutTreegrunt(self):
        from blurdev.utils import shortcut

        self.createShortcut(shortcut.createShortcutTreegrunt)

    def execAll(self):
        """
            \remarks    Clears the console before executing all workbox code
        """
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execAll()

    def execSelected(self):
        """
            \remarks    Clears the console before executing selected workbox code
        """
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execSelected()

    def gotoError(self):
        text = self.uiConsoleTXT.textCursor().selectedText()
        results = re.match(r'[ \t]*File "([^"]+)", line (\d+)', text)
        if results:
            from blurdev.ide import IdeEditor

            IdeEditor.instance().show()
            filename, lineno = results.groups()
            IdeEditor.instance().load(filename, int(lineno))

    def keyPressEvent(self, event):
        # Fix 'Maya : Qt tools lose focus' https://redmine.blur.com/issues/34430
        if event.modifiers() & (Qt.AltModifier | Qt.ControlModifier | Qt.ShiftModifier):
            pass
        else:
            super(LoggerWindow, self).keyPressEvent(event)

    def overrideKeyboardShortcuts(self):
        """
            \remarks    If a specific software has limitations preventing keyboard shortcuts from working, they can be overidden here
                        Example: Softimage treats both enter keys as Qt.Key_Enter, It ignores Qt.Key_Return
        """
        if self._software == 'softimage':
            self.uiRunSelectedACT.setShortcut(
                QKeySequence(Qt.Key_Enter + Qt.ShiftModifier)
            )
            self.uiRunAllACT.setShortcut(
                QKeySequence(Qt.Key_Enter + Qt.ControlModifier)
            )

    def pdbRepeat(self, commandText):
        # If we need to repeat the command store that info
        value = self.uiPdbExecuteCountDDL.value()
        if value > 1:
            # The first request is triggered at the end of this function, so we need to store
            # one less than requested
            self._pdbContinue = (value - 1, commandText)
        else:
            self._pdbContinue = None
        # Send the first command
        self.uiConsoleTXT.pdbSendCommand(commandText)

    def pathsAboutToBeCleared(self):
        if self.uiClearLogOnRefreshACT.isChecked():
            self.clearLog()

    def refreshDebugLevels(self):
        from blurdev.debug import DebugLevel, debugLevel

        dlevel = debugLevel()
        for act, level in [
            (self.uiNoDebugACT, 0),
            (self.uiDebugLowACT, DebugLevel.Low),
            (self.uiDebugMidACT, DebugLevel.Mid),
            (self.uiDebugHighACT, DebugLevel.High),
        ]:
            act.blockSignals(True)
            act.setChecked(level == dlevel)
            act.blockSignals(False)

    def reportExecutionTime(self, seconds):
        """ Update status text with seconds passed in. """
        self.setStatusText('Exec: {:0.04f} Seconds'.format(seconds))

    def resetPaths(self):
        blurdev.activeEnvironment().resetPaths()

    def recordPrefs(self):
        pref = prefs.find(r'blurdev\LoggerWindow')
        pref.recordProperty('loggergeom', self.geometry())
        pref.recordProperty('windowState', self.windowState().__int__())
        pref.recordProperty('SplitterVertical', self.uiEditorVerticalACT.isChecked())
        pref.recordProperty('SplitterSize', self.uiSplitterSPLIT.sizes())
        pref.recordProperty('tabIndent', self.uiIndentationsTabsACT.isChecked())
        pref.recordProperty(
            'copyIndentsAsSpaces', self.uiCopyTabsToSpacesACT.isChecked()
        )
        pref.recordProperty('hintingEnabled', self.uiAutoCompleteEnabledACT.isChecked())
        pref.recordProperty(
            'spellCheckEnabled', self.uiSpellCheckEnabledACT.isChecked()
        )
        pref.recordProperty('wordWrap', self.uiWordWrapACT.isChecked())
        pref.recordProperty(
            'clearBeforeRunning', self.uiClearBeforeRunningACT.isChecked()
        )
        pref.recordProperty(
            'clearBeforeEnvRefresh', self.uiClearLogOnRefreshACT.isChecked()
        )
        pref.recordProperty('toolbarStates', self.saveState())
        pref.recordProperty('consoleFont', self.uiConsoleTXT.font())

        for index in range(self.uiWorkboxTAB.count()):
            workbox = self.uiWorkboxTAB.widget(index)
            pref.recordProperty(self._genPrefName('WorkboxText', index), workbox.text())
            lexer = workbox.lexer()
            if lexer:
                font = lexer.font(0)
            else:
                font = workbox.font()
            pref.recordProperty(self._genPrefName('workboxFont', index), font)
            pref.recordProperty(
                self._genPrefName('workboxMarginFont', index), workbox.marginsFont()
            )
            pref.recordProperty(
                self._genPrefName('workboxTabTitle', index),
                self.uiWorkboxTAB.tabBar().tabText(index),
            )

            linkPath = ''
            if workbox._fileMonitoringActive:
                linkPath = workbox.filename()
                if os.path.isfile(linkPath):
                    workbox.save()
                else:
                    self.unlinkTab(index)

            pref.recordProperty(self._genPrefName('workboxPath', index), linkPath)

        pref.recordProperty('WorkboxCount', self.uiWorkboxTAB.count())
        pref.recordProperty('WorkboxCurrentIndex', self.uiWorkboxTAB.currentIndex())
        pref.recordProperty('currentStyleSheet', self._stylesheet)
        if self._stylesheet == 'Custom':
            pref.recordProperty('styleSheet', self.styleSheet())
        pref.recordProperty('flashTime', self.uiConsoleTXT.flashTime)

        pref.save()

    def restorePrefs(self):
        from blurdev.XML.minidom import unescape

        pref = prefs.find(r'blurdev\LoggerWindow')
        rect = pref.restoreProperty('loggergeom')
        if rect and not rect.isNull():
            self.setGeometry(rect)
        self.uiEditorVerticalACT.setChecked(
            pref.restoreProperty('SplitterVertical', False)
        )
        self.adjustWorkboxOrientation(self.uiEditorVerticalACT.isChecked())
        sizes = pref.restoreProperty('SplitterSize', None)
        if sizes:
            self.uiSplitterSPLIT.setSizes(sizes)
        self.setWindowState(Qt.WindowStates(pref.restoreProperty('windowState', 0)))
        self.uiIndentationsTabsACT.setChecked(pref.restoreProperty('tabIndent', True))
        self.uiCopyTabsToSpacesACT.setChecked(
            pref.restoreProperty('copyIndentsAsSpaces', False)
        )
        self.uiAutoCompleteEnabledACT.setChecked(
            pref.restoreProperty('hintingEnabled', True)
        )
        self.setSpellCheckEnabled(self.uiSpellCheckEnabledACT.isChecked())
        self.uiSpellCheckEnabledACT.setChecked(
            pref.restoreProperty('spellCheckEnabled', False)
        )
        self.uiConsoleTXT.completer().setEnabled(
            self.uiAutoCompleteEnabledACT.isChecked()
        )
        self.uiWordWrapACT.setChecked(pref.restoreProperty('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(
            pref.restoreProperty('clearBeforeRunning', False)
        )
        self.uiClearLogOnRefreshACT.setChecked(
            pref.restoreProperty('clearBeforeEnvRefresh', False)
        )
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())
        font = pref.restoreProperty('consoleFont', None)
        if font:
            self.uiConsoleTXT.setFont(font)
        # Restore the workboxes
        count = pref.restoreProperty('WorkboxCount', 1)
        for index in range(count - self.uiWorkboxTAB.count()):
            # create each of the workbox tabs
            self.addWorkbox(self.uiWorkboxTAB)
        for index in range(count):
            workbox = self.uiWorkboxTAB.widget(index)
            workbox.setText(
                unescape(
                    pref.restoreProperty(self._genPrefName('WorkboxText', index), '')
                )
            )

            workboxPath = pref.restoreProperty(
                self._genPrefName('workboxPath', index), ''
            )
            if os.path.isfile(workboxPath):
                self.linkTab(index, workboxPath)

            font = pref.restoreProperty(self._genPrefName('workboxFont', index), None)
            if font:
                lexer = workbox.lexer()
                if lexer:
                    font = lexer.setFont(font)
                else:
                    font = workbox.setFont(font)
            font = pref.restoreProperty(
                self._genPrefName('workboxMarginFont', index), None
            )
            if font:
                workbox.setMarginsFont(font)
            tabText = pref.restoreProperty(
                self._genPrefName('workboxTabTitle', index), 'Workbox'
            )
            self.uiWorkboxTAB.tabBar().setTabText(index, tabText)

        self.uiWorkboxTAB.setCurrentIndex(
            pref.restoreProperty('WorkboxCurrentIndex', 0)
        )

        self._stylesheet = pref.restoreProperty('currentStyleSheet', 'Bright')
        if self._stylesheet == 'Custom':
            self.setStyleSheet(unescape(pref.restoreProperty('styleSheet', '')))
        else:
            self.setStyleSheet(self._stylesheet)
        self.uiConsoleTXT.flashTime = pref.restoreProperty('flashTime', 1.0)

        self.restoreToolbars()

    def restoreToolbars(self):
        pref = prefs.find(r'blurdev\LoggerWindow')
        state = pref.restoreProperty('toolbarStates', None)
        if state:
            self.restoreState(state)
            # Ensure uiPdbTOOLBAR respects the current pdb mode
            self.uiConsoleTXT.setPdbMode(self.uiConsoleTXT.pdbMode())

    def removeWorkbox(self, index):
        if self.uiWorkboxTAB.count() == 1:
            msg = "You have to leave at least one tab open."
            QMessageBox.critical(self, 'Tab can not be closed.', msg, QMessageBox.Ok)
            return
        msg = "Would you like to donate this tabs contents to the /dev/null fund for wayward code?"
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
        aspell = None
        try:
            import aspell
        except Exception as e:
            if self.isVisible():
                # Only show warning if Logger is visible and also disable
                self.uiSpellCheckEnabledACT.setDisabled(True)
                QMessageBox.warning(self, "Spell-Check", "{}".format(e))

        if aspell:
            try:
                speller = aspell.Speller()
                for index in range(self.uiWorkboxTAB.count()):
                    self.uiWorkboxTAB.widget(index).setSpellCheckEnabled(state)
            except Exception as e:
                if self.isVisible():
                    # Only show warning if Logger is visible and also disable
                    self.uiSpellCheckEnabledACT.setCheckable(False)
                    QMessageBox.warning(self, "Spell-Check", "{}".format(e))

    def setStatusText(self, txt):
        """ Set the text shown in the menu corner of the menu bar.

        Args:
            txt (str): The text to show in the status text label.
        """
        self.uiStatusLBL.setText(txt)
        self.uiMenuBar.adjustSize()

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """ Accepts the name of a stylesheet included with blurdev, or a full
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
            sheet, valid = blurdev.core.readStyleSheet('logger/{}'.format(stylesheet))
            if valid:
                self._stylesheet = stylesheet
            else:
                # Assume the user passed the text of the stylesheet directly
                sheet = stylesheet
                self._stylesheet = 'Custom'

        # Load the stylesheet
        if sheet is not None:
            super(LoggerWindow, self).setStyleSheet(sheet)
            wgt = self.uiWorkboxTAB.currentWidget()
            wgt.updateColorScheme()

        # Update the style menu
        for act in self.uiStyleMENU.actions():
            name = act.objectName()
            isCurrent = name == 'ui{}ACT'.format(self._stylesheet)
            act.setChecked(isCurrent)

    def setClearBeforeRunning(self, state):
        if state:
            self.uiRunSelectedACT.setIcon(iconFactory.getIcon('playlist_play'))
            self.uiRunAllACT.setIcon(iconFactory.getIcon('fast_forward'))
        else:
            self.uiRunSelectedACT.setIcon(iconFactory.getIcon('playlist_play'))
            self.uiRunAllACT.setIcon(iconFactory.getIcon('fast_forward'))

    def setNoDebug(self):
        from blurdev import debug

        debug.setDebugLevel(None)

    def setLowDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Low)

    def setMidDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Mid)

    def setFlashWindowInterval(self):
        value = self.uiConsoleTXT.flashTime
        msg = (
            'If running code in the logger takes X seconds or longer,\n'
            'the window will flash if it is not in focus.\n'
            'Setting the value to zero will disable flashing.'
        )
        value, success = QInputDialog.getDouble(None, 'Set flash window', msg, value)
        if success:
            self.uiConsoleTXT.flashTime = value

    def setHighDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.High)

    def setWordWrap(self, state):
        if state:
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.WidgetWidth)
        else:
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.NoWrap)

    def showAbout(self):
        msg = blurdev.core.aboutBlurdev()
        QMessageBox.information(self, 'About blurdev', msg)

    def showEnvironmentVars(self):
        from blurdev.gui import Dialog

        dlg = Dialog(blurdev.core.logger())
        lyt = QVBoxLayout(dlg)
        lbl = QTextBrowser(dlg)
        lyt.addWidget(lbl)
        dlg.setWindowTitle('Blurdev Environment Variable Help')
        with open(blurdev.resourcePath('environment_variables.html')) as f:
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
            pref = prefs.find(r'blurdev\LoggerWindow')
            prevPath = pref.restoreProperty(
                'linkFolder', os.path.join(os.path.expanduser('~'))
            )

            # Handle the file dialog
            filters = "Python Files (*.py);;All Files (*.*)"
            path, _ = QtCompat.QFileDialog.getOpenFileName(
                self, "Link File", prevPath, filters
            )
            if not path:
                return
            pref.recordProperty('linkFolder', os.path.dirname(path))
            pref.save()

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
        for tabIndex in range(self.uiWorkboxTAB.count()):
            workbox = self.uiWorkboxTAB.widget(tabIndex)
            if workbox.filename() == filename:
                self._reloadRequested.add(tabIndex)
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
            self._reloadRequested.remove(tabIdx)

    def openFileMonitor(self):
        return self._openFileMonitor

    @staticmethod
    def instance(parent=None, runWorkbox=False):
        # create the instance for the logger
        if not LoggerWindow._instance:

            # create the logger instance
            inst = LoggerWindow(parent, runWorkbox=runWorkbox)

            # RV has a Unique window structure. It makes more sense to not parent a singleton
            # window than to parent it to a specific top level window.
            if blurdev.core.objectName() == 'rv':
                inst.setParent(None)
                inst.setAttribute(Qt.WA_QuitOnClose, False)

            # protect the memory
            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            # cache the instance
            LoggerWindow._instance = inst

        return LoggerWindow._instance

    def installLogToFile(self):
        """ All stdout/stderr output is also appended to this file.

        This uses blurdev.debug.logToFile(path, useOldStd=True).
        """
        if self._logToFilePath is None:
            basepath = blurdev.osystem.expandvars(os.environ['BDEV_PATH_BLUR'])
            path = os.path.join(basepath, 'blurdevProtocol.log')
            path, _ = QtCompat.QFileDialog.getOpenFileName(
                self, "Log Output to File", path
            )
            if not path:
                return
            path = os.path.normpath(path)
            print('Output logged to: "{}"'.format(path))
            blurdev.debug.logToFile(path, useOldStd=True)
            # Store the std's so we can clear them later
            self._stds = (sys.stdout, sys.stderr)
            self.uiLogToFileACT.setText('Output Logged to File')
            self.uiLogToFileClearACT.setVisible(True)
            self._logToFilePath = path
        else:
            print('Output logged to: "{}"'.format(self._logToFilePath))

    @classmethod
    def instanceSetPdbMode(cls, mode, msg=''):
        """ Sets the instance of LoggerWindow to pdb mode if the logger instance has been created.

        Args:
            mode (bool): The mode to set it to
        """
        if cls._instance:
            inst = cls._instance
            if inst.uiConsoleTXT.pdbMode() != mode:
                inst.uiConsoleTXT.setPdbMode(mode)
                import blurdev.external

                blurdev.external.External(
                    ['pdb', '', {'msg': 'blurdev.debug.getPdb().currentLine()'}]
                )
            # Pdb returns its prompt automatically. If we detect the pdb prompt and _pdbContinue
            # is set re-run the command until it's count reaches zero.
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
        """ Faster way to shutdown the instance of LoggerWindow if it possibly was not used.

        Returns:
            bool: If a shutdown was required
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False
