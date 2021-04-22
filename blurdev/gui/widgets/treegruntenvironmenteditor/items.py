from __future__ import print_function
from __future__ import absolute_import
import os
import cute
from Qt.QtCore import Qt
from Qt.QtWidgets import QTreeWidgetItem
from ... import iconFactory
from ....tools.toolsenvironment import ToolsEnvironment
from .columns import Columns


class EnvironmentTreeWidgetItem(QTreeWidgetItem):
    """QTreeWidgetItem for viewing and editing a individual treegrunt environment."""

    def __init__(self, parent, environment, **kwargs):
        super(EnvironmentTreeWidgetItem, self).__init__(parent, **kwargs)
        for column in Columns:
            value = environment.get(column.label)
            if column.typ is bool:
                state = cute.functions.bool_to_check_state(value)
                self.setCheckState(column, state)
            else:
                self.setData(column, Qt.EditRole, value)

        self.read_only = parent.read_only
        if self.read_only:
            self.setIcon(0, parent.icon(0))
        else:
            self.setFlags(self.flags() | Qt.ItemIsEditable)

        self.check_valid()

    def check_valid(self):
        """Highlight any issues with the current state of the environment"""
        path = self.data(Columns.Path, Qt.EditRole)
        if path:
            self.valid = os.path.exists(path)
        else:
            self.valid = False

    @property
    def env_index(self):
        return self.parent().indexOfChild(self)

    @property
    def filename(self):
        return self.parent().filename

    def setConfigValue(self, config, column, value):
        """Update the provided config and this item's display of the data"""
        config[self.filename]['environments'][self.env_index][column.label] = value
        # Update the current item and its valid status
        self.setData(column, Qt.EditRole, value)
        self.check_valid()
        # For now, save the config when a user edits the data.
        # TODO: Implement a proper saving system(undo/redo?) with dirty detection
        ToolsEnvironment.save_config(config)

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, value):
        self._valid = value
        if self.valid:
            self.setBackground(Columns.Path, Qt.transparent)
        else:
            self.setBackground(Columns.Path, Qt.red)


class FileTreeWidgetItem(QTreeWidgetItem):
    """QTreeWidgetItem for viewing and editing a treegrunt config json file."""

    def __init__(self, parent, config, filename, **kwargs):
        super(FileTreeWidgetItem, self).__init__(parent, **kwargs)
        self.filename = filename
        self.name = config.get('name', '')
        self.read_only = config.get('read_only', False)

        self.setText(Columns.Name, self.name)
        self.setText(Columns.Path, filename)

        if self.read_only:
            self.setIcon(0, iconFactory.getIcon("lock"))

    def setConfigValue(self, config, column, value):
        if column == Columns.Name:
            config[self.filename]['name'] = value
        elif column == Columns.Path:
            data = config.pop(self.filename)
            config[value]['filename'] = data
