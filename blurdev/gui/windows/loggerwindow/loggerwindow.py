##
# 	\namespace	blurdev.gui.windows.loggerwindow.loggerwindow
#
# 	\remarks	LoggerWindow class is an overloaded python interpreter for blurdev
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/15/08
#

import os, time
from functools import partial
from blurdev.gui import Window
from blurdev.gui.widgets.dragspinbox import DragSpinBox
from workboxwidget import WorkboxWidget
from blurdev import prefs
from PyQt4.QtCore import Qt, QFileSystemWatcher, QFileInfo
from PyQt4.QtGui import (
    QSplitter,
    QKeySequence,
    QIcon,
    QColor,
    QWidget,
    QMessageBox,
    QMenu,
    QCursor,
    QInputDialog,
    QApplication,
    QLabel,
    QFileDialog,
    QFileIconProvider,
)
import blurdev


class LoggerWindow(Window):
    _instance = None

    def __init__(self, parent):
        Window.__init__(self, parent)
        self.aboutToClearPathsEnabled = False

        import blurdev.gui

        self.setWindowIcon(QIcon(blurdev.resourcePath('img/ide.png')))
        blurdev.gui.loadUi(__file__, self)

        self.uiConsoleTXT.pdbModeAction = self.uiPdbModeACT
        self.uiConsoleTXT.pdbUpdateVisibility = self.updatePdbVisibility
        self.updatePdbVisibility(False)
        self.uiClearToLastPromptACT.triggered.connect(
            self.uiConsoleTXT.clearToLastPrompt
        )
        # If we don't disable this shortcut Qt won't respond to this classes or the ConsoleEdit's
        self.uiConsoleTXT.uiClearToLastPromptACT.setShortcut('')

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

        # Store the software name so we can handle custom keyboard shortcuts bassed on software
        self._software = blurdev.core.objectName()

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
        self.uiIndentationsTabsACT.toggled.connect(self.updateIndentationsUseTabs)
        self.uiCopyTabsToSpacesACT.toggled.connect(self.updateCopyIndentsAsSpaces)
        self.uiWordWrapACT.toggled.connect(self.setWordWrap)
        self.uiResetPathsACT.triggered.connect(self.resetPaths)
        self.uiSdkBrowserACT.triggered.connect(self.showSdk)
        self.uiClearLogACT.triggered.connect(self.clearLog)
        self.uiSaveConsoleSettingsACT.triggered.connect(self.recordPrefs)
        self.uiClearBeforeRunningACT.triggered.connect(self.setClearBeforeRunning)
        self.uiEditorVerticalACT.toggled.connect(self.adjustWorkboxOrientation)
        blurdev.core.aboutToClearPaths.connect(self.pathsAboutToBeCleared)

        self.uiNewScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/newfile.png')))
        self.uiOpenScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/open.png')))
        self.uiOpenIdeACT.setIcon(QIcon(blurdev.resourcePath('img/ide.png')))
        self.uiRunScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/run.png')))
        self.uiNoDebugACT.setIcon(QIcon(blurdev.resourcePath('img/debug_off.png')))
        self.uiDebugLowACT.setIcon(QIcon(blurdev.resourcePath('img/debug_low.png')))
        self.uiDebugMidACT.setIcon(QIcon(blurdev.resourcePath('img/debug_mid.png')))
        self.uiDebugHighACT.setIcon(QIcon(blurdev.resourcePath('img/debug_high.png')))
        self.uiResetPathsACT.setIcon(QIcon(blurdev.resourcePath('img/reset.png')))
        self.uiClearLogACT.setIcon(QIcon(blurdev.resourcePath('img/ide/clearlog.png')))
        self.uiSaveConsoleSettingsACT.setIcon(
            QIcon(blurdev.resourcePath('img/savesettings.png'))
        )
        self.uiCloseLoggerACT.setIcon(QIcon(blurdev.resourcePath('img/ide/close.png')))

        self.uiPdbContinueACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/pdb_continue.png'))
        )
        self.uiPdbStepACT.setIcon(QIcon(blurdev.resourcePath('img/ide/pdb_step.png')))
        self.uiPdbNextACT.setIcon(QIcon(blurdev.resourcePath('img/ide/pdb_next.png')))
        self.uiPdbUpACT.setIcon(QIcon(blurdev.resourcePath('img/ide/pdb_up.png')))
        self.uiPdbDownACT.setIcon(QIcon(blurdev.resourcePath('img/ide/pdb_down.png')))

        # Start the filesystem monitor
        self._openFileMonitor = QFileSystemWatcher(self)
        self._openFileMonitor.fileChanged.connect(self.linkedFileChanged)

        # Make action shortcuts available anywhere in the Logger
        self.addAction(self.uiClearLogACT)

        # refresh the ui
        self.refreshDebugLevels()

        # calling setLanguage resets this value to False
        self.restorePrefs()
        self.overrideKeyboardShortcuts()
        self.uiConsoleTOOLBAR.show()
        import sys, platform

        loggerName = QApplication.instance().translate(
            'PythonLoggerWindow', 'Python Logger'
        )
        self.setWindowTitle(
            '%s - %s - %s %ibit'
            % (
                loggerName,
                blurdev.core.objectName(),
                '%i.%i.%i' % sys.version_info[:3],
                blurdev.osystem.getPointerSize(),
            )
        )

    @classmethod
    def _genPrefName(cls, baseName, index):
        if index:
            baseName = '{name}{index}'.format(name=baseName, index=index)
        return baseName

    def addWorkbox(self, tabWidget=None, title='Workbox', closable=True):
        if tabWidget == None:
            tabWidget = self.uiWorkboxTAB
        workbox = WorkboxWidget(tabWidget)
        workbox.setConsole(self.uiConsoleTXT)
        workbox.setMinimumHeight(1)
        index = tabWidget.addTab(workbox, title)
        workbox.setLanguage('Python')
        workbox.setShowSmartHighlighting(True)
        # update the lexer
        lex = workbox.lexer()
        workbox.setMarginsFont(workbox.font())
        if closable:
            # If only one tab is visible, don't show the close tab button
            tabWidget.setTabsClosable(tabWidget.count() != 1)
        tabWidget.setCurrentIndex(index)
        workbox.setIndentationsUseTabs(self.uiIndentationsTabsACT.isChecked())
        workbox.copyIndentsAsSpaces = self.uiCopyTabsToSpacesACT.isChecked()
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

    def closeEvent(self, event):
        self.recordPrefs()
        Window.closeEvent(self, event)
        if self.uiConsoleTOOLBAR.isFloating():
            self.uiConsoleTOOLBAR.hide()

    def closeLogger(self):
        self.close()

    def execAll(self):
        """
            \remarks	Clears the console before executing all workbox code
        """
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execAll()

    def execSelected(self):
        """
            \remarks	Clears the console before executing selected workbox code
        """
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxTAB.currentWidget().execSelected()

    def gotoError(self):
        text = self.uiConsoleTXT.textCursor().selectedText()
        import re

        results = re.match('[ \t]*File "([^"]+)", line (\d+)', unicode(text))
        if results:
            from blurdev.ide import IdeEditor

            IdeEditor.instance().show()
            filename, lineno = results.groups()
            IdeEditor.instance().load(filename, int(lineno))

    def overrideKeyboardShortcuts(self):
        """
            \remarks	If a specific software has limitations preventing keyboard shortcuts from working, they can be overidden here
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

    def resetPaths(self):
        blurdev.activeEnvironment().resetPaths()

    def recordPrefs(self):
        pref = prefs.find('blurdev\LoggerWindow')
        pref.recordProperty('loggergeom', self.geometry())
        pref.recordProperty('windowState', self.windowState().__int__())
        pref.recordProperty('SplitterVertical', self.uiEditorVerticalACT.isChecked())
        pref.recordProperty('SplitterSize', self.uiSplitterSPLIT.sizes())
        pref.recordProperty('tabIndent', self.uiIndentationsTabsACT.isChecked())
        pref.recordProperty(
            'copyIndentsAsSpaces', self.uiCopyTabsToSpacesACT.isChecked()
        )
        pref.recordProperty('hintingEnabled', self.uiAutoCompleteEnabledACT.isChecked())
        pref.recordProperty('wordWrap', self.uiWordWrapACT.isChecked())
        pref.recordProperty(
            'clearBeforeRunning', self.uiClearBeforeRunningACT.isChecked()
        )
        pref.recordProperty(
            'clearBeforeEnvRefresh', self.uiClearLogOnRefreshACT.isChecked()
        )
        pref.recordProperty(
            'disableSdkShortcut', self.uiDisableSDKShortcutACT.isChecked()
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
        pref.recordProperty('styleSheet', self.styleSheet())

        pref.save()

    def restorePrefs(self):
        from blurdev.XML.minidom import unescape

        pref = prefs.find('blurdev\LoggerWindow')
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
        self.uiDisableSDKShortcutACT.setChecked(
            pref.restoreProperty('disableSdkShortcut', False)
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

        self.setStyleSheet(unescape(pref.restoreProperty('styleSheet', '')))

        self.restoreToolbars()

    def restoreToolbars(self):
        pref = prefs.find('blurdev\LoggerWindow')
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

    def setClearBeforeRunning(self, state):
        if state:
            self.uiRunSelectedACT.setIcon(
                QIcon(blurdev.resourcePath('img/ide/runselectedclear.png'))
            )
            self.uiRunAllACT.setIcon(
                QIcon(blurdev.resourcePath('img/ide/runallclear.png'))
            )
        else:
            self.uiRunSelectedACT.setIcon(
                QIcon(blurdev.resourcePath('img/ide/runselected.png'))
            )
            self.uiRunAllACT.setIcon(QIcon(blurdev.resourcePath('img/ide/runall.png')))

    def setNoDebug(self):
        from blurdev import debug

        debug.setDebugLevel(None)

    def setLowDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Low)

    def setMidDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Mid)

    def setHighDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.High)

    def setWordWrap(self, state):
        if state:
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.WidgetWidth)
        else:
            self.uiConsoleTXT.setLineWrapMode(self.uiConsoleTXT.NoWrap)

    def showEvent(self, event):
        super(LoggerWindow, self).showEvent(event)
        self.restoreToolbars()
        self.updateIndentationsUseTabs()
        self.updateCopyIndentsAsSpaces()

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
        # If the user has set a stylesheet on the logger we need to refresh it
        self.setStyleSheet(self.styleSheet())

    def showSdk(self):
        if not self.uiDisableSDKShortcutACT.isChecked():
            blurdev.core.sdkBrowser().show()

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
            pref = prefs.find('blurdev\LoggerWindow')
            prevPath = pref.restoreProperty(
                'linkFolder', os.path.join(os.path.expanduser('~'))
            )

            # Handle the file dialog
            filters = "Python Files (*.py);;All Files (*.*)"
            path = QFileDialog.getOpenFileName(self, "Link File", prevPath, filters)
            if not path:
                return
            path = unicode(path)
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
    def instance(parent=None):
        # create the instance for the logger
        if not LoggerWindow._instance:

            # create the logger instance
            inst = LoggerWindow(parent)

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
