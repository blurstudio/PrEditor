##
# 	\namespace	python.blurdev.gui.windows.loggerwindow.workboxwidget
#
# 	\remarks	A area to save and run code past the existing session
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		03/17/11
#

from PyQt4.QtGui import QTextEdit
from PyQt4.QtCore import QEvent, Qt
from blurdev.ide.documenteditor import DocumentEditor
import blurdev


class WorkboxWidget(DocumentEditor):
    def __init__(self, parent, console=None):
        # initialize the super class
        DocumentEditor.__init__(self, parent)

        self._console = console
        # define the user interface data

    #! 		finish initializing the class

    # create custom properties
    #! 		self._customProperty = ''

    # create connections
    #! 		self.uiNameTXT.textChanged.connect( self.setCustomProperty )

    def console(self):
        return self._console

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if blurdev.application.keyboardModifiers() == Qt.ControlModifier:
                if self._console:
                    # grab the command from the selected line
                    text = self.selectedText()
                    self._console.executeCommand(text)

        DocumentEditor.keyPressEvent(self, event)

    def setConsole(self, console):
        self._console = console
