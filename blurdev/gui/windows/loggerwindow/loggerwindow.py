##
# 	\namespace	blurdev.gui.windows.loggerwindow.loggerwindow
#
# 	\remarks	LoggerWindow class is an overloaded python interpreter for blurdev
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/15/08
#

from blurdev.gui import Window
from blurdev import prefs
from PyQt4.QtGui import QSplitter, QKeySequence, QIcon
from PyQt4.QtCore import Qt
import blurdev


class LoggerWindow(Window):
    _instance = None

    def __init__(self, parent):
        Window.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # create the splitter layout
        self.uiSplitterSPLIT = QSplitter(self)

        # create the console widget
        from console import ConsoleEdit

        self.uiConsoleTXT = ConsoleEdit(self.uiSplitterSPLIT)
        self.uiConsoleTXT.setMinimumHeight(1)

        # create the workbox
        from workboxwidget import WorkboxWidget

        self.uiWorkboxWGT = WorkboxWidget(self.uiSplitterSPLIT)
        self.uiWorkboxWGT.setConsole(self.uiConsoleTXT)
        self.uiWorkboxWGT.setMinimumHeight(1)

        # Store the software name so we can handle custom keyboard shortcuts bassed on software
        self._software = blurdev.core.objectName()

        # create the layout
        from PyQt4.QtGui import QVBoxLayout

        layout = QVBoxLayout()
        layout.addWidget(self.uiSplitterSPLIT)
        self.centralWidget().setLayout(layout)

        # create the connections
        blurdev.core.debugLevelChanged.connect(self.refreshDebugLevels)

        self.uiCloseLoggerACT.triggered.connect(self.closeLogger)

        self.uiNewScriptACT.triggered.connect(blurdev.core.newScript)
        self.uiOpenScriptACT.triggered.connect(blurdev.core.openScript)
        self.uiRunScriptACT.triggered.connect(blurdev.core.runScript)
        self.uiGotoErrorACT.triggered.connect(self.gotoError)

        self.uiNoDebugACT.triggered.connect(self.setNoDebug)
        self.uiDebugLowACT.triggered.connect(self.setLowDebug)
        self.uiDebugMidACT.triggered.connect(self.setMidDebug)
        self.uiDebugHighACT.triggered.connect(self.setHighDebug)

        self.uiRunAllACT.triggered.connect(self.execAll)
        self.uiRunSelectedACT.triggered.connect(self.execSelected)

        self.uiIndentationsTabsACT.toggled.connect(
            self.uiWorkboxWGT.setIndentationsUseTabs
        )
        self.uiWordWrapACT.toggled.connect(self.setWordWrap)
        self.uiResetPathsACT.triggered.connect(self.resetPaths)
        self.uiSdkBrowserACT.triggered.connect(self.showSdk)
        self.uiClearLogACT.triggered.connect(self.clearLog)
        self.uiSaveConsoleSettingsACT.triggered.connect(self.recordPrefs)
        self.uiClearBeforeRunningACT.triggered.connect(self.setClearBeforeRunning)
        self.uiEditorVerticalACT.toggled.connect(self.adjustWorkboxOrientation)

        self.uiNewScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/newfile.png')))
        self.uiOpenScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/open.png')))
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

        # refresh the ui
        self.refreshDebugLevels()
        self.restorePrefs()
        self.overrideKeyboardShortcuts()
        self.uiConsoleTOOLBAR.show()
        import sys, platform

        self.setWindowTitle(
            'Command Logger - %s %s'
            % ('%i.%i.%i' % sys.version_info[:3], platform.architecture()[0])
        )

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
        self.uiWorkboxWGT.execAll()

    def execSelected(self):
        """
            \remarks	Clears the console before executing selected workbox code
        """
        if self.uiClearBeforeRunningACT.isChecked():
            self.clearLog()
        self.uiWorkboxWGT.execSelected()

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
        pref.recordProperty(
            'WorkboxText', unicode(self.uiWorkboxWGT.text()).replace('\r', '')
        )
        pref.recordProperty('SplitterVertical', self.uiEditorVerticalACT.isChecked())
        pref.recordProperty('SplitterSize', self.uiSplitterSPLIT.sizes())
        pref.recordProperty('tabIndent', self.uiIndentationsTabsACT.isChecked())
        pref.recordProperty('wordWrap', self.uiWordWrapACT.isChecked())
        pref.recordProperty(
            'clearBeforeRunning', self.uiClearBeforeRunningACT.isChecked()
        )
        pref.recordProperty('toolbarStates', self.saveState())

        pref.save()

    def restorePrefs(self):
        pref = prefs.find('blurdev\LoggerWindow')
        rect = pref.restoreProperty('loggergeom')
        if rect and not rect.isNull():
            self.setGeometry(rect)
            blurdev.ensureWindowIsVisible(self)
        self.uiWorkboxWGT.setText(pref.restoreProperty('WorkboxText', ''))
        self.uiEditorVerticalACT.setChecked(
            pref.restoreProperty('SplitterVertical', False)
        )
        self.adjustWorkboxOrientation(self.uiEditorVerticalACT.isChecked())
        sizes = pref.restoreProperty('SplitterSize', None)
        if sizes:
            self.uiSplitterSPLIT.setSizes(sizes)
        self.setWindowState(Qt.WindowStates(pref.restoreProperty('windowState', 0)))
        self.uiIndentationsTabsACT.setChecked(pref.restoreProperty('tabIndent', True))
        self.uiWorkboxWGT.setIndentationsUseTabs(self.uiIndentationsTabsACT.isChecked())
        self.uiWordWrapACT.setChecked(pref.restoreProperty('wordWrap', True))
        self.setWordWrap(self.uiWordWrapACT.isChecked())
        self.uiClearBeforeRunningACT.setChecked(
            pref.restoreProperty('clearBeforeRunning', False)
        )
        self.setClearBeforeRunning(self.uiClearBeforeRunningACT.isChecked())
        self.restoreToolbars()

    def restoreToolbars(self):
        pref = prefs.find('blurdev\LoggerWindow')
        state = pref.restoreProperty('toolbarStates', None)
        if state:
            self.restoreState(state)

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
        self.uiWorkboxWGT.setLanguage('Python')
        self.uiWorkboxWGT.setShowSmartHighlighting(True)

    def showSdk(self):
        blurdev.core.sdkBrowser().show()

    def shutdown(self):
        # close out of the ide system

        # if this is the global instance, then allow it to be deleted on close
        if self == LoggerWindow._instance:
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            LoggerWindow._instance = None

        # clear out the system
        self.close()

    @staticmethod
    def instance(parent=None):
        # create the instance for the logger
        if not LoggerWindow._instance:
            # determine default parenting
            if not (parent or blurdev.core.isMfcApp()):
                parent = blurdev.core.rootWindow()

            # create the logger instance
            inst = LoggerWindow(parent)

            # protect the memory
            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            # cache the instance
            LoggerWindow._instance = inst

        return LoggerWindow._instance
