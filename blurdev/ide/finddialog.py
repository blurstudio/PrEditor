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
from blurdev.ide.documenteditor import DocumentEditor


class FindDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self.uiCaseSensitiveCHK.setChecked(
            parent.searchFlags() & DocumentEditor.SearchOptions.CaseSensitive
        )
        self.uiFindWholeWordsCHK.setChecked(
            parent.searchFlags() & DocumentEditor.SearchOptions.WholeWords
        )
        self.uiQRegExpCHK.setChecked(
            parent.searchFlags() & DocumentEditor.SearchOptions.QRegExp
        )
        self.uiSearchTXT.setText(parent.searchText())

        # update the signals
        self.uiCaseSensitiveCHK.clicked.connect(self.updateSearchTerms)
        self.uiFindWholeWordsCHK.clicked.connect(self.updateSearchTerms)
        self.uiSearchTXT.textChanged.connect(self.updateSearchTerms)

        self.uiFindNextBTN.clicked.connect(parent.uiFindNextACT.triggered.emit)
        self.uiFindPrevBTN.clicked.connect(parent.uiFindPrevACT.triggered.emit)

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

    def search(self, text):
        # show the dialog
        self.show()

        # set the search text
        self.uiSearchTXT.setText(text)
        self.uiSearchTXT.setFocus()
        self.uiSearchTXT.selectAll()

    def updateSearchTerms(self):
        parent = self.parent()
        options = 0
        if self.uiCaseSensitiveCHK.isChecked():
            options |= DocumentEditor.SearchOptions.CaseSensitive
        if self.uiFindWholeWordsCHK.isChecked():
            options |= DocumentEditor.SearchOptions.WholeWords
        if self.uiQRegExpCHK.isChecked():
            options |= DocumentEditor.SearchOptions.QRegExp

        parent.setSearchFlags(options)
        parent.setSearchText(self.uiSearchTXT.toPlainText())
