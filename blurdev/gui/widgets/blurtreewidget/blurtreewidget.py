##
# 	\namespace	blurtreewidgetwidget
#
# 	\remarks	A tree widget with common blur functionality built in
# 				Features:
# 					- Holding Ctrl when expanding or contracting a item will cascade to all children.
# 					- Single call to add most setup information to a preffrences file(column width, visibility)
# 					- Integrated item gradiation
# 					- Integrated cell borders
# 					- Lockable columns on all 4 sides
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		03/05/11
#
# \Example view, the BlurTreeWidget is added in the UI file
# |from PyQt4.QtGui import QWidget
# |
# |class TestWidgetView( QWidget ):
# |	def __init__( self, parent ):
# |		QWidget.__init__( self, parent )
# |
# |		# load the ui
# |		import blurdev.gui
# |		blurdev.gui.loadUi( __file__, self )
# |
# |		# create connections
# |		self.uiTREE.setDelegate( self )
# |
# |		# Restore user prefs
# |		self.restorePrefs()
# |
# |	def closeEvent( self, event ):
# |		self.recordPrefs()
# |		QWidget.closeEvent( self, event )
# |
# |	def createEditor( self, parent, option, index ):
# |		from PyQt4.QtGui import QComboBox
# |		editor = QComboBox( parent )
# |		editor.addItem( 'Something' )
# |		return editor
# |
# |	def headerMenu( self, menu ):
# |		action = menu.addAction( 'Added by view class' )
# |		return True
# |
# |	def recordPrefs( self ):
# |		from trax.gui import prefs
# |		pref = prefs.find( 'Test_Widget_View' )
# |		self.uiTREE.recordPrefs( pref )
# |		pref.save()
# |
# |	def restorePrefs( self ):
# |		from trax.gui import prefs
# |		pref = prefs.find( 'Test_Widget_View' )
# |		self.uiTREE.restorePrefs( pref )

from PyQt4.QtCore import pyqtProperty, Qt, pyqtSlot, pyqtSignal
from PyQt4.QtGui import QItemDelegate, QTreeWidget, QCursor, QMenu, QIcon, QApplication
import blurdev
from blurdev.gui.widgets.lockabletreewidget import LockableTreeWidget
from blurdev.gui.delegates.griddelegate import GridDelegate


