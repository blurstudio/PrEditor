##
# 	\namespace	[FILENAME]
#
# 	\remarks	[ADD REMARKS]
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/02/10
#

from blurdev.gui import Dialog


class IdeProjectDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self._project = None

        self.uiProjectTREE.customContextMenuRequested.connect(self.showMenu)

    def accept(self):
        if self._project.isNull():
            path = str(self.uiProjectPATH.filePath())
            name = str(self.uiProjectNameTXT.text())

            import os.path

            if not os.path.exists(path):
                from PyQt4.QtGui import QMessageBox

                QMessageBox.critical(
                    None,
                    'Invalid Project Path',
                    'Please specify a valid path for your project.  Cannot create the project at: %s'
                    % path,
                )
                return False

            filename = os.path.join(path, name + '.blurproj')
            if os.path.exists(filename):
                from PyQt4.QtGui import QMessageBox

                results = QMessageBox.question(
                    None,
                    'Project Already Exists',
                    'The project you are trying to create already exists.  Do you want to overwrite?',
                    (QMessageBox.Yes | QMessageBox.No),
                )
                if results == QMessageBox.No:
                    return False

            self._project.setFilename(filename)

        if self._project.save():
            Dialog.accept(self)

    def addRootItem(self):
        from ideprojectitemdialog import IdeProjectItemDialog
        from ideproject import IdeProjectItem

        # pull the parent from the tree
        model = self.uiProjectTREE.model()
        item = IdeProjectItem(self._project)
        if IdeProjectItemDialog.edit(item):
            model.reset()
        else:
            item.setParent(None)
            item.deleteLater()

    def addItem(self):
        from ideprojectitemdialog import IdeProjectItemDialog
        from ideproject import IdeProjectItem

        # pull the parent from the tree
        model = self.uiProjectTREE.model()
        parent = model.object(self.uiProjectTREE.currentIndex())

        if not parent:
            parent = self._project

        item = IdeProjectItem(parent)
        if IdeProjectItemDialog.edit(item):
            model.reset()
        else:
            item.setParent(None)
            item.deleteLater()

    def editItem(self):
        from ideprojectitemdialog import IdeProjectItemDialog
        from ideproject import IdeProjectItem

        # pull the item from the tree
        model = self.uiProjectTREE.model()
        object = model.object(self.uiProjectTREE.currentIndex())

        if object and IdeProjectItemDialog.edit(object):
            model.reset()

    def project(self):
        return self._project

    def removeItem(self):
        model = self.uiProjectTREE.model()
        object = model.object(self.uiProjectTREE.currentIndex())
        if object:
            object.setParent(None)
            object.deleteLater()
            model.reset()

    def setProject(self, project):
        self._project = project
        if project.isNull():
            from ideproject import IdeProject

            self.uiProjectPATH.setFilePath(IdeProject.DefaultPath)
            self.uiProjectPATH.setEnabled(True)
            self.uiProjectNameTXT.setText('')
            self.uiProjectNameTXT.setEnabled(True)
        else:
            import os.path

            self.uiProjectPATH.setFilePath(os.path.split(project.filename())[0])
            self.uiProjectPATH.setEnabled(False)
            self.uiProjectNameTXT.setText(project.objectName())
            self.uiProjectNameTXT.setEnabled(False)

        from ideprojectmodel import IdeProjectModel

        model = IdeProjectModel(project)
        self.uiProjectTREE.setModel(model)

    def showMenu(self):
        from PyQt4.QtGui import QMenu, QCursor

        menu = QMenu(self)
        menu.addAction('Add Root Item...').triggered.connect(self.addRootItem)
        menu.addAction('Add Item...').triggered.connect(self.addItem)
        menu.addAction('Edit Item...').triggered.connect(self.editItem)
        menu.addSeparator()
        menu.addAction('Remove Item').triggered.connect(self.removeItem)

        menu.popup(QCursor.pos())

    @staticmethod
    def edit(project):
        import blurdev

        dlg = IdeProjectDialog(blurdev.core.activeWindow())
        dlg.setProject(project)
        if dlg.exec_():
            return True
        return False
