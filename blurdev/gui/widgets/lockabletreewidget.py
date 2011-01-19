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
        view.setHorizontalScrollMode(self.horizontalScrollMode())
        view.setVerticalScrollMode(self.horizontalScrollMode())
        view.setSelectionModel(self.selectionModel())
        view.setFrameShape(view.NoFrame)
        view.setRootIsDecorated(self.rootIsDecorated())
        view.setColumnWidth(0, self.columnWidth(0))
        view.setVerticalScrollMode(self.verticalScrollMode())
        view.setAlternatingRowColors(self.alternatingRowColors())

        # create vertical alignment options
        if alignment in (Qt.AlignLeft, Qt.AlignRight):
            view.horizontalScrollBar().valueChanged.connect(self.resetHScrollBar)

            self.verticalScrollBar().valueChanged.connect(
                view.verticalScrollBar().setValue
            )
            view.verticalScrollBar().valueChanged.connect(
                self.verticalScrollBar().setValue
            )

            self.itemExpanded.connect(self.updateItemExpansion)
            self.itemCollapsed.connect(self.updateItemCollapsed)

        # create horizontal alignment options
        elif alignment in (Qt.AlignTop, Qt.AlignBottom):
            view.header().hide()
            view.verticalScrollBar().valueChanged.connect(self.resetVScrollBar)

            self.horizontalScrollBar().valueChanged.connect(
                view.horizontalScrollBar().setValue
            )
            view.horizontalScrollBar().valueChanged.connect(
                self.horizontalScrollBar().setValue
            )

        # compound alignment options
        else:
            view.horizontalScrollBar().valueChanged.connect(self.resetHScrollBar)
            view.verticalScrollBar().valueChanged.connect(self.resetVScrollBar)

        # update the view
        self.updateLockedGeometry()
        view.show()
        view.raise_()

        return view

    def closeEvent(self, event):
        for view, span in self._lockedViews.values():
            view.close()
            view.setParent(None)
            view.deleteLater()
        self._lockedViews.clear()

        QTreeWidget.closeEvent(self, event)

    def isLocked(self, alignment):
        return self._lockedViews.get(int(alignment)) != None

    def resizeEvent(self, event):
        QTreeWidget.resizeEvent(self, event)
        self.updateLockedGeometry()

    def resetVScrollBar(self):
        from PyQt4.QtCore import Qt

        for align in self._lockedViews:
            v, span = self._lockedViews[align]

            # lock top scrolling
            if int(Qt.AlignTop) & align:
                bar = v.verticalScrollBar()
                bar.blockSignals(True)
                bar.setValue(0)
                bar.blockSignals(False)

            # lock bottom scrolling
            elif int(Qt.AlignBottom) & align:
                bar = v.verticalScrollBar()
                bar.blockSignals(True)
                bar.setValue(bar.maximum())
                bar.blockSignals(False)

    def resetHScrollBar(self):
        from PyQt4.QtCore import Qt

        for align, options in self._lockedViews.items():
            v, span = options

            # lock left scrolling
            if int(Qt.AlignLeft) & align:
                bar = v.horizontalScrollBar()
                bar.blockSignals(True)
                bar.setValue(0)
                bar.blockSignals(False)

            # lock left scrolling
            elif int(Qt.AlignLeft) & align:
                bar = v.horizontalScrollBar()
                bar.blockSignals(True)
                bar.setValue(bar.maximum())
                bar.blockSignals(False)

    def setLocked(self, alignment, state, span=1):
        v = self._lockedViews.get(int(alignment))

        changed = False

        # create a locked view
        if state:
            if not v:
                v = self._createLockedView(alignment, span)
                # record the locked view
                self._lockedViews[int(alignment)] = (v, span)
                changed = True

        # remove the existing locked view
        elif v:
            w = v[0]
            w.close()
            w.setParent(None)
            w.deleteLater()
            self._lockedViews.pop(int(alignment))
            changed = False

        # create compound locks
        if changed:
            from PyQt4.QtCore import Qt

            self.setLocked(
                Qt.AlignLeft | Qt.AlignTop,
                self.isLocked(Qt.AlignLeft) and self.isLocked(Qt.AlignTop),
            )
            self.setLocked(
                Qt.AlignLeft | Qt.AlignBottom,
                self.isLocked(Qt.AlignLeft) and self.isLocked(Qt.AlignBottom),
            )
            self.setLocked(
                Qt.AlignRight | Qt.AlignTop,
                self.isLocked(Qt.AlignRight) and self.isLocked(Qt.AlignTop),
            )
            self.setLocked(
                Qt.AlignRight | Qt.AlignBottom,
                self.isLocked(Qt.AlignRight) and self.isLocked(Qt.AlignBottom),
            )

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

        for v, span in self._lockedViews.values():
            v.setColumnWidth(index, newSize)

        self.updateLockedGeometry()

    def updateLockedGeometry(self):
        from PyQt4.QtCore import Qt

        for align, options in self._lockedViews.items():
            v, span = options

            w = 0
            h = 0
            x = 0
            y = 0

            # update the left item
            if align == int(Qt.AlignLeft):

                # hide unnecessary columns
                for col in range(span, self.columnCount()):
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in range(span)])
                h = self.viewport().height() + self.header().height()

                x = self.frameWidth()
                y = self.frameWidth()

            # update the right item
            elif align == int(Qt.AlignRight):

                # hide unnecessary columns
                cols = range(self.columnCount() - 1, self.columnCount() - span - 1, -1)
                for col in cols:
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in cols])
                h = self.viewport().height() + self.header().height()

                x = self.width() - self.frameWidth() - w
                y = self.frameWidth()

            # update the top item
            elif align == int(Qt.AlignTop):
                w = self.viewport().width()
                h = sum(
                    [
                        self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                        for i in range(span)
                        if self.topLevelItem(i)
                    ]
                )

                x = self.frameWidth()
                y = self.frameWidth() + self.header().height()

            # update the bottom item
            elif align == int(Qt.AlignBottom):
                w = self.viewport().width()
                h = sum(
                    [
                        self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                        for i in range(
                            self.topLevelItemCount() - 1,
                            self.topLevelItemCount() - span - 1,
                            -1,
                        )
                        if self.topLevelItem(i)
                    ]
                )

                x = self.frameWidth()
                y = self.height() - self.frameWidth() - h

            # update the top left item
            elif align == int(Qt.AlignLeft | Qt.AlignTop):
                colspan = self._lockedViews.get(int(Qt.AlignLeft), (None, 0))[1]
                rowspan = self._lockedViews.get(int(Qt.AlignTop), (None, 0))[1]

                # hide unnecessary columns
                for col in range(colspan, self.columnCount()):
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in range(colspan)])
                h = (
                    sum(
                        [
                            self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                            for i in range(rowspan)
                            if self.topLevelItem(i)
                        ]
                    )
                    + self.header().height()
                )

                x = self.frameWidth()
                y = self.frameWidth()

            # update the top right item
            elif align == int(Qt.AlignRight | Qt.AlignTop):
                colspan = self._lockedViews.get(int(Qt.AlignRight), (None, 0))[1]
                rowspan = self._lockedViews.get(int(Qt.AlignTop), (None, 0))[1]

                # hide unnecessary columns
                cols = range(
                    self.columnCount() - 1, self.columnCount() - colspan - 1, -1
                )
                for col in cols:
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in cols])
                h = (
                    sum(
                        [
                            self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                            for i in range(rowspan)
                            if self.topLevelItem(i)
                        ]
                    )
                    + self.header().height()
                )

                x = self.width() - self.frameWidth() - w
                y = self.frameWidth()

            # update the bottom left item
            elif align == int(Qt.AlignLeft | Qt.AlignBottom):
                colspan = self._lockedViews.get(int(Qt.AlignLeft), (None, 0))[1]
                rowspan = self._lockedViews.get(int(Qt.AlignBottom), (None, 0))[1]

                # hide unnecessary columns
                for col in range(colspan, self.columnCount()):
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in range(colspan)])
                h = sum(
                    [
                        self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                        for i in range(
                            self.topLevelItemCount() - 1,
                            self.topLevelItemCount() - rowspan - 1,
                            -1,
                        )
                        if self.topLevelItem(i)
                    ]
                )

                x = self.frameWidth()
                y = self.height() - self.frameWidth() - h

            # update the bottom right item
            elif align == int(Qt.AlignRight | Qt.AlignBottom):
                colspan = self._lockedViews.get(int(Qt.AlignRight), (None, 0))[1]
                rowspan = self._lockedViews.get(int(Qt.AlignBottom), (None, 0))[1]

                # hide unnecessary columns
                cols = range(
                    self.columnCount() - 1, self.columnCount() - colspan - 1, -1
                )
                for col in cols:
                    v.setColumnHidden(col, True)

                w = sum([self.columnWidth(c) for c in cols])
                h = sum(
                    [
                        self.rowHeight(self.indexFromItem(self.topLevelItem(i)))
                        for i in range(
                            self.topLevelItemCount() - 1,
                            self.topLevelItemCount() - rowspan - 1,
                            -1,
                        )
                        if self.topLevelItem(i)
                    ]
                )

                x = self.width() - self.frameWidth() - w
                y = self.height() - self.frameWidth() - h

            v.setGeometry(x, y, w, h)
