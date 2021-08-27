##
# 	\namespace	[FILENAME]
#
# 	\remarks	[ADD REMARKS]
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/02/10
#

from __future__ import absolute_import
import os

from blurdev.gui import Dialog
from blurdev.ide.ideproject import IdeProjectItem

from blurdev import osystem
from Qt import QtCompat


class IdeProjectDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self._project = None

        self.uiProjectNameTXT.textChanged.connect(self.updateProjectName)
        self.uiProjectTREE.customContextMenuRequested.connect(self.showMenu)

    def accept(self):
        import os.path

        path = str(self.uiProjectPATH.filePath())
        name = str(self.uiProjectNameTXT.text())

        filename = os.path.join(path, name + '.blurproj')

        # check to see if we are saving to a new location
        if os.path.normcase(self._project.filename()) != os.path.normcase(filename):
            if not os.path.exists(path):
                from Qt.QtWidgets import QMessageBox

                QMessageBox.critical(
                    None,
                    'Invalid Project Path',
                    (
                        'Please specify a valid path for your project. '
                        'Cannot create the project at: %s'
                    )
                    % path,
                )
                return False

            if os.path.exists(filename):
                from Qt.QtWidgets import QMessageBox

                results = QMessageBox.question(
                    None,
                    'Project Already Exists',
                    (
                        'The project you are trying to create already exists. '
                        'Do you want to overwrite?'
                    ),
                    (QMessageBox.Yes | QMessageBox.No),
                )
                if results == QMessageBox.No:
                    return False

            self._project.setFilename(filename)

        if self._project.save():
            Dialog.accept(self)

    def addItem(self):
        from .ideprojectitemdialog import IdeProjectItemDialog
        from .ideproject import IdeProjectItem

        # pull the parent from the tree
        item = self.uiProjectTREE.currentItem()
        if not item:
            item = self._project

        child = IdeProjectItem()
        if IdeProjectItemDialog.edit(child):
            item.addChild(child)

    def addFile(self):
        filename, _ = QtCompat.QFileDialog.getOpenFileName(
            self, 'Select File', '', 'All Files (*.*)'
        )

        if filename:
            # pull the parent from the tree
            item = self.uiProjectTREE.currentItem()
            if not item:
                item = self._project

            child = IdeProjectItem.createFileItem(str(filename))
            child.setFileSystem(False)
            item.addChild(child)

    def editItem(self):
        from .ideprojectitemdialog import IdeProjectItemDialog

        # pull the item from the tree
        item = self.uiProjectTREE.currentItem()
        if item:
            IdeProjectItemDialog.edit(item)

    def filename(self):
        import os.path

        path = str(self.uiProjectPATH.filePath())
        name = str(self.uiProjectNameTXT.text())

        return os.path.join(path, name + '.blurproj')

    def project(self):
        return self._project

    def removeItem(self):
        item = self.uiProjectTREE.currentItem()
        if item.parent():
            item.parent().takeChild(item.parent().indexOfChild(item))

    def setProject(self, project):
        if not project:
            from .ideproject import IdeProject

            project = IdeProject()
            self.uiProjectPATH.setFilePath(
                osystem.expandvars(os.environ.get('BDEV_PATH_PROJECT', ''))
            )
            self.uiProjectPATH.setEnabled(True)
            self.uiProjectNameTXT.setText('')
            self.uiProjectNameTXT.setEnabled(True)
        else:
            import os.path

            self.uiProjectPATH.setFilePath(os.path.split(project.filename())[0])
            self.uiProjectPATH.setEnabled(False)
            self.uiProjectNameTXT.setText(project.text(0))
            self.uiProjectNameTXT.setEnabled(False)

        self._project = project
        self.uiProjectTREE.clear()
        self.uiProjectTREE.addTopLevelItem(self._project)

    def showMenu(self):
        from Qt.QtGui import QCursor
        from Qt.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction('Add Folder...').triggered.connect(self.addItem)
        menu.addAction('Edit Folder...').triggered.connect(self.editItem)
        menu.addAction('Add File...').triggered.connect(self.addFile)
        menu.addSeparator()
        menu.addAction('Remove Item').triggered.connect(self.removeItem)

        menu.popup(QCursor.pos())

    def updateProjectName(self):
        if self._project:
            self._project.setText(0, self.uiProjectNameTXT.text())

    @staticmethod
    def createNew():
        import blurdev

        dlg = IdeProjectDialog(blurdev.core.activeWindow())
        dlg.setProject(None)
        if dlg.exec_():
            from .ideproject import IdeProject

            return IdeProject.fromXml(dlg.filename())
        return None

    @staticmethod
    def edit(filename):
        import blurdev
        from .ideproject import IdeProject

        dlg = IdeProjectDialog(blurdev.core.activeWindow())
        dlg.setProject(IdeProject.fromXml(filename))
        if dlg.exec_():
            return True
        return False
