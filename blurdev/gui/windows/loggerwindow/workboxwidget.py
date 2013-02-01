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
        self._searchFlags = 0
        self._searchText = ''
        self._searchDialog = None
        # Store the software name so we can handle custom keyboard shortcuts bassed on software
        import blurdev

        self._software = blurdev.core.objectName()
        self.regex = re.compile('\s+$')
        self.initShortcuts()

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

    def initShortcuts(self):
        """
        Use this to set up shortcuts when the DocumentEditor is not being used in the IdeEditor.
        """
        from blurdev.ide.finddialog import FindDialog
        from PyQt4.QtGui import QAction, QIcon

        self.uiFindACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/find.png')), 'Find...', self
        )
        self.uiFindACT.setShortcut("Ctrl+F")
        self.addAction(self.uiFindACT)
        self.uiFindPrevACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/findprev.png')), 'Find Prev', self
        )
        self.uiFindPrevACT.setShortcut("Ctrl+F3")
        self.addAction(self.uiFindPrevACT)
        self.uiFindNextACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/findnext.png')), 'Find Next', self
        )
        self.uiFindNextACT.setShortcut("F3")
        self.addAction(self.uiFindNextACT)

        self.uiCommentAddACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/comment_add.png')), 'Comment Add', self
        )
        self.uiCommentAddACT.setShortcut("Alt+3")
        self.addAction(self.uiCommentAddACT)

        self.uiCommentRemoveACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/comment_remove.png')),
            'Comment Remove',
            self,
        )
        self.uiCommentRemoveACT.setShortcut("Alt+#")
        self.addAction(self.uiCommentRemoveACT)

        self.uiCommentToggleACT = QAction(
            QIcon(blurdev.resourcePath('img/ide/comment_toggle.png')),
            'Comment Toggle',
            self,
        )
        self.uiCommentToggleACT.setShortcut("Ctrl+Alt+3")
        self.addAction(self.uiCommentToggleACT)

        # create the search dialog and connect actions
        self._searchDialog = FindDialog(self)
        self._searchDialog.setAttribute(Qt.WA_DeleteOnClose, False)
        self.uiFindACT.triggered.connect(
            lambda: self._searchDialog.search(self.searchText())
        )
        self.uiFindPrevACT.triggered.connect(
            lambda: self.findPrev(self.searchText(), self.searchFlags())
        )
        self.uiFindNextACT.triggered.connect(
            lambda: self.findNext(self.searchText(), self.searchFlags())
        )
        self.uiCommentAddACT.triggered.connect(self.commentAdd)
        self.uiCommentRemoveACT.triggered.connect(self.commentRemove)
        self.uiCommentToggleACT.triggered.connect(self.commentToggle)

    def searchFlags(self):
        return self._searchFlags

    def searchText(self):
        if not self._searchDialog:
            return ''
        # refresh the search text unless we are using regular expressions
        if (
            not self._searchDialog.isVisible()
            and not self._searchFlags & self.SearchOptions.QRegExp
        ):
            text = self.selectedText()
            if text:
                self._searchText = text
        return self._searchText

    def selectedText(self):
        return self.regex.split(super(WorkboxWidget, self).selectedText())[0]

    def setConsole(self, console):
        self._console = console

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def setSearchText(self, text):
        self._searchText = text
