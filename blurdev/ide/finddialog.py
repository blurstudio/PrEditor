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


class FindDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        from PyQt4.QtGui import QTextDocument

        self.uiCaseSensitiveCHK.setChecked(
            parent.searchFlags() & QTextDocument.FindCaseSensitively
        )
        self.uiFindWholeWordsCHK.setChecked(
            parent.searchFlags() & QTextDocument.FindWholeWords
        )
        self.uiSearchTXT.setText(parent.searchText())

        # update the signals
        self.uiCaseSensitiveCHK.clicked.connect(self.updateSearchTerms)
        self.uiFindWholeWordsCHK.clicked.connect(self.updateSearchTerms)
        self.uiSearchTXT.textChanged.connect(self.updateSearchTerms)

        self.uiFindNextBTN.clicked.connect(parent.uiFindNextACT.triggered.emit)
        self.uiFindPrevBTN.clicked.connect(parent.uiFindPrevACT.triggered.emit)

    def show(self):
        Dialog.show(self)

        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose, False)

    def updateSearchTerms(self):
        parent = self.parent()
        options = 0
        from PyQt4.QtGui import QTextDocument

        if self.uiCaseSensitiveCHK.isChecked():
            options |= QTextDocument.FindCaseSensitively
        if self.uiFindWholeWordsCHK.isChecked():
            options |= QTextDocument.FindWholeWords

        parent.setSearchFlags(options)
        parent.setSearchText(self.uiSearchTXT.toPlainText())
