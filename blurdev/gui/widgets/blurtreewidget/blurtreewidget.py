##
# 	:namespace	blurtreewidgetwidget
#
# 	:remarks	A tree widget with common blur functionality built in
# 				Features:
# 					- Holding Ctrl when expanding or contracting a item will cascade to all children.
# 					- Single call to add most setup information to a preffrences file(column width, visibility)
# 					- Integrated item gradiation
# 					- Integrated cell borders
# 					- Lockable columns on all 4 sides
#
# 	:author		beta@blur.com
# 	:author		Blur Studio
# 	:date		03/05/11
#
#:Example view, the BlurTreeWidget is added in the UI file
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
# |		# If you have more than one tree widget you can handle the prefrence saving and use diffrnent delegate methods
# |		self.uiTREE.setIdentifier("uniqueName"
# |		# If you set a identifier you will need to change the names of these methods to start with the identifier and
# |		# capitalize the first leter of the name. This does not affect restorePrefs and recordPrefs.
# |		# Example: closeEvent will become uniqueNameCloseEvent
# |
# |		# Restore user prefs
# |		self.restorePrefs()
# |
# |	def closeEvent( self, event ):
# |		self.recordPrefs()
# |		QWidget.closeEvent( self, event )
# |
# |	def createEditor( self, parent, option, index, tree=None ):
# |		from PyQt4.QtGui import QComboBox
# |		editor = QComboBox( parent )
# |		return editor
# |
# |	def drawBranches(self, painter, rect, index, tree):
# |		c = self.uiTREE.itemFromIndex( index).backgroundColor(0)
# |		c.setAlpha(128)
# |		painter.fillRect(rect, c)
# |		super(BlurTreeWidget, tree).drawBranches(painter, rect, index)
# |
# |	def drawRow(self, painter, option, index, tree):
# |		painter.fillRect(option.rect, self.uiTREE.itemFromIndex( index).backgroundColor(1))
# |		super(BlurTreeWidget, tree).drawRow(painter, option, index)
# |
# |	def setEditorData(self, editor, index, tree=None):
# |		if isinstance(editor, QComboBox):
# |			editor.addItems(['Something', 'Else'])
# |
# |	def setModelData(self, editor, model, index, tree=None):
# |		if isinstance(editor, QComboBox):
# |			model.setData(index, editor.currentText())
# |
# |	def dropEvent(self, event, tree=None):
# |		print 'Drop Event', self.uiTREE.indexAt(event.pos()).column()
# |		super(BlurTreeWidget, self.uiTREE).dropEvent(event)
# |
# |	def headerMenu( self, menu, tree=None ):
# |		action = menu.addAction( 'Added by view class' )
# |		return True
# |
# |	def mimeData(self, items, tree=None):
# |		from PyQt4.QtCore import QMimeData
# |		data = QMimeData()
# |		text = []
# |		for item in items:
# |			text.append(unicode(item.text(0)))
# |		data.setText(';'.join(text))
# |		return data
# |
# |	def mimeTypes(self, tree=None):
# |		return [
# |			'text/uri-list',
# |			'application/x-qabstractitemmodeldatalist']
# |
# | def startDrag(self, supportedActions, tree=None):
# |		mimeData = tree.mimeData(tree.selectedItems())
# |
# |		# create the drag
# |		drag = QDrag(tree)
# |		drag.setMimeData(mimeData)
# |
# |		# drag.setPixmap(QPixmap(<path>))
# |		drag.setHotSpot(QPoint(10,10))
# |		drag.exec_()
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
# |
# |	def wheelEvent(self, event, tree=None):
# |		if tree == self.uiPosesTREE:
# |			if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
# |				self.doStuff(event)
# |				event.accept()
# |				return
# |			super(BlurTreeWidget, tree).wheelEvent(event)
# |		event.ignore()

from PyQt4.QtCore import pyqtProperty, Qt, pyqtSlot, pyqtSignal
from PyQt4.QtGui import (
    QItemDelegate,
    QTreeWidget,
    QCursor,
    QMenu,
    QIcon,
    QApplication,
    QTreeWidgetItemIterator,
)
import blurdev
from blurdev.gui.widgets.lockabletreewidget import LockableTreeWidget
from blurdev.gui.delegates.griddelegate import GridDelegate
from blurdev.decorators import pendingdeprecation


