from __future__ import absolute_import

import re

from Qt.QtCore import QSortFilterProxyModel, Qt
from Qt.QtGui import QStandardItem, QStandardItemModel


class GroupTabItemModel(QStandardItemModel):
    GroupIndexRole = Qt.UserRole + 1
    TabIndexRole = GroupIndexRole + 1

    def __init__(self, manager, *args, **kwargs):
        super(GroupTabItemModel, self).__init__(*args, **kwargs)
        self.manager = manager

    def workbox_indexes_from_model_index(self, index):
        """Returns the group_index and tab_index for the provided QModelIndex"""
        return (
            index.data(self.GroupIndexRole),
            index.data(self.TabIndexRole),
        )

    def pathFromIndex(self, index):
        parts = [""]
        while index.isValid():
            parts.append(self.data(index, Qt.DisplayRole))
            index = index.parent()
        if len(parts) == 1:
            return ""
        return "/".join([x for x in parts[::-1] if x])


class GroupTabTreeItemModel(GroupTabItemModel):
    def process(self):
        root = self.invisibleRootItem()
        current_group = self.manager.currentIndex()
        current_tab = self.manager.currentWidget().currentIndex()

        prev_group = -1
        all_widgets = self.manager.all_widgets()
        for _, group_name, tab_name, group_index, tab_index in all_widgets:
            if prev_group != group_index:
                group_item = QStandardItem(group_name)
                group_item.setData(group_index, self.GroupIndexRole)
                root.appendRow(group_item)
                prev_group = group_index

            tab_item = QStandardItem(tab_name)
            tab_item.setData(group_index, self.GroupIndexRole)
            tab_item.setData(tab_index, self.TabIndexRole)
            group_item.appendRow(tab_item)
            if group_index == current_group and tab_index == current_tab:
                self.original_model_index = self.indexFromItem(tab_item)


class GroupTabListItemModel(GroupTabItemModel):
    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def process(self):
        root = self.invisibleRootItem()
        current_group = self.manager.currentIndex()
        current_tab = self.manager.currentWidget().currentIndex()

        all_widgets = self.manager.all_widgets()
        for _, group_name, tab_name, group_index, tab_index in all_widgets:
            tab_item = QStandardItem('/'.join((group_name, tab_name)))
            tab_item.setData(group_index, self.GroupIndexRole)
            tab_item.setData(tab_index, self.TabIndexRole)
            root.appendRow(tab_item)
            if group_index == current_group and tab_index == current_tab:
                self.original_model_index = self.indexFromItem(tab_item)


class GroupTabFuzzyFilterProxyModel(QSortFilterProxyModel):
    """Implements a fuzzy search filter proxy model."""

    def __init__(self, parent=None):
        super(GroupTabFuzzyFilterProxyModel, self).__init__(parent=parent)
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

        return super(GroupTabFuzzyFilterProxyModel, self).filterAcceptsRow(
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
