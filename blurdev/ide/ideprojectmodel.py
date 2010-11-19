##
# 	\namespace	blurdev.ide.ideprojectmodel
#
# 	\remarks	Creates a treeview model for viewing IdeProject hierarchies
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from blurdev.models.objecttreemodel import ObjectTreeModel


class IdeProjectModel(ObjectTreeModel):
    def filePath(self, index):
        if index and index.isValid():
            return index.internalPointer().filePath()
        return ''

    def data(self, index, role):
        from PyQt4.QtCore import Qt

        if role == Qt.DecorationRole:
            if index and index.isValid():
                return index.internalPointer().icon()
        return ObjectTreeModel.data(self, index, role)
