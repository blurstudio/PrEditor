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
    def __init__(self, parent):
        Window.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # disable the delete on close attribute
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # create the console widget
        from console import ConsoleEdit

        console = ConsoleEdit(self)

        # create the layout
        from PyQt4.QtGui import QVBoxLayout

        layout = QVBoxLayout()
        layout.addWidget(console)
        self.centralWidget().setLayout(layout)

        # create the connections
        blurdev.core.debugLevelChanged.connect(self.refreshDebugLevels)
        self.uiNoDebugACT.triggered.connect(self.setNoDebug)
        self.uiDebugLowACT.triggered.connect(self.setLowDebug)
        self.uiDebugMidACT.triggered.connect(self.setMidDebug)
        self.uiDebugHighACT.triggered.connect(self.setHighDebug)

        # refresh the ui
        self.refreshDebugLevels()

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
