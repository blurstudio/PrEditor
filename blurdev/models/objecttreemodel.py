##
# 	\namespace	blurdev.models.objecttreemodel
#
# 	\remarks	Creates a QAbstractItemModel for QObject tree hierarchies
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/01/10
#

from __future__ import absolute_import
from Qt.QtCore import QAbstractItemModel, Qt


class ObjectTreeModel(QAbstractItemModel):
    def __init__(self, object):
        QAbstractItemModel.__init__(self)

        # store the root object
        self._rootObject = object

    def childrenOf(self, parent):
        """Returns a list of the children for the inputed object, by default will
        return the QObject's children

        Args:
            parent (QObject):

        Returns:
            list:
        """
        return parent.children()

    def columnCount(self, index):

        """Returns the number of columns the inputed model has

        Args:
            index (QModelIndex):

        Returns:
            int:
        """
        return 1

    def data(self, index, role):
        """Returns a variant containing the information for the inputed index and
        the given role

        Args:
            index (QModelIndex):
            role (Qt::Role):
        """

        # return the name of the object
        if index.isValid() and role == Qt.DisplayRole:
            return index.internalPointer().objectName()

        # for all else, return a blank variant
        return None

    def object(self, index):
        """Returns the object that the index contains

        Args:
            index (QModelIndex):

        Returns:
            QObject:
        """
        if index and index.isValid():
            return index.internalPointer()
        return None

    def indexOf(self, object, column=0):
        """Returns a model index representing the inputed object at the given column

        Args:
            object (QObject)
            column (int)

        Returns:
            QModelIndex):
        """

        return self.createIndex(self.rowForObject(object), column, object)

    def findObjectAtRow(self, parent, row):
        """Returns the child object of the inputed parent at the given row

        Args:
            parent (QObject):
            column (int):

        Returns:
            QModelIndex:
        """
        return self.childrenOf(parent)[row]

    def flags(self, index):

        """Returns the item flags for the inputted index

        Args:
            index (QModelIndex):

        Returns:
            QModelIndex:
        """
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._rootObject.objectName()
        return None

    def index(self, row, column, parent):

        from Qt.QtCore import QModelIndex

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
        from Qt.QtCore import QModelIndex

        if not index.isValid():
            return QModelIndex()

        object = index.internalPointer()
        try:
            parent = object.parent()
        except Exception:
            parent = None

        if parent and parent != self._rootObject:
            return self.createIndex(self.rowForObject(parent), 0, parent)

        return QModelIndex()

    def rootObject(self):
        return self._rootObject

    def rowCount(self, parent):
        from Qt.QtCore import QModelIndex

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

        children = self.childrenOf(parent)
        if object in children:
            return children.index(object)
        return 0
