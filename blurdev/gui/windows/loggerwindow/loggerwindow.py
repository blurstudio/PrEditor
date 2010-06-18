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