class BlurTreeWidget(LockableTreeWidget):
    columnShown = pyqtSignal(int)
    columnsAllShown = pyqtSignal()

    def __init__(self, parent):
        # initialize the super class
        LockableTreeWidget.__init__(self, parent)

        # initialize the ui data
        self.itemExpanded.connect(self.itemIsExpanded)
        self.itemCollapsed.connect(self.itemIsCollapsed)
        self.connectHeaderMenu()

        # create custom properties
        self._userCanHideColumns = False
        self._hideableColumns = []
        self._showColumnControls = False
        self._saveColumnWidths = False
        self._saveColumnOrder = False
        self._columnsMenu = None
        self._delegate = None
        self._showAllColumnsText = 'Show all columns'
        self._columnIndex = []
        self._indexBuilt = False
        # grid Delegate properties
        self._enableGradiated = False

        # create connections
        self.destroyed.connect(self.aboutToBeDestroyed)

    def aboutToBeDestroyed(self):
        """ Prevent crashes due to "delete loops" """
        self._delegate = None

    def buildColumnIndex(self):
        """
            \remarks	Builds column name index. This is called automatically the first time columnIndex or columnNames is called.
        """
        self._columnIndex = []
        headerItem = self.headerItem()
        for column in range(headerItem.columnCount()):
            self._columnIndex.append(str(headerItem.text(column)))
        self._indexBuilt = True

    def closeTearOffMenu(self):
        if self._columnsMenu and self._columnsMenu.isTearOffEnabled():
            self._columnsMenu.hideTearOffMenu()

    def columnIndex(self, label):
        """
            \remarks	Returns the column index for column named label. If label is not a <str> it converts it to <str>.
            \return		<int>
        """
        if not self._indexBuilt:
            self.buildColumnIndex()
        if type(label) != str:
            label = str(label)
        if label in self._columnIndex:
            return self._columnIndex.index(label)
        return None

    def columnNames(self):
        """
            \Remarks	Returns a list of column names as <str>.
            \return		<list>
        """
        if not self._indexBuilt:
            self.buildColumnIndex()
        return self._columnIndex

    def columnOrder(self):
        order = {}
        header = self.header()
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            order.update({str(headerItem.text(column)): header.visualIndex(column)})
        return order

    def columnVisibility(self):
        visibility = {}
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            visibility.update(
                {str(headerItem.text(column)): not self.isColumnHidden(column)}
            )
        return visibility

    def columnWidths(self):
        widths = {}
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            widths.update({str(headerItem.text(column)): self.columnWidth(column)})
        return widths

    def connectHeaderMenu(self, view=None):
        if view == None:
            view = self
        header = view.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.showHeaderMenu)

    def delegate(self):
        return self._delegate

    def enableGridDelegate(self, enable):
        if enable:
            self.setItemDelegate(GridDelegate(self))
            # self.itemDelegate().setDelegate( self )
            if self._enableGradiated:
                self.setGradiated(True)
        else:
            self.setItemDelegate(QItemDelegate())

    def expandAll(self, state=True):
        """
            \remarks	Expands all the tree items based on the inputed parent item
            \param		state	<bool>	Expand or contract items
        """
        for index in range(self.topLevelItemCount()):
            self.itemExpandAllChildren(self.topLevelItem(index), state)

    def hideableColumns(self):
        count = self.columnCount()
        if len(self._hideableColumns) > count:
            self._hideableColumns = self._hideableColumns[:count]
        elif len(self._hideableColumns) < count:
            while len(self._hideableColumns) < count:
                self._hideableColumns.append(1)
        return self._hideableColumns

    def hideableColumnsArray(self):
        from PyQt4.QtCore import QByteArray

        textItems = []
        items = self.hideableColumns()
        for item in items:
            textItems.append(str(item))
        return QByteArray(','.join(textItems))

    def isGradiated(self):
        return self._enableGradiated

    def isGridDelegateEnabled(self):
        return type(self.itemDelegate()) == GridDelegate

    def itemCount(self):
        """
            \Remarks	Shows the total number of QTreeWidgetItem's in this tree, it is recursive and will include all children of items.
            \Return		<int>
        """
        total = self.topLevelItemCount()
        for index in range(total):
            total += self.itemCountForItem(self.topLevelItem(index))
        return total

    def itemCountForItem(self, item):
        """
            \Remarks	Recursive function for itemCount
            \Return		<int>
        """
        total = item.childCount()
        for index in range(total):
            total += self.itemCountForItem(item.child(index))
        return total

    def itemIsCollapsed(self, item):
        """
            \remarks	Marks this item as being collapsed, then calls the update items method to reflect the tree state in the dateline scene.  If the user has
                        the CTRL modifier clicked, then the collapse will be recursive
            \param		item	<QTreeWidgetItem>
        """
        if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
            # self.blockSignals( True )
            self.itemExpandAllChildren(item, False)
            # self.blockSignals( False )

    def itemIsExpanded(self, item):
        """
            \remarks	Marks this item as being expanded, then calls the update items method to reflect the tree state in the dateline scene.  If the user has
                        the CTRL modifier clicked, then the expansion will be recursive
            \param		item	<QTreeWidgetItem>
        """
        if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
            # self.blockSignals( True )
            self.itemExpandAllChildren(item, True)
            # self.blockSignals( False )

    def itemExpandAllChildren(self, item, state, filter=None, column=0, contains=False):
        """
            \Remarks	Recursively goes down the tree hierarchy expanding/collapsing all the tree items.  This method is called in the expandAll, itemExpanded, and itemCollapsed methods.
            \param		item	<QTreeWidgetItem>
            \param		state	<bool>	Expand or collapse state
            \param		filter	<str>	Only expand items with text in column matching this will be set to state
            \param		column	<int>	The column filter is applied to
            \param		contains	<bool>	If True check if filter is contained in the column text, not that the column text matches the filter.
            \Return		<bool>	Was this item or its children expanded.
        """
        result = False
        for c in range(item.childCount()):
            if self.itemExpandAllChildren(
                item.child(c), state, filter, column, contains
            ):
                result = True
        if not result:
            if filter:
                text = item.text(column)
                if (not contains and text == filter) or (
                    contains and filter in unicode(text)
                ):
                    item.setExpanded(state)
                    self.itemExpandAllChildren(item, state)
                    return True
                else:
                    item.setExpanded(not state)
                    return False
            else:
                item.setExpanded(state)
                return False
        else:
            item.setExpanded(state)
            return True

    def prefName(self, name, identifier=''):
        """
            \Remarks	Appends the identifier to the pref name allowing you to save more than one BlurTreeWidget preffrences in a single file.
            \param		name		<str>
            \param		identifier	<str>
            \Return		<str>		"name-identifier" || 'name'
        """
        names = [name]
        if identifier:
            names.append(identifier)
        return '-'.join(names)

    def recordOpenState(self, item=None, key=''):
        output = []
        if not item:
            for i in range(self.topLevelItemCount()):
                output += self.recordOpenState(self.topLevelItem(i))
        else:
            text = str(item.text(0))
            if item.isExpanded():
                output.append(key + text)
            key += text + '::'
            for c in range(item.childCount()):
                output += self.recordOpenState(item.child(c), key)
        return output

    def recordPrefs(self, pref, identifier=''):
        pref.recordProperty(
            self.prefName('ColumnVis', identifier), self.columnVisibility()
        )
        if self._saveColumnWidths:
            pref.recordProperty(
                self.prefName('ColumnWidths', identifier), self.columnWidths()
            )
        if self._saveColumnOrder:
            pref.recordProperty(
                self.prefName('ColumnOrder', identifier), self.columnOrder()
            )
        pref.recordProperty(self.prefName('SortColumn', identifier), self.sortColumn())
        pref.recordProperty(
            self.prefName('SortColumnOrder', identifier),
            int(self.header().sortIndicatorOrder()),
        )
        if self._saveColumnOrder:
            names = ['ColumnOrder']
            if identifier:
                names.append(identifier)
            pref.recordProperty('-'.join(names), self.columnOrder())

    def resetColumnOrder(self):
        header = self.header()
        for column in range(self.columnCount()):
            header.moveSection(header.visualIndex(column), column)

    def resizeColumnsToContents(self):
        """
            \remarks	Resizes all columns to fit contents, If the header is set to stretch the last section, it will properly stretch the last column if it falls short of the view's width
        """
        count = self.columnCount()
        for index in range(count):
            self.resizeColumnToContents(index)
        treeWidth = self.treeWidth()
        viewWidth = self.width()
        # If the tree has resized to smaller than the visible table, resize the last column to fill the remaining if this is enabled
        if self.header().stretchLastSection() and treeWidth < viewWidth:
            treeWidth -= self.columnWidth(-1)
            self.setColumnWidth(-1, viewWidth - treeWidth)

    def resizeColumnsToWindow(self):
        """
            \remarks	Reduce the width of all columns until they fit on screen.
        """
        # get view width and data width
        viewWidth = self.width()
        treeWidth = self.treeWidth()
        # remove the vertical scroll bar width if it is visible
        vert = self.verticalScrollBar()
        if vert.isVisible():
            viewWidth -= vert.width()
        # calculate the percentage each column needs reduced
        resizePercent = viewWidth / treeWidth
        if resizePercent > 1:
            return
        for column in range(self.columnCount()):
            self.setColumnWidth(column, self.columnWidth(column) * resizePercent)

    def restoreColumnOrder(self, order):
        header = self.header()
        headerItem = self.headerItem()
        for name, index in order.items():
            for column in range(self.columnCount()):
                if headerItem.text(column) == name:
                    header.moveSection(header.visualIndex(column), index)
                    break
            else:
                print 'Failed to find item', name, index

    def restoreColumnVisibility(self, visibility):
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            key = str(headerItem.text(column))
            if key in visibility:
                if visibility[key]:
                    self.showColumn(column)
                else:
                    self.hideColumn(column)
            else:
                self.showColumn(column)

    def restoreColumnWidths(self, widths):
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            key = str(headerItem.text(column))
            if key in widths:
                self.setColumnWidth(column, widths[key])
            else:
                self.resizeColumnToContents(column)

    def restoreOpenState(self, openState, item=None, key=''):
        if not item:
            for i in range(self.topLevelItemCount()):
                self.restoreOpenState(openState, self.topLevelItem(i))
        else:
            text = str(item.text(0))
            itemkey = key + text
            if itemkey in openState:
                item.setExpanded(True)
            key += text + '::'
            for c in range(item.childCount()):
                self.restoreOpenState(openState, item.child(c), key)

    def restorePrefs(self, pref, identifier=''):
        self.restoreColumnVisibility(
            pref.restoreProperty(self.prefName('ColumnVis', identifier), {})
        )
        if self._saveColumnWidths:
            self.restoreColumnWidths(
                pref.restoreProperty(self.prefName('ColumnWidths', identifier), {})
            )
        if self._saveColumnOrder:
            self.restoreColumnOrder(
                pref.restoreProperty(self.prefName('ColumnOrder', identifier), {})
            )
        self.sortByColumn(
            pref.restoreProperty(self.prefName('SortColumn', identifier), 0),
            pref.restoreProperty(
                self.prefName('SortColumnOrder', identifier), Qt.DescendingOrder
            ),
        )

        if self._saveColumnOrder:
            names = ['ColumnOrder']
            if identifier:
                names.append(identifier)
            self.restoreColumnOrder(pref.restoreProperty('-'.join(names), {}))

    def setColumnCount(self, columns):
        """
            \remarks	overloaded from QTreeWidget.setColumnCount( int columns ). Invalidates column name index before setting column count.
        """
        self._indexBuilt = False
        QTreeWidget.setColumnCount(self, columns)

    def saveColumnOrder(self):
        return self._saveColumnOrder

    def saveColumnWidths(self):
        return self._saveColumnWidths

    def setDelegate(self, delegate):
        self._delegate = delegate
        self.setGridsDelegate(delegate)

    def setGridsDelegate(self, delegate):
        """
            \remarks	If the Grid Delegate is enabled set its delegate to delegate. Seting this allows you to define delegate methods in the controling class instead of subclassing <trax.gui.delegates.griddelegate.GridDelegate>.
            \return		<bool>	Grid Delegate is enabled and its delegate is now set to delegate
        """
        if self.isGridDelegateEnabled():
            self.itemDelegate().setDelegate(delegate)
            return True
        return False

    def setGradiated(self, state):
        itemDelegate = self.itemDelegate()
        if type(itemDelegate) == GridDelegate:
            itemDelegate.setGradiated(state)
        self._enableGradiated = state

    def setHeaderItem(self, item):
        """
            \remarks	overloaded from QTreeWidget.setHeaderItem (self, QTreeWidgetItem item). Invalidates column name index before setting header item
        """
        self._indexBuilt = False
        QTreeWidget.setHeaderItem(self, item)

    def setHeaderLabel(self, alabel):
        """
            \remarks	overloaded from QTreeWidget.setHeaderLabel (self, QString alabel). Invalidates column name index before setting header item
        """
        self._indexBuilt = False
        QTreeWidget.setHeaderLabel(self, alabel)

    def setHeaderLabels(self, labels):
        """
            \remarks	overloaded from QTreeWidget.setHeaderLabels (self, QStringList labels). Invalidates column name index before setting header item
        """
        self._indexBuilt = False
        QTreeWidget.setHeaderLabels(self, labels)

    def setHideableColumns(self, columns):
        count = self.columnCount()
        while len(columns) < count:
            columns.append(0)
        self._hideableColumns = columns

    def setHideableColumnsArray(self, array):
        split = array.split(',')
        output = []
        failed = False
        for item in split:
            try:
                out = int(item)
                output.append(out)
            except:
                failed = True
                break
        if not failed:
            self._hideableColumns = output

    def setLocked(self, alignment, state, span=1):
        view = LockableTreeWidget.setLocked(self, alignment, state, span)
        if state:
            self.connectHeaderMenu(view)
        return view

    def setSaveColumnOrder(self, state):
        self._saveColumnOrder = state

    def setSaveColumnWidths(self, state):
        self._saveColumnWidths = state

    def setShowColumnControls(self, state):
        self._showColumnControls = state

    def setUserCanHideColumns(self, state):
        self._userCanHideColumns = state

    def showAllColumns(self):
        for column in range(self.columnCount()):
            self.showColumn(column)
            if self.columnWidth(column) == 0:
                self.resizeColumnToContents(column)

    def showAllColumnsMenu(self):
        self.showAllColumns()
        self.closeTearOffMenu()
        self.columnsAllShown.emit()

    def showColumnControls(self):
        return self._showColumnControls

    @pyqtSlot()
    def showHeaderMenu(self):
        """
            \Remarks	Shows the header menu if the header menu is enabled. It populates the menu with column visiblity if this is enabled.
                        If a delegate is set, it will pass the menu item to headerMenu( menu ). You can customize the menu in this delegate function, headerMenu( menu ) must return a <bool> if the menu is to be shown
        """

        menu = QMenu(self)
        header = self.headerItem()

        if self._userCanHideColumns:
            self.closeTearOffMenu()
            self._columnsMenu = QMenu(self)
            self._columnsMenu.setTearOffEnabled(True)

            columns = {}
            hideable = self.hideableColumns()
            for column in range(self.columnCount()):
                if hideable[column]:
                    text = str(header.text(column))
                    state = self.isColumnHidden(column)
                    action = self._columnsMenu.addAction(text)
                    action.setCheckable(True)
                    action.setChecked(not state)
                    action.toggled.connect(self.updateColumnVisibility)
            self._columnsMenu.addSeparator()
            action = self._columnsMenu.addAction(self._showAllColumnsText)
            action.triggered.connect(self.showAllColumnsMenu)

            colAction = menu.addMenu(self._columnsMenu)
            colAction.setText('Column visibility')
        # add columnResizeing options
        if self._showColumnControls:
            menu.addSeparator()
            action = menu.addAction('Resize to fit contents')
            action.triggered.connect(self.resizeColumnsToContents)
            action = menu.addAction('Resize to fit window')
            action.triggered.connect(self.resizeColumnsToWindow)
            if self.header().isMovable():
                menu.addSeparator()
                action = menu.addAction('Reset column order')
                action.triggered.connect(self.resetColumnOrder)

        if self.lockedViews():
            menu.addSeparator()
            action = menu.addAction('Update locked alignment')
            action.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))
            action.triggered.connect(self.updateSizeHints)

        # call delegate so user can add custom menu items if they wish
        result = True
        cursorPos = QCursor.pos()
        if self._delegate and hasattr(self._delegate, 'headerMenu'):
            result = self._delegate.headerMenu(menu)
        # only show the menu if delegate allows it and if there are any actions to show.
        if result and menu.actions():
            menu.popup(cursorPos)

    def treeWidth(self):
        """
            \remarks	Calculates the width of the tree's contents
        """
        treeWidth = 0.0
        for column in range(self.columnCount()):
            treeWidth += self.columnWidth(column)
        return treeWidth

    def updateColumnVisibility(self):
        if self._columnsMenu:
            header = self.headerItem()
            hidden = []
            for column in range(header.columnCount()):
                if self.isColumnHidden(column):
                    hidden.append(column)
            self.showAllColumns()
            for action in self._columnsMenu.actions():
                name = str(action.text())
                if name != self._showAllColumnsText and not action.isSeparator():
                    for column in range(self.columnCount()):
                        if header.text(column) == name:
                            if not action.isChecked():
                                self.hideColumn(column)
                                if column in hidden:
                                    hidden.remove(column)
                            break
            if hidden:
                self.columnShown.emit(hidden[0])

    def userCanHideColumns(self):
        return self._userCanHideColumns

    def visibleTopLevelItem(self, index):
        visibleIndex = 0
        for row in range(self.topLevelItemCount()):
            child = self.topLevelItem(row)
            if not child.isHidden():
                if visibleIndex == index:
                    return child
                visibleIndex += 1
        return None

    pyEnableColumnHideMenu = pyqtProperty(
        'bool', userCanHideColumns, setUserCanHideColumns
    )
    pyShowColumnControls = pyqtProperty(
        'bool', showColumnControls, setShowColumnControls
    )
    pyHideableColumns = pyqtProperty(
        'QByteArray', hideableColumnsArray, setHideableColumnsArray
    )
    pySaveColumnWidths = pyqtProperty('bool', saveColumnWidths, setSaveColumnWidths)
    pySaveVisualIndex = pyqtProperty('bool', saveColumnOrder, setSaveColumnOrder)

    pyEnableGradiated = pyqtProperty('bool', isGradiated, setGradiated)
    pyEnableGridDelegate = pyqtProperty(
        'bool', isGridDelegateEnabled, enableGridDelegate
    )
