##
# 	\namespace	blurdev.ide.idemethodbrowserdialog
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/16/11
#

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import QTreeWidgetItem, QPalette, QIcon

import blurdev
import os.path

from blurdev.gui import Dialog


class IdeMethodBrowserDialog(Dialog):
    def __init__(self, ide):
        Dialog.__init__(self, ide)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # set the icons
        from PyQt4.QtGui import QIcon

        self.uiRefreshBTN.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))

        # setup the stretching
        header = self.uiMethodTREE.header()
        header.setResizeMode(0, header.Stretch)
        header.setResizeMode(1, header.ResizeToContents)

        # create connections
        ide.currentDocumentChanged.connect(self.refresh)
        self.uiRefreshBTN.clicked.connect(self.refresh)
        self.uiMethodTREE.itemClicked.connect(self.navigateToItem)
        self.uiSortedCHK.clicked.connect(self.updateSorting)
        self.uiSearchTXT.textChanged.connect(self.filterItems)

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
        document = self.parent().currentDocument()
        document.goToLine(int(item.text(1)))
        document.window().activateWindow()
        document.setFocus()

    def refresh(self):
        # only refresh for visible trees
        if not self.isVisible():
            return False

        # refresh the tree methods
        self.uiMethodTREE.setUpdatesEnabled(False)
        self.uiMethodTREE.blockSignals(True)

        self.uiMethodTREE.clear()

        document = self.parent().currentDocument()
        if document:
            import re
            from blurdev.ide import lang

            language = lang.byName(document.language())
            if language:
                descriptors = language.descriptors()

                if descriptors:
                    levelstack = []
                    text = self.parent().currentDocument().text()
                    lines = text.split('\n')
                    clr = self.uiMethodTREE.palette().color(QPalette.Base).darker(140)

                    for lineno, line in enumerate(lines):
                        for descriptor in descriptors:
                            results = descriptor.match(str(line))

                            if results:
                                item = QTreeWidgetItem(
                                    [results['name'], '%05i' % (lineno + 1)]
                                )
                                iconpath = blurdev.resourcePath(
                                    'img/ide/%s.png' % results['type'].lower()
                                )
                                if not os.path.exists(iconpath):
                                    iconpath = blurdev.resourcePath(
                                        'img/ide/function.png'
                                    )

                                item.setSizeHint(0, QSize(0, 20))
                                item.setIcon(0, QIcon(iconpath))
                                item.setTextAlignment(
                                    1, Qt.AlignRight | Qt.AlignVCenter
                                )
                                item.setForeground(1, clr)

                                # make sure we have a previous level
                                currlevel = results['level']
                                while levelstack and currlevel <= levelstack[-1][0]:
                                    levelstack.pop()

                                # append the item to the current level
                                if levelstack:
                                    levelstack[-1][1].addChild(item)
                                else:
                                    self.uiMethodTREE.addTopLevelItem(item)

                                # append the parenting level
                                levelstack.append((currlevel, item))

        self.updateSorting()
        self.filterItems(self.uiSearchTXT.text())

        self.uiMethodTREE.setUpdatesEnabled(True)
        self.uiMethodTREE.blockSignals(False)

    def show(self):
        Dialog.show(self)
        self.refresh()

    def updateSorting(self):
        from PyQt4.QtCore import Qt

        if self.uiSortedCHK.isChecked():
            self.uiMethodTREE.sortByColumn(0, Qt.AscendingOrder)
        else:
            self.uiMethodTREE.sortByColumn(1, Qt.AscendingOrder)
