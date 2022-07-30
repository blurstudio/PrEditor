from __future__ import absolute_import

from ..gui import Dialog, loadUi
from .documenteditor import SearchOptions


class FindDialog(Dialog):
    def __init__(self, parent):
        super(FindDialog, self).__init__(parent)

        loadUi(__file__, self)

        self.uiCaseSensitiveCHK.setChecked(
            parent.searchFlags() & SearchOptions.CaseSensitive
        )
        self.uiFindWholeWordsCHK.setChecked(
            parent.searchFlags() & SearchOptions.WholeWords
        )
        self.uiQRegExpCHK.setChecked(parent.searchFlags() & SearchOptions.QRegExp)
        self.uiSearchTXT.setPlainText(parent.searchText())

        # update the signals
        self.uiCaseSensitiveCHK.clicked.connect(self.updateSearchTerms)
        self.uiFindWholeWordsCHK.clicked.connect(self.updateSearchTerms)
        self.uiQRegExpCHK.clicked.connect(self.updateSearchTerms)
        self.uiSearchTXT.textChanged.connect(self.updateSearchTerms)

        self.uiFindNextBTN.clicked.connect(parent.uiFindNextACT.triggered.emit)
        self.uiFindPrevBTN.clicked.connect(parent.uiFindPrevACT.triggered.emit)

        self.uiSearchTXT.installEventFilter(self)
        self.uiSearchTXT.setFocus()
        self.uiSearchTXT.selectAll()

    def eventFilter(self, object, event):
        from Qt.QtCore import QEvent, Qt

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
        self.uiSearchTXT.setPlainText(text)
        self.uiSearchTXT.setFocus()
        self.uiSearchTXT.selectAll()

    def updateSearchTerms(self):
        parent = self.parent()
        options = 0
        if self.uiCaseSensitiveCHK.isChecked():
            options |= SearchOptions.CaseSensitive
        if self.uiFindWholeWordsCHK.isChecked():
            options |= SearchOptions.WholeWords
        if self.uiQRegExpCHK.isChecked():
            options |= SearchOptions.QRegExp

        parent.setSearchFlags(options)
        parent.setSearchText(self.uiSearchTXT.toPlainText())
