##
# 	:namespace	python.blurdev.gui.widgets.lockabletreewidget
#
# 	:remarks
#
# 	:author		beta@blur.com
# 	:author		Blur Studio
# 	:date		12/06/10
#

from Qt import QtCompat
from Qt.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem
from Qt.QtCore import QSize, QTimer, Qt
import blurdev
import sip


class LockableTreeHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None, delegate=None):
        super(LockableTreeHeaderView, self).__init__(orientation, parent)
        self.delegate = delegate

    def mousePressEvent(self, event):
        self.delegate.mousePressEvent(event)
        # super(LockableTreeHeaderView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.delegate.mouseMoveEvent(event)
        # super(LockableTreeHeaderView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.delegate.mouseReleaseEvent(event)
        # super(LockableTreeHeaderView, self).mouseReleaseEvent(event)


class LockableTreeWidget(QTreeWidget):
    def __init__(self, parent):
        # initialize the super class
        QTreeWidget.__init__(self, parent)
        # create lockable options
        self._lockedViews = {}
        self._metric = None
        self._enableAutoHeight = True
        # initialize the tree options
        self.setHorizontalScrollMode(QTreeWidget.ScrollPerPixel)
        self.setVerticalScrollMode(QTreeWidget.ScrollPerPixel)

        # create connections
        self.header().sectionResized.connect(self.updateSectionWidth)

    def _createLockedView(self, alignment, span):
        from Qt.QtWidgets import QTreeView

        # create the view
        view = QTreeView(self)
        view.setModel(self.model())
        view.setItemDelegate(self.itemDelegate())
        view.setFocusPolicy(Qt.NoFocus)
        QtCompat.QHeaderView.setSectionResizeMode(view.header(), view.header().Fixed)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setHorizontalScrollMode(self.horizontalScrollMode())
        view.setVerticalScrollMode(self.horizontalScrollMode())
        view.setSelectionModel(self.selectionModel())
        view.setSelectionMode(self.selectionMode())
        view.setFrameShape(view.NoFrame)
        view.setRootIsDecorated(self.rootIsDecorated())
        view.setColumnWidth(0, self.columnWidth(0))
        view.setVerticalScrollMode(self.verticalScrollMode())
        view.setAlternatingRowColors(self.alternatingRowColors())
        view.setContextMenuPolicy(self.contextMenuPolicy())

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
            view.expanded.connect(self.updateRootItemExpansion)
            view.collapsed.connect(self.updateRootItemCollapsed)
            # connect header sort options
            oldHeader = view.header()
            view.setHeader(
                LockableTreeHeaderView(
                    oldHeader.orientation(), oldHeader.parent(), delegate=self.header()
                )
            )
            view.header().setMovable(False)
            # 			view.header().sortIndicatorChanged.connect(self.sortByColumn)
            self.header().sortIndicatorChanged.connect(self.updateSortView)
            view.setSortingEnabled(self.isSortingEnabled())
            self.header().sectionMoved.connect(self.updateColumnOrders)

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

        # remap click events to the QTreeWidget version
        view.clicked.connect(self.viewClicked)
        view.customContextMenuRequested.connect(self.customContextMenuRequestedForView)

        # update the view
        self.updateLockedGeometry()
        view.show()
        view.raise_()

        return view

    def autoHeight(self):
        return self._enableAutoHeight

    def bindTreeWidgetItem(self, item):
        """
            :remarks    Overrides the setHidden and setExpanded methods for
                        QTreeWidgetItems recursively. Should be replaced with a subclass
                        of QTreeWidget that can update the model without this method as
                        it may introduce memory leaks.
        """
        blurdev.bindMethod(item, 'setHidden', self.setHiddenForItem)
        blurdev.bindMethod(item, 'setExpanded', self.setExpandedForItem)
        for index in range(item.childCount()):
            self.bindTreeWidgetItem(item.child(index))

    def bindTreeWidgetItems(self):
        for index in range(self.topLevelItemCount()):
            self.bindTreeWidgetItem(self.topLevelItem(index))

    def closeEvent(self, event):
        for view, span in self._lockedViews.values():
            view.close()
            view.setParent(None)
            view.deleteLater()
        self._lockedViews.clear()

        QTreeWidget.closeEvent(self, event)

    def customContextMenuRequestedForView(self, point):
        self.customContextMenuRequested.emit(point)

    def enableAutoHeight(self, state):
        """
            :remarks    Controls if updateSizeHintForItem(recursive=True) is called when
                        a item is expaned. Disable for quicker expansion.
            :param		state	<bool>
        """
        self._enableAutoHeight = state

    def initFontMetric(self, font):
        from Qt.QtGui import QFontMetrics

        self._metric = QFontMetrics(font)

    def isLocked(self, alignment):
        return self._lockedViews.get(int(alignment)) is not None

    def lockedViews(self):
        return self._lockedViews

    def resizeEvent(self, event):
        QTreeWidget.resizeEvent(self, event)
        self.updateLockedGeometry()

    def resetVScrollBar(self):
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

    def setExpandedForItem(item, expanded):  # noqa: N805
        # item.treeWidget().setItemExpanded( item, expanded )
        QTreeWidgetItem.setExpanded(item, expanded)
        tree = item.treeWidget()
        if tree:
            if expanded:
                tree.updateItemExpansion(item)
            else:
                tree.updateItemCollapsed(item)

    def setHiddenForItem(item, hidden):  # noqa: N805
        item.treeWidget().setItemHidden(item, hidden)
        # QTreeWidgetItem.setHidden( item )

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
        # return the so locked view so subclasses can access it
        if type(v) == tuple:
            return v[0]
        return v

    def setItemHidden(self, item, hide):
        """
            overrides QTreeWidget.setItemHidden (self, QTreeWidgetItem item, bool hide)
        """
        index = self.indexFromItem(item)
        for view, span in self._lockedViews.values():
            # view.setRowHidden (self, int row, QModelIndex parent, bool hide)
            view.setRowHidden(index.row(), index.parent(), hide)
        # self.blockSignals( True )
        QTreeWidget.setItemHidden(self, item, hide)
        # self.blockSignals( False )

    def setPalette(self, palette):
        super(LockableTreeWidget, self).setPalette(palette)
        for view, span in self._lockedViews.values():
            view.setPalette(palette)

    def setRowHidden(self, row, parent, hide):
        for view, span in self._lockedViews.values():
            view.setRowHidden(row, parent, hide)
        # self.blockSignals( True )
        QTreeWidget.setRowHidden(self, row, parent, hide)
        # self.blockSignals( False )

    def setSortingEnabled(self, state):
        super(LockableTreeWidget, self).setSortingEnabled(state)
        for align in self._lockedViews:
            view, span = self._lockedViews[align]
            view.setSortingEnabled(state)

    def updateColumnOrders(self):
        for align, options in self._lockedViews.items():
            view, span = options
            # update the left item
            if align == int(Qt.AlignLeft):
                for col in range(span):
                    header = self.header()
                    header.moveSection(header.visualIndex(col), col)
            # update the right item
            elif align == int(Qt.AlignRight):
                for col in range(
                    self.columnCount() - 1, self.columnCount() - span - 1, -1
                ):
                    header = self.header()
                    header.moveSection(header.visualIndex(col), col)

    def updateItemExpansion(self, item):
        index = self.indexFromItem(item, 0)
        # for view, span in self._lockedViews.values():
        # view.blockSignals( True )
        # view.setExpanded( index, True )
        # view.blockSignals( False )
        for align in self._lockedViews:
            view, span = self._lockedViews[align]
            view.setExpanded(index, True)
            if self._enableAutoHeight:
                if align == Qt.AlignLeft:
                    colRange = range(span)
                elif align == Qt.AlignRight:
                    count = self.columnCount()
                    colRange = range(count - span, count)
                else:
                    colRange = range(0)
                for column in colRange:
                    QTimer.singleShot(
                        0, lambda: self.updateSizeHintForItem(item, column, 2)
                    )

    def updateItemCollapsed(self, item):
        index = self.indexFromItem(item, 0)
        for view, span in self._lockedViews.values():
            # view.blockSignals( True )
            view.setExpanded(index, False)
            # view.blockSignals( False )

    def updateRootItemCollapsed(self, index):
        item = self.itemFromIndex(index)
        self.collapseItem(item)

    def updateRootItemExpansion(self, index):
        item = self.itemFromIndex(index)
        self.expandItem(item)

    def updateSectionWidth(self, index, oldSize, newSize):
        # update locked views

        for v, span in self._lockedViews.values():
            v.setColumnWidth(index, newSize)

        self.updateLockedGeometry()

    def updateSizeHints(self):
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            for align in self._lockedViews:
                view, span = self._lockedViews[align]
                if align == Qt.AlignLeft:
                    colRange = range(span)
                elif align == Qt.AlignRight:
                    count = self.columnCount()
                    colRange = range(count - span, count)
                else:
                    colRange = range(0)
                for column in colRange:
                    self.updateSizeHintForItem(item, column, recursive=True)

    def updateSizeHintForItem(self, item, column, recursive=0):
        """
            :remarks    Updates the size hint of a QTreeWidgetItem's column, optionaly
                        recursively. recursive is reduced for each child, so you can
                        specify the number of recursions. If recursive is -1 then it
                        will not expire
            :param		item		<QTreeWidgetItem>
            :param		column		<int>
            :param		recursive	<int>				Number of recursions
        """
        if sip.isdeleted(item):
            # The item has been deleted so we have no need to update the sizeHint.
            return
        if recursive:
            for index in range(item.childCount()):
                self.updateSizeHintForItem(item.child(index), column, recursive - 1)
        hint = self.itemSizeHint(item, column)
        if hint.isValid():
            item.setSizeHint(column, hint)

    def updateSortView(self, column, order):
        for align in self._lockedViews:
            view, span = self._lockedViews[align]
            view.blockSignals(True)
            view.sortByColumn(column, order)
            view.blockSignals(False)

    def itemSizeHint(self, item, column):
        # hint = item.sizeHint( column )
        hint = QSize()
        height = self.rowHeight(self.indexFromItem(item, 0))
        if height:
            hint.setHeight(height)
        if not self._metric:
            self.initFontMetric(item.font(column))
        width = self._metric.size(0, item.text(column)).width()
        parent = item.parent()
        while parent:
            parent = parent.parent()
            width += self.indentation()
        hint.setWidth(width)
        return hint

    def updateLockedGeometry(self):
        if not hasattr(self, '_lockedViews'):
            self._lockedViews = {}
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

    def viewClicked(self, index):
        """
            :remarks        convert the QTreeView.clicked to a QTreeView.itemClicked
                            signal for transparent mapping
        """
        item = self.itemFromIndex(index)
        self.itemClicked.emit(item, index.column())
