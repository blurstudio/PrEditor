from __future__ import print_function
from __future__ import absolute_import
import os
import blurdev
import shutil
from .columns import Columns
from .items import EnvironmentTreeWidgetItem, FileTreeWidgetItem
from ..blurtreewidget import BlurTreeWidget
from ..filepickerwidget import FilePickerWidget
from ...dialogs.createenvironmentdialog import CreateEnvironmentDialog
from ....tools.toolsenvironment import ToolsEnvironment
from collections import OrderedDict
from pillar.live_subprocess import LiveSubprocess
from pillar.virtualenv_helper import VirtualenvHelper
from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTreeWidgetItem,
    QWidget,
)


class TreegruntEnvironmentEditor(QWidget):
    def __init__(self, parent=None, filename=None):
        super(TreegruntEnvironmentEditor, self).__init__(parent=parent)
        self.setMinimumSize(1024, 600)

        self.uiMainTREE = BlurTreeWidget(self)
        self.config = OrderedDict()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.uiMainTREE)

        self.uiMainTREE.enableGridDelegate(True)
        self.uiMainTREE.setDelegate(self)

        self.uiMainTREE.setHeaderLabels(list(Columns.names()))
        self.uiMainTREE.setAlternatingRowColors(True)
        self.uiMainTREE.setShowColumnControls(True)
        self.uiMainTREE.setUserCanHideColumns(True)
        self.uiMainTREE.setHideableColumns([1 if c.can_hide else 0 for c in Columns])
        self.uiMainTREE.restoreColumnVisibility(
            {c.name: c.visible for c in Columns if not c.visible}
        )

        self.uiMainTREE.setContextMenuPolicy(Qt.CustomContextMenu)
        self.uiMainTREE.customContextMenuRequested.connect(self.showMenu)

        self.load(filename)

    def createEditor(self, parent, option, index, tree=None):
        column = Columns[index.column()]
        if column.typ == bool:
            # TODO: Enable editing of the check boxes
            return None
        elif column == Columns.Path:
            editor = FilePickerWidget(parent)

            # Setting editor preferences.
            editor.setOpenFile(True)
            editor.setPickFolder(True)
            editor.setResolvePath(True)
            editor.setCaption('Pick repository root directory(site-packages)')
            item = tree.itemFromIndex(index)
            text = item.text(column)
            editor.setFilePath(text)
            return editor

        return QLineEdit(parent)

    def createEnvironment(self):
        selected = self.uiMainTREE.currentItem()
        if not isinstance(selected, FileTreeWidgetItem):
            return

        dlg = CreateEnvironmentDialog(
            config=self.config, filename=selected.filename, parent=self
        )

        if not dlg.exec_():
            return

        # Show the newly created treegrunt environment.
        self.refresh()

    def explore(self):
        """Open the file explorer to the selected path"""
        selected = self.uiMainTREE.currentItem()
        name = selected.text(Columns.Path)
        blurdev.osystem.explore(name, dirFallback=True)

    def load(self, filename=None):
        """Load the configuration file and its included files.

        Args:
            filename (str, optional): The file path to load, if not provided, uses
                :py:meth`blurdev.core.defaultEnvironmentPath`.
        """
        if filename is None:
            filename = blurdev.core.defaultEnvironmentPath()

        self.config = ToolsEnvironment.load_config_file(filename)
        self.refresh()

    def open_file(self):
        """Open the selected file with the default application"""
        selected = self.uiMainTREE.currentItem()
        name = selected.text(Columns.Path)
        os.startfile(name)

    def open_python_environment_manager(self):
        """Open the Python Environment Manager tool to manage the environment's
        configuration.
        """
        from updatedevrepo.updatedevrepo import UpdateDevRepoWindow

        selected = self.uiMainTREE.currentItem()
        name = selected.text(Columns.Name)

        update_dev_repo = UpdateDevRepoWindow(self)
        update_dev_repo.show()

        index = update_dev_repo.uiEnvironmentDDL.findText(name)
        if update_dev_repo.uiEnvironmentDDL.currentIndex() != index:
            update_dev_repo.uiEnvironmentDDL.setCurrentIndex(index)

    def rebuild_index(self):
        """Rebuild the treegrunt index of the selected item."""
        selected = self.uiMainTREE.currentItem()
        name = selected.text(Columns.Name)
        env = ToolsEnvironment.findEnvironment(name)

        if env.isEmpty():
            QMessageBox.critical(
                self,
                "Missing treegrunt environment",
                'Unable to find the treegrunt environment "{}"'.format(name),
            )
            return

        # Rebuild the selected index, using a subprocess prevents needing to switch
        # treegrunt environments in the current program.
        proc = LiveSubprocess(["blurdev", "env", "rebuild", '--name', name])
        proc.wait()
        if proc.returncode:
            QMessageBox.critical(
                self,
                "Error rebuilding index",
                "There was a error rebuilding the index:\n\n{}".format(proc.output),
            )

    def refresh(self):
        self.uiMainTREE.clear()
        for filename, config in self.config.items():
            parent = FileTreeWidgetItem(self.uiMainTREE, config, filename)

            if 'included' in config:
                include_root = QTreeWidgetItem(parent, ['Included'])
                for include in config.get('included', []):
                    include_item = QTreeWidgetItem(
                        include_root,
                        [include.get('name')],
                    )
                    include_item.setText(Columns.Path, include.get('filename'))

            for environment in config.get('environments', []):
                EnvironmentTreeWidgetItem(parent, environment)

        self.uiMainTREE.expandToDepth(1)
        self.uiMainTREE.resizeColumnsToContents()

    def remove_environment(self):
        selected = self.uiMainTREE.currentItem()
        if not isinstance(selected, EnvironmentTreeWidgetItem):
            return

        env_name = selected.text(Columns.Name)
        path = selected.text(Columns.Path)
        path = VirtualenvHelper.root_from_lib(path)

        message_box = QMessageBox(self)
        message_box.setWindowTitle('Remove Environment?')
        if path and os.path.exists(path):
            message_box.addButton('From Disk', QMessageBox.YesRole)
            msg = (
                'Do you want to remove the environment "{name}" from disk or just '
                'from treegrunt? '
            )
        else:
            msg = (
                'Do you want to remove the environment "{name}" from treegrunt?'
                '<br>The path was not found, it will not be removed from disk.'
            )
        if path:
            msg += '<br>Path: <a href="{path}">{path}</a>?'
        msg += '<br>This is not undo-able.'
        message_box.setText(msg.format(name=env_name, path=path))
        message_box.addButton('Treegrunt', QMessageBox.NoRole)
        message_box.addButton('Cancel', QMessageBox.RejectRole)
        message_box.exec_()
        ret = message_box.clickedButton().text()

        if ret == 'Cancel':
            return
        if ret == 'From Disk':
            if os.path.exists(path):
                shutil.rmtree(path)

        del self.config[selected.filename]['environments'][selected.env_index]
        ToolsEnvironment.save_config(self.config)

        self.refresh()

    def setModelData(self, editor, model, index, tree=None):
        column = Columns[index.column()]
        item = tree.itemFromIndex(index)

        if isinstance(editor, FilePickerWidget):
            value = editor.filePath()
        else:
            value = editor.text()

        item.setConfigValue(self.config, column, value)

    def showMenu(self, pos):
        item = self.uiMainTREE.itemAt(pos)
        menu = QMenu(self.uiMainTREE)
        is_env = isinstance(item, EnvironmentTreeWidgetItem)
        is_file = isinstance(item, FileTreeWidgetItem)

        if is_file:
            menu.addAction('Open').triggered.connect(self.open_file)

        if is_env or is_file:
            menu.addAction('Explore').triggered.connect(self.explore)
            menu.addSeparator()

        if is_file:
            if not item.read_only:
                menu.addAction('Create Environment').triggered.connect(
                    self.createEnvironment
                )
        elif is_env:
            menu.addSeparator()
            menu.addAction('Rebuild Index').triggered.connect(self.rebuild_index)
            menu.addAction('Open Python Environment Manager').triggered.connect(
                self.open_python_environment_manager
            )
            if not item.read_only:
                menu.addSeparator()
                menu.addAction('Remove Environment').triggered.connect(
                    self.remove_environment
                )

        menu.addSeparator()
        menu.addAction('Refresh').triggered.connect(self.refresh)
        menu.exec_(self.uiMainTREE.mapToGlobal(pos))

    @classmethod
    def edit(cls, filename=None, parent=None, connect_logger=True):
        """A dialog for editing treegrunt environments.

        Args:
            filename (str, optional): The file path to load, if not provided, uses
                :py:meth`blurdev.core.defaultEnvironmentPath`.
            parent (QWidget, optional): Parent for the dialog.
            connect_logger (bool, optional): Connect the python logger to this dialog.

        Returns:
            bool:
        """
        dlg = blurdev.gui.Dialog(parent=parent)

        dlg.setWindowTitle("Treegrunt Environment Editor")
        dlg.setWindowIcon(QIcon(blurdev.resourcePath('img/treegrunt.png')))
        dlg.uiEditorWGT = cls(dlg, filename)
        if connect_logger:
            # TreegruntDialog doesn't connect the logger by default, so we can't
            # connect it here as it would cause the logger to be closed with dlg.
            blurdev.gui.connectLogger(dlg)

        dlg.uiInfoLBL = QLabel(
            "Note: Edits made with this dialog are committed right away. The check "
            "boxes don't work at the moment.",
            dlg,
        )

        lyt = QVBoxLayout(dlg)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.addWidget(dlg.uiEditorWGT)
        lyt.addWidget(dlg.uiInfoLBL)

        if dlg.exec_():
            return True
        return False
