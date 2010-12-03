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


class LoggerWindow(Window):

    _instance = None

    def __init__(self, parent):
        Window.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # create the console widget
        from console import ConsoleEdit

        self._console = ConsoleEdit(self)

        # create the layout
        from PyQt4.QtGui import QVBoxLayout

        layout = QVBoxLayout()
        layout.addWidget(self._console)
        self.centralWidget().setLayout(layout)

        # create the connections
        blurdev.core.debugLevelChanged.connect(self.refreshDebugLevels)

        self.uiNewScriptACT.triggered.connect(blurdev.core.newScript)
        self.uiOpenScriptACT.triggered.connect(blurdev.core.openScript)
        self.uiRunScriptACT.triggered.connect(blurdev.core.runScript)
        self.uiGotoErrorACT.triggered.connect(self.gotoError)

        self.uiNoDebugACT.triggered.connect(self.setNoDebug)
        self.uiDebugLowACT.triggered.connect(self.setLowDebug)
        self.uiDebugMidACT.triggered.connect(self.setMidDebug)
        self.uiDebugHighACT.triggered.connect(self.setHighDebug)

        from PyQt4.QtGui import QIcon

        self.uiNoDebugACT.setIcon(QIcon(blurdev.resourcePath('img/debug_off.png')))

        self.uiDebugLowACT.setIcon(QIcon(blurdev.resourcePath('img/debug_low.png')))

        self.uiDebugMidACT.setIcon(QIcon(blurdev.resourcePath('img/debug_mid.png')))

        self.uiDebugHighACT.setIcon(QIcon(blurdev.resourcePath('img/debug_high.png')))

        self.uiResetPathsACT.triggered.connect(self.resetPaths)

        # refresh the ui
        self.refreshDebugLevels()

    def gotoError(self):
        text = self._console.textCursor().selectedText()
        import re

        results = re.match('[ \t]*File "([^"]+)", line (\d+)', unicode(text))
        if results:

            from blurdev.ide import IdeEditor

            IdeEditor.instance().show()

            filename, lineno = results.groups()

            IdeEditor.instance().load(filename, int(lineno))

    def refreshDebugLevels(self):
        from blurdev.debug import DebugLevel, debugLevel

        for act, level in [
            (self.uiNoDebugACT, 0),
            (self.uiDebugLowACT, DebugLevel.Low),
            (self.uiDebugMidACT, DebugLevel.Mid),
            (self.uiDebugHighACT, DebugLevel.High),
        ]:
            act.blockSignals(True)
            act.setChecked(level == debugLevel())
            act.blockSignals(False)

    def resetPaths(self):

        import blurdev

        blurdev.activeEnvironment().resetPaths()

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

    def shutdown(self):

        # close out of the ide system

        from PyQt4.QtCore import Qt

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
            import blurdev

            parent = None
            if not blurdev.core.isMfcApp():
                parent = blurdev.core.rootWindow()

            # create the logger instance

            inst = LoggerWindow(parent)

            # protect the memory

            from PyQt4.QtCore import Qt

            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            # cache the instance
            LoggerWindow._instance = inst

        return LoggerWindow._instance
