##
# 	\namespace	blurdev.models.objecttreemodel
#
# 	\remarks	Creates a QAbstractItemModel for QObject tree hierarchies
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/01/10
#

from PyQt4.QtCore import Qt, QAbstractItemModel


class ObjectTreeModel(QAbstractItemModel):
    def __init__(self, object):
        QAbstractItemModel.__init__(self)

        # store the root object
        self._rootObject = object

    def childrenOf(self, object):
        return object.children()

    def columnCount(self, index):
        return 1

    def data(self, index, role):
        from PyQt4.QtCore import QVariant

        if not index.isValid():
            return QVariant()

        # retrieve the object
        object = index.internalPointer()

        # return the name of the object
        if role == Qt.DisplayRole:
            return object.objectName()

        return QVariant()

    def object(self, index):
        if index and index.isValid():
            return index.internalPointer()
        return None

    def indexOf(self, object, column=0):

        return self.createIndex(self.rowForObject(object), column, object)

    def findObjectAtRow(self, parent, row):
        return parent.children()[row]

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        from PyQt4.QtCore import QVariant

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._rootObject.objectName()
        return QVariant()

    def index(self, row, column, parent=None):
        from PyQt4.QtCore import QModelIndex

        if not parent:
            parent = QModelIndex()

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        # collect children for the root
        if not parent.isValid():
            root = self._rootObject
        else:
            root = parent.internalPointer()

        child = self.findObjectAtRow(root, row)
        if child:
            return self.createIndex(row, column, child)
        return QModelIndex()

    def parent(self, index):
        from PyQt4.QtCore import QModelIndex

        if not index.isValid():
            return QModelIndex()

        object = index.internalPointer()
        parent = object.parent()

        if parent and parent != self._rootObject:
            return self.createIndex(self.rowForObject(parent), 0, parent)

        return QModelIndex()

    def rowCount(self, parent=None):
        from PyQt4.QtCore import QModelIndex

        if not parent:
            parent = QModelIndex()

        if 0 < parent.column():
            return 0

        if not parent.isValid():
            return len(self.childrenOf(self._rootObject))
        else:
            return len(self.childrenOf(parent.internalPointer()))

    def rowForObject(self, object):
        parent = object.parent()
        if not parent:
            return 0

        return parent.children().index(object)
