##
# 	\namespace	python.blurdev.gui.widgets.lockabletreewidget
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		12/06/10
#


from PyQt4.QtGui import QTreeWidget


class LockableTreeWidget(QTreeWidget):
    def __init__(self, parent):

        # initialize the super class

        QTreeWidget.__init__(self, parent)

        # initialize the tree options

        self.setHorizontalScrollMode(QTreeWidget.ScrollPerPixel)

        self.setVerticalScrollMode(QTreeWidget.ScrollPerPixel)

        # create lockable options

        self._lockedViews = {}

        # create connections

        self.header().sectionResized.connect(self.updateSectionWidth)

    def _createLockedView(self, alignment, span):

        from PyQt4.QtGui import QTreeView

        from PyQt4.QtCore import Qt

        # create the view

        view = QTreeView(self)

        view.setModel(self.model())

        view.setItemDelegate(self.itemDelegate())

        view.setFocusPolicy(Qt.NoFocus)

        view.header().setResizeMode(view.header().Fixed)

        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        view.setSelectionModel(self.selectionModel())

        view.setFrameShape(view.NoFrame)

        view.setRootIsDecorated(self.rootIsDecorated())

        view.setColumnWidth(0, self.columnWidth(0))

        view.setVerticalScrollMode(self.verticalScrollMode())

        view.setAlternatingRowColors(self.alternatingRowColors())

        # create vertical alignment options

        if alignment in (Qt.AlignLeft, Qt.AlignRight):

            for c in range(span, self.columnCount()):

                view.setColumnHidden(c, True)

            self.verticalScrollBar().valueChanged.connect(
                view.verticalScrollBar().setValue
            )

            view.verticalScrollBar().valueChanged.connect(
                self.verticalScrollBar().setValue
            )

            self.itemExpanded.connect(self.updateItemExpansion)

            self.itemCollapsed.connect(self.updateItemCollapsed)

        # create horizontal alignment options

        else:

            view.header().hide()

            view.verticalScrollBar().valueChanged.connect(self.resetVScrollBar)

            self.horizontalScrollBar().valueChanged.connect(
                view.horizontalScrollBar().setValue
            )

            view.horizontalScrollBar().valueChanged.connect(
                self.horizontalScrollBar().setValue
            )

        # update the view

        view.show()

        self.updateLockedGeometry()

        viewport = self.viewport()

        for v, span in self._lockedViews.values():

            self.viewport().stackUnder(v)

        return view

    def isLocked(self, alignment):

        return self._lockedViews.get(int(alignment)) != None

    def resizeEvent(self, event):

        QTreeWidget.resizeEvent(self, event)

        self.updateLockedGeometry()

    def resetVScrollBar(self):

        from PyQt4.QtCore import Qt

        v, span = self._lockedViews.get(int(Qt.AlignTop), (None, 0))

        if v:

            bar = v.verticalScrollBar()

            bar.blockSignals(True)

            bar.setValue(0)

            bar.blockSignals(False)

        v, span = self._lockedViews.get(int(Qt.AlignBottom), (None, 0))

        if v:

            bar = v.verticalScrollBar()

            bar.blockSignals(True)

            bar.setValue(0)

            bar.blockSignals(False)

    def setLocked(self, alignment, state, span=1):

        v = self._lockedViews.get(int(alignment))

        # create a locked view

        if state:

            if not v:

                v = self._createLockedView(alignment, span)

            # record the locked view

            self._lockedViews[int(alignment)] = (v, span)

        # remove the existing locked view

        elif v:

            v.close()

            v.setParent(None)

            v.deleteLater()

            self._lockedViews.pop(int(alignment))

    def updateItemExpansion(self, item):

        index = self.indexFromItem(item, 0)

        for view, span in self._lockedViews.values():

            view.setExpanded(index, True)

    def updateItemCollapsed(self, item):

        index = self.indexFromItem(item, 0)

        for view, span in self._lockedViews.values():

            view.setExpanded(index, False)

    def updateSectionWidth(self, index, oldSize, newSize):

        # update locked views

        from PyQt4.QtCore import Qt

        # update locked vertical columns

        v, span = self._lockedViews.get(int(Qt.AlignLeft), (None, 0))

        if v and index < span:

            v.setColumnWidth(index, newSize)

        v, span = self._lockedViews.get(int(Qt.AlignRight), (None, 0))

        if v and self.columnCount() - span <= index:

            v.setColumnWidth(index, newSize)

        # update locked horizontal columns

        v, span = self._lockedViews.get(int(Qt.AlignTop), (None, 0))

        if v:

            v.setColumnWidth(index, newSize)

        v, span = self._lockedViews.get(int(Qt.AlignBottom), (None, 0))

        if v:

            v.setColumnWidth(index, newSize)

        self.updateLockedGeometry()

    def updateLockedGeometry(self):

        from PyQt4.QtCore import Qt

        for align, options in self._lockedViews.items():

            v, span = options

            # update the left item

            if align == Qt.AlignLeft:

                x = self.frameWidth()

                y = self.frameWidth()

                w = sum([self.columnWidth(c) for c in range(span)])

                h = self.viewport().height() + self.header().height()

            # update the right item

            elif align == Qt.AlignRight:

                w = sum(
                    [
                        self.columnWidth(c)
                        for c in range(
                            self.columnCount() - 1, -1, self.columnCount() - span
                        )
                    ]
                )

                h = self.viewport().height() + self.header().height()

                x = self.width() - self.frameWidth() - w

                h = self.viewport().height() + self.header().height()

            # update the top item

            elif align == Qt.AlignTop:

                x = self.frameWidth()

                y = self.frameWidth() + self.header().height()

                w = self.viewport().width()

                h = 0

                for i in range(span):

                    item = self.topLevelItem(i)

                    if item:

                        h += self.rowHeight(self.indexFromItem(item))

            # update the bottom item

            elif align == Qt.AlignBottom:

                w = self.viewport().width()

                h = 0

                for i in range(span):

                    item = self.topLevelItem(i)

                    if item:

                        h += self.rowHeight(self.indexFromItem(item))

                x = self.frameWidth()

                y = self.height() - self.frameWidth() - h

            v.setGeometry(x, y, w, h)
