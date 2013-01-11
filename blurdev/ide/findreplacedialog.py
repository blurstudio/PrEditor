##
# 	\namespace	[FILENAME]
#
# 	\remarks	[ADD REMARKS]
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/01/10
#

from blurdev.gui import Dialog


class FindReplaceDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self.uiSearchTXT.setText(parent.searchText())

        # update the signals
        self.uiSearchTXT.textChanged.connect(self.updateSearchTerms)

        self.uiFindNextBTN.clicked.connect(parent.uiFindNextACT.triggered.emit)
        self.uiFindPrevBTN.clicked.connect(parent.uiFindPrevACT.triggered.emit)
        self.uiReplaceBTN.clicked.connect(parent.uiReplaceACT.triggered.emit)
        self.uiReplaceBTN.clicked.connect(parent.uiFindNextACT.triggered.emit)
        self.uiReplaceAllBTN.clicked.connect(parent.uiReplaceAllACT.triggered.emit)
        self.uiCloseBTN.clicked.connect(self.close)

        self.uiSearchTXT.installEventFilter(self)
        self.uiSearchTXT.setFocus()
        self.uiSearchTXT.selectAll()

    def eventFilter(self, object, event):
        from PyQt4.QtCore import QEvent, Qt

        if event.type() == QEvent.KeyPress:
            if (
                event.key() in (Qt.Key_Enter, Qt.Key_Return)
                and not event.modifiers() == Qt.ShiftModifier
            ):
                self.parent().uiFindNextACT.triggered.emit(True)
                self.accept()
                return True
        return False

    def replaceText(self):
        return self.uiReplaceTXT.toPlainText()

    def search(self, text):
        # show the dialog
        self.show()

        # set the search text
        self.uiSearchTXT.setText(text)
        self.uiSearchTXT.setFocus()
        self.uiSearchTXT.selectAll()

    def updateSearchTerms(self):
        parent = self.parent()
        parent.setSearchText(self.uiSearchTXT.toPlainText())
