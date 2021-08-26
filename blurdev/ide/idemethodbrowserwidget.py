##
# 	\namespace	blurdev.ide.idemethodbrowserwidget
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/16/11
#

from __future__ import absolute_import
from Qt.QtCore import QSize, Qt
from Qt.QtGui import QIcon, QPalette
from Qt.QtWidgets import QTreeWidgetItem, QVBoxLayout, QWidget
from Qt import QtCompat

import blurdev
import os.path

from blurdev.gui import Dialog


class IdeMethodBrowserWidget(QWidget):
    def __init__(self, ide):
        QWidget.__init__(self, ide)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self._document = None
        self._resultcache = []
        self._levelstack = []
        self._ide = ide

        # set the icons
        from Qt.QtGui import QIcon

        self.uiRefreshBTN.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))

        # setup the stretching
        header = self.uiMethodTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.Stretch)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)

        # create connections
        ide.currentDocumentChanged.connect(self.refresh)
        self.uiRefreshBTN.clicked.connect(self.refresh)
        self.uiMethodTREE.itemClicked.connect(self.navigateToItem)
        self.uiSortedCHK.clicked.connect(self.updateSorting)
        self.uiSearchTXT.textChanged.connect(self.filterItems)

    def cacheResult(self, text, position=0, currlevel='', typeName='function'):
        self._resultcache.append((text, position, currlevel, typeName))

    def addCachedResults(self):
        self._resultcache.sort(key=lambda x: x[1])
        for text, position, currlevel, typeName in self._resultcache:
            self.addItem(text, position, currlevel, typeName)

    def addItem(self, text, position=0, currlevel='', typeName='function'):
        clr = self.uiMethodTREE.palette().color(QPalette.Base).darker(140)
        item = QTreeWidgetItem(
            [
                text.replace('\n', '').replace('\t', '').replace(' ', ''),
                '%05i' % (self._document.lineIndexFromPosition(position)[0] + 1),
            ]
        )
        iconpath = blurdev.resourcePath('img/ide/%s.png' % typeName.lower())
        if not os.path.exists(iconpath):
            iconpath = blurdev.resourcePath('img/ide/function.png')

        item.setSizeHint(0, QSize(0, 20))
        item.setIcon(0, QIcon(iconpath))
        item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
        item.setForeground(1, clr)

        # make sure we have a previous level
        if not currlevel:
            self._levelstack = []

        while self._levelstack and currlevel <= self._levelstack[-1][0]:
            self._levelstack.pop()

        # append the item to the current level
        if self._levelstack:
            self._levelstack[-1][1].addChild(item)
        else:
            self.uiMethodTREE.addTopLevelItem(item)

        # append the parenting level
        self._levelstack.append((currlevel, item))

    def filterItems(self, text, item=None):
        # sort from the root
        if not item:
            text = str(text).lower()
            for i in range(self.uiMethodTREE.topLevelItemCount()):
                self.filterItems(text, self.uiMethodTREE.topLevelItem(i))
            return False
        else:
            found = False
            for c in range(item.childCount()):
                if self.filterItems(text, item.child(c)):
                    found = True

            # restore to original state
            if not text:
                item.setHidden(False)
                found = True

            # show found state
            elif found or text in str(item.text(0)).lower():
                item.setHidden(False)
                item.setExpanded(True)
                found = True

            # show hidden state
            else:
                item.setHidden(True)
                found = False

            return found

    def navigateToItem(self, item):
        self._document.goToLine(int(item.text(1)))
        self._document.window().activateWindow()
        self._document.setFocus()

    def refresh(self):
        # only refresh for visible trees
        if not self.isVisible():
            return False

        # refresh the tree methods
        self.uiMethodTREE.setUpdatesEnabled(False)
        self.uiMethodTREE.blockSignals(True)

        self.uiMethodTREE.clear()
        self._resultcache = []
        self._levelstack = []

        self._document = self._ide.currentDocument()

        # parse out the results for the document
        if self._document:
            from blurdev.ide import lang

            language = lang.byName(self._document.language())
            if language:
                descriptors = language.descriptors()

                if descriptors:
                    try:
                        text = str(self._ide.currentDocument().text())
                    except Exception:
                        self.cacheResult('Error converting text to string')
                        text = ''

                    if text:
                        for descriptor in descriptors:
                            result = descriptor.search(text)

                            while result:
                                self.cacheResult(
                                    result.group('name'),
                                    result.start(),
                                    result.group('level'),
                                    result.groupdict().get('type', descriptor.dtype),
                                )
                                result = descriptor.search(text, result.end())

        # add the items to the tree
        self.addCachedResults()

        self.updateSorting()
        self.filterItems(self.uiSearchTXT.text())
        self.uiMethodTREE.expandAll()

        self.uiMethodTREE.setUpdatesEnabled(True)
        self.uiMethodTREE.blockSignals(False)

    def show(self):
        QWidget.show(self)
        self.refresh()

    def updateSorting(self):
        from Qt.QtCore import Qt

        if self.uiSortedCHK.isChecked():
            self.uiMethodTREE.sortByColumn(0, Qt.AscendingOrder)
        else:
            self.uiMethodTREE.sortByColumn(1, Qt.AscendingOrder)

    @staticmethod
    def dialog(ide=None):
        dialog = Dialog(ide)
        widget = IdeMethodBrowserWidget(ide)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.show()
        return dialog
