from __future__ import absolute_import

import re

from Qt.QtCore import QSortFilterProxyModel, Qt
from Qt.QtGui import QStandardItem, QStandardItemModel


class WorkboxItemModel(QStandardItemModel):
    def __init__(self, manager, *args, **kwargs):
        super(WorkboxItemModel, self).__init__(*args, **kwargs)
        self.manager = manager

    def pathFromIndex(self, index):
        parts = [""]
        while index.isValid():
            parts.append(self.data(index, Qt.DisplayRole))
            index = index.parent()
        if len(parts) == 1:
            return ""
        return "/".join([x for x in parts[::-1] if x])


class WorkboxTreeItemModel(WorkboxItemModel):
    def process(self):
        root = self.invisibleRootItem()
        prev_group = -1
        for _, group_name, tab_name, group_index, _ in self.manager.all_widgets():
            if prev_group != group_index:
                group_item = QStandardItem(group_name)
                root.appendRow(group_item)
                prev_group = group_index

            tab_item = QStandardItem(tab_name)
            group_item.appendRow(tab_item)


class WorkboxListItemModel(WorkboxItemModel):
    def process(self):
        root = self.invisibleRootItem()
        for _, group_name, tab_name, _, _ in self.manager.all_widgets():
            group_item = QStandardItem('/'.join((group_name, tab_name)))
            root.appendRow(group_item)


class WorkboxFuzzyFilterProxyModel(QSortFilterProxyModel):
    """Implements a fuzzy search filter proxy model."""

    def __init__(self, parent=None):
        super(WorkboxFuzzyFilterProxyModel, self).__init__(parent=parent)
        self._fuzzy_regex = None

    def setFuzzySearch(self, search):
        search = '.*'.join(search)
        # search = '.*{}.*'.format(search)
        self._fuzzy_regex = re.compile(search, re.I)
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        if self.filterKeyColumn() == 0 and self._fuzzy_regex:

            index = self.sourceModel().index(sourceRow, 0, sourceParent)
            data = self.sourceModel().data(index)
            ret = bool(self._fuzzy_regex.search(data))
            return ret

        return super(WorkboxFuzzyFilterProxyModel, self).filterAcceptsRow(
            sourceRow, sourceParent
        )

    def pathFromIndex(self, index):
        parts = [""]
        while index.isValid():
            parts.append(self.data(index, Qt.DisplayRole))
            index = index.parent()
        if len(parts) == 1:
            return ""
        return "/".join([x for x in parts[::-1] if x])
