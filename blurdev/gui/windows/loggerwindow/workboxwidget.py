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
from PyQt4.QtGui import QApplication
import blurdev, re


class WorkboxWidget(DocumentEditor):
    def __init__(self, parent, console=None):
        # initialize the super class
        DocumentEditor.__init__(self, parent)

        self._console = console
        # Store the software name so we can handle custom keyboard shortcuts bassed on software
        import blurdev

        self._software = blurdev.core.objectName()
        self.regex = re.compile('\s+$')

    def console(self):
        return self._console

    def execAll(self):
        """
            \remarks	reimplement the DocumentEditor.exec_ method to run this code without saving
        """
        import __main__

        exec unicode(self.text()).replace(
            '\r', '\n'
        ).rstrip() in __main__.__dict__, __main__.__dict__

    def execSelected(self):
        text = unicode(self.selectedText()).replace('\r', '\n')
        if not text:
            line, index = self.getCursorPosition()
            text = unicode(self.text(line)).replace('\r', '\n')

        import __main__

        exec text in __main__.__dict__, __main__.__dict__

    def keyPressEvent(self, event):
        if self._software == 'softimage':
            DocumentEditor.keyPressEvent(self, event)
        else:
            if event.key() == Qt.Key_Enter or (
                event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier
            ):
                self.execSelected()
            else:
                DocumentEditor.keyPressEvent(self, event)

    def selectedText(self):
        return self.regex.split(super(WorkboxWidget, self).selectedText())[0]

    def setConsole(self, console):
        self._console = console