class BlurTreeWidget(LockableTreeWidget):
    columnShown = pyqtSignal(int)
    columnsAllShown = pyqtSignal()

    def __init__(self, parent=None):
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
        self._identifier = ''
        # grid Delegate properties
        self._enableGradiated = False

        # create connections
        self.destroyed.connect(self.aboutToBeDestroyed)

    def aboutToBeDestroyed(self):
        """ Prevent crashes due to "delete loops" """
        self._delegate = None

    def buildColumnIndex(self):
        """
            :remarks	Builds column name index. This is called automatically the first time columnIndex or columnNames is called.
        """
        self._columnIndex = []
        headerItem = self.headerItem()
        for column in range(headerItem.columnCount()):
            self._columnIndex.append(unicode(headerItem.text(column)))
        self._indexBuilt = True

    def closeTearOffMenu(self):
        if self._columnsMenu and self._columnsMenu.isTearOffEnabled():
            self._columnsMenu.hideTearOffMenu()

    def columnIndex(self, label):
        """
            :remarks	Returns the column index for column named label. If label is not a <str> it converts it to <str>.
            :return		<int>
        """
        if not self._indexBuilt:
            self.buildColumnIndex()
        if type(label) != str:
            label = unicode(label)
        if label in self._columnIndex:
            return self._columnIndex.index(label)
        return None

    def columnNames(self):
        """
            :Remarks	Returns a list of column names as <str>.
            :return		<list>
        """
        if not self._indexBuilt:
            self.buildColumnIndex()
        return self._columnIndex

    def columnOrder(self):
        order = {}
        header = self.header()
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            order.update({unicode(headerItem.text(column)): header.visualIndex(column)})
        return order

    def columnVisibility(self):
        visibility = {}
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            visibility.update(
                {unicode(headerItem.text(column)): not self.isColumnHidden(column)}
            )
        return visibility

    def columnWidths(self):
        widths = {}
        headerItem = self.headerItem()
        for column in range(self.columnCount()):
            widths.update({unicode(headerItem.text(column)): self.columnWidth(column)})
        return widths

    def connectHeaderMenu(self, view=None):
        if view == None:
            view = self
        header = view.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.showHeaderMenu)

    def delegate(self):
        return self._delegate

    def drawBranches(self, painter, rect, index):
        """
            :remarks	Overloaded. If you add this function to the delegate you can override drawBranches.
                        Draws the branches in the tree view on the same row as the model item index, using 
                        the painter given. The branches are drawn in the rectangle specified by rect.
            :param		painter		<QPainter>
            :param		rect		<QRect>
            :param		index		<QModelIndex>
        """
        name = self.identifierName('drawBranches')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                funct(painter, rect, index, self)
            else:
                funct(painter, rect, index)
        else:
            super(BlurTreeWidget, self).drawBranches(painter, rect, index)

    def drawRow(self, painter, option, index):
        """
            :remarks	Overloaded. If you add this function to the delegate you can override drawRow.
                        Draws the row in the tree view that contains the model item index, using the 
                        painter given. The option control how the item is displayed.
            :param		painter		<QPainter>
            :param		rect		<QStyleOptionViewItem>
            :param		index		<QModelIndex>
        """
        name = self.identifierName('drawRow')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                funct(painter, option, index, self)
            else:
                funct(painter, option, index)
        else:
            super(BlurTreeWidget, self).drawRow(painter, option, index)

    def dropEvent(self, event):
        """
            :remarks	Overloaded. If you add this function to the delegate you can override the dropEvent handling.
            :param		items		<list>
            :return		<QMimeData>
        """
        name = self.identifierName('dropEvent')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                data = funct(event, self)
            else:
                data = funct(event)
        else:
            data = super(BlurTreeWidget, self).dropEvent(event)
        return data

    def enableGridDelegate(self, enable):
        if enable:
            self.setItemDelegate(GridDelegate(self))
            if self._enableGradiated:
                self.setGradiated(True)
        else:
            self.setItemDelegate(QItemDelegate())

    def expandAll(self, state=True):
        """
            :remarks	Expands all the tree items based on the inputed parent item
            :param		state	<bool>	Expand or contract items
        """
        for index in range(self.topLevelItemCount()):
            self.itemExpandAllChildren(self.topLevelItem(index), state)

    def expandParentOfItem(self, item, state=True, recursive=True):
        """
            :Remarks	Expand the parents of this item recursively, to ensure its visible.
            :param		item		<object>
            :param		state		<bool>		Expansion state, defaults to True
            :param		recursive	<bool>		Should this be recusive
        """
        parent = item.parent()
        if parent:
            parent.setExpanded(state)
            if recursive:
                self.expandParentOfItem(parent, state, recursive)

    def expandToDepth(self, depth, item=None):
        """
            :Remarks	Recursively expands children until depth reaches zero. If a item is provided it will only use the children
                        of that item. If no item is passed in it will start with the top level items of this widget.
            :param		depth	<int>						How many levels deep to expand
            :param		item	<QTreeWidgetItem>||None		Item to start with.
        """
        if depth < 0:
            return
        childDepth = depth - 1
        if item:
            item.setExpanded(True)
            for c in range(item.childCount()):
                child = item.child(c)
                self.expandToDepth(childDepth, child)
        else:
            for index in range(self.topLevelItemCount()):
                self.expandToDepth(childDepth, self.topLevelItem(index))

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
            textItems.append(unicode(item))
        return QByteArray(','.join(textItems))

    def identifier(self):
        return self._identifier

    def identifierName(self, name):
        """
            :Remarks	Returns the name. If self._identifier is set it will return place the identifier before name and capitalize the first 
                        letter of name.
            :param		name		<str>
            :Return		<str>		"identifierName" || 'name'
        """
        if self._identifier:
            name = self._identifier + name[0].upper() + name[1:]
        return name

    def isGradiated(self):
        return self._enableGradiated

    def isGridDelegateEnabled(self):
        return type(self.itemDelegate()) == GridDelegate

    def itemCount(self):
        """
            :Remarks	Shows the total number of QTreeWidgetItem's in this tree, it is recursive and will include all children of items.
            :Return		<int>
        """
        total = 0
        for item in self.itemIterator():
            total += 1
        return total

    def itemCountForItem(self, item):
        """
            :Remarks	Recursive function for itemCount
            :Return		<int>
        """
        total = item.childCount()
        for index in range(total):
            total += self.itemCountForItem(item.child(index))
        return total

    def itemIsCollapsed(self, item):
        """
            :remarks	Marks this item as being collapsed, then calls the update items method to reflect the tree state in the dateline scene.  If the user has
                        the CTRL modifier clicked, then the collapse will be recursive
            :param		item	<QTreeWidgetItem>
        """
        if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
            # self.blockSignals( True )
            self.itemExpandAllChildren(item, False)
            # self.blockSignals( False )

    def itemIsExpanded(self, item):
        """
            :remarks	Marks this item as being expanded, then calls the update items method to reflect the tree state in the dateline scene.  If the user has
                        the CTRL modifier clicked, then the expansion will be recursive
            :param		item	<QTreeWidgetItem>
        """
        if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
            # self.blockSignals( True )
            self.itemExpandAllChildren(item, True)
            # self.blockSignals( False )

    def itemIterator(self, selected=None, hidden=None, enabled=None, func=None):
        """ 
        Returns a generator that iterates over the items in a QTreeWidget.
        For more info: http://qt-project.org/doc/qt-4.8/qtreewidgetitemiterator.html
        
        The selected, hidden, and enabled arguments, if set, will only yield items
        that match the given value.
        
        The func argument allows you to pass in a function that takes a treewidgetitem
        as an argument and returns True if it should be yielded, or False if it
        should be skipped.
        """

        flags = QTreeWidgetItemIterator.All
        if selected is not None:
            flags |= (
                QTreeWidgetItemIterator.Selected
                if selected
                else QTreeWidgetItemIterator.Unselected
            )
        if hidden is not None:
            flags |= (
                QTreeWidgetItemIterator.Hidden
                if hidden
                else QTreeWidgetItemIterator.NotHidden
            )
        if enabled is not None:
            flags |= (
                QTreeWidgetItemIterator.Enabled
                if enabled
                else QTreeWidgetItemIterator.Disabled
            )

        iterator = QTreeWidgetItemIterator(self, flags)
        item = iterator.value()
        while item:
            if func is None or func(item):
                yield item
            iterator += 1
            item = iterator.value()

    def itemExpandAllChildren(self, item, state, filter=None, column=0, contains=False):
        """
            :Remarks	Recursively goes down the tree hierarchy expanding/collapsing all the tree items.  This method is called in the expandAll, itemExpanded, and itemCollapsed methods.
            :param		item	<QTreeWidgetItem>
            :param		state	<bool>	Expand or collapse state
            :param		filter	<str>	Only expand items with text in column matching this will be set to state
            :param		column	<int>	The column filter is applied to
            :param		contains	<bool>	If True check if filter is contained in the column text, not that the column text matches the filter.
            :Return		<bool>	Was this item or its children expanded.
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

    def mimeData(self, items):
        """
            :remarks	Overloaded. If you add this function to the delegate you can override the mimeData for drag events.
            :param		items		<list>
            :return		<QMimeData>
        """
        name = self.identifierName('mimeData')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                data = funct(items, self)
            else:
                data = funct(items)
        else:
            data = super(BlurTreeWidget, self).mimeData(items)
        return data

    def mimeTypes(self):
        """ Define the accepted mimeTypes for this tree widget.
        
        Overloaded. If you add this function to the delegate you can override the accepted 
        mimeTypes for drag Events.
        
        Returns:
            list: A list of mime types this tree view accepts.
        """
        name = self.identifierName('mimeTypes')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                data = funct(self)
            else:
                data = funct()
        else:
            data = super(BlurTreeWidget, self).mimeTypes()
        return data

    def prefName(self, name):
        """
            :Remarks	Appends self._identifier to the pref name allowing you to save more than one BlurTreeWidget preffrences in a single file.
            :param		name		<str>
            :Return		<str>		"name-identifier" || 'name'
        """
        names = [name]
        if self._identifier:
            names.append(self._identifier)
        elif self.objectName():
            names.append(unicode(self.objectName()))
        return '-'.join(names)

    def recordOpenState(self, item=None, key=''):
        output = []
        if not item:
            for i in range(self.topLevelItemCount()):
                output += self.recordOpenState(self.topLevelItem(i))
        else:
            text = unicode(item.text(0))
            if item.isExpanded():
                output.append(key + text)
            key += text + '::'
            for c in range(item.childCount()):
                output += self.recordOpenState(item.child(c), key)
        return output

    def recordPrefs(self, pref):
        """
            :remarks	Record tree settings for the provided prefrences. You can control what prefrences get saved by enableing 
                        the various options. If you want to save the prefrences of more than one BlurTreeWidget in the same preffrences
                        file you must set a identifier for each tree.
            
            :param		pref	<blurdev.prefs.Preference>	The pref file to restore from.
            :sa			<BlurTreeWidget.saveColumnWidths>	Save column widths
            :sa			<BlurTreeWidget.saveColumnOrder>	Sace column order
            :sa			<BlurTreeWidget.setIdentifier>	Set a specific identifier for each tree.
        """
        pref.recordProperty(self.prefName('ColumnVis'), self.columnVisibility())
        if self._saveColumnWidths:
            pref.recordProperty(self.prefName('ColumnWidths'), self.columnWidths())
        if self._saveColumnOrder:
            pref.recordProperty(self.prefName('ColumnOrder'), self.columnOrder())
        pref.recordProperty(self.prefName('SortColumn'), self.sortColumn())
        pref.recordProperty(
            self.prefName('SortColumnOrder'), int(self.header().sortIndicatorOrder())
        )

    def resetColumnOrder(self):
        header = self.header()
        for column in range(self.columnCount()):
            header.moveSection(header.visualIndex(column), column)

    def resizeColumnsToContents(self):
        """
            :remarks	Resizes all columns to fit contents, If the header is set to stretch the last section, it will properly stretch the last column if it falls short of the view's width
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
            :remarks	Reduce the width of all columns until they fit on screen.
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
            key = unicode(headerItem.text(column))
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
            key = unicode(headerItem.text(column))
            if key in widths:
                self.setColumnWidth(column, widths[key])
            else:
                self.resizeColumnToContents(column)

    def restoreOpenState(self, openState, item=None, key=''):
        if not item:
            for i in range(self.topLevelItemCount()):
                self.restoreOpenState(openState, self.topLevelItem(i))
        else:
            text = unicode(item.text(0))
            itemkey = key + text
            if itemkey in openState:
                item.setExpanded(True)
            key += text + '::'
            for c in range(item.childCount()):
                self.restoreOpenState(openState, item.child(c), key)

    def restorePrefs(self, pref):
        """
            :remarks	Restore settings if they exist in the provided prefs file.
            :param		pref	<blurdev.prefs.Preference>	The pref file to restore from.
        """
        self.restoreColumnVisibility(
            pref.restoreProperty(self.prefName('ColumnVis'), {})
        )
        if self._saveColumnWidths:
            self.restoreColumnWidths(
                pref.restoreProperty(self.prefName('ColumnWidths'), {})
            )
        if self._saveColumnOrder:
            self.restoreColumnOrder(
                pref.restoreProperty(self.prefName('ColumnOrder'), {})
            )
        self.sortByColumn(
            pref.restoreProperty(self.prefName('SortColumn'), 0),
            pref.restoreProperty(self.prefName('SortColumnOrder'), Qt.AscendingOrder),
        )

    def saveColumnOrder(self):
        return self._saveColumnOrder

    def saveColumnWidths(self):
        return self._saveColumnWidths

    def setColumnCount(self, columns):
        """
            :remarks	overloaded from QTreeWidget.setColumnCount( int columns ). Invalidates column name index before setting column count.
        """
        self._indexBuilt = False
        QTreeWidget.setColumnCount(self, columns)

    def setDelegate(self, delegate):
        self._delegate = delegate
        self.setGridsDelegate(delegate)

    def setGridsDelegate(self, delegate):
        """
            :remarks	If the Grid Delegate is enabled set its delegate to delegate. Seting this allows you to define delegate methods in the controling class instead of subclassing <trax.gui.delegates.griddelegate.GridDelegate>.
            :return		<bool>	Grid Delegate is enabled and its delegate is now set to delegate
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
            :remarks	overloaded from QTreeWidget.setHeaderItem (self, QTreeWidgetItem item). Invalidates column name index before setting header item
        """
        self._indexBuilt = False
        QTreeWidget.setHeaderItem(self, item)

    def setHeaderLabel(self, alabel):
        """
            :remarks	overloaded from QTreeWidget.setHeaderLabel (self, QString alabel). Invalidates column name index before setting header item
        """
        self._indexBuilt = False
        QTreeWidget.setHeaderLabel(self, alabel)

    def setHeaderLabels(self, labels):
        """
            :remarks	overloaded from QTreeWidget.setHeaderLabels (self, QStringList labels). Invalidates column name index before setting header item
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

    @pendingdeprecation(
        "\n# Add a tree argument to the end of your delegate methods instead."
        "# It will contain the BlurTreeWidget the method was called from. For example...\n"
        "# def createEditor(self, parent, option, index, tree):"
        "# If you are using recordPrefs with multiple trees make sure to set objectName"
    )
    def setIdentifier(self, identifier):
        self._identifier = identifier
        if self.isGridDelegateEnabled():
            self.itemDelegate().setIdentifier(identifier)

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
        hideableColumns = self.hideableColumns()
        for column in range(self.columnCount()):
            if hideableColumns[column]:
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
            :remarks	Shows the header menu if the header menu is enabled. It populates the menu with column visiblity if this is enabled.
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
                    text = unicode(header.text(column))
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
        name = self.identifierName('headerMenu')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            if 'tree' in funct.func_code.co_varnames:
                result = funct(menu, self)
            else:
                result = funct(menu)
        # only show the menu if delegate allows it and if there are any actions to show.
        if result and menu.actions():
            menu.popup(cursorPos)

    def startDrag(self, supportedActions):
        """
            :remarks	Overloaded. If you add this function to the delegate you can override the startDrag for drag events.
            :param		DropActions	- QFlags<DropAction> an OR combination of DropAction values
            :return		<QMimeData>
        """
        name = self.identifierName('startDrag')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            data = funct(supportedActions, self)
        else:
            data = super(BlurTreeWidget, self).startDrag(supportedActions)
        return data

    def treeWidth(self):
        """
            :remarks	Calculates the width of the tree's contents
        """
        treeWidth = 0.0
        for column in range(self.columnCount()):
            treeWidth += self.columnWidth(column)
        return treeWidth

    def topLevelItems(self):
        r"""
            :remarks	Returns a list of all top level items.
            :return 	<list>
        """
        return [self.topLevelItem(index) for index in range(self.topLevelItemCount())]

    def updateColumnVisibility(self):
        if self._columnsMenu:
            header = self.headerItem()
            hidden = []
            for column in range(header.columnCount()):
                if self.isColumnHidden(column):
                    hidden.append(column)
            self.showAllColumns()
            for action in self._columnsMenu.actions():
                name = unicode(action.text())
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

    def wheelEvent(self, event):
        name = self.identifierName('wheelEvent')
        if self._delegate and hasattr(self._delegate, name):
            funct = getattr(self._delegate, name)
            # All widgets have wheelEvent, only call it if its been overriden.
            if hasattr(funct, 'func_code'):
                if 'tree' in funct.func_code.co_varnames:
                    funct(event, self)
                else:
                    funct(event)
                return
        super(BlurTreeWidget, self).wheelEvent(event)

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
