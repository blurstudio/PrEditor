##
# 	\namespace	linux-2011-07-19.ide.config.project.[module]
#
# 	\remarks	Modify the overall project settings
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		07/20/11
#

from __future__ import absolute_import
import os
import blurdev
from blurdev import osystem

from Qt.QtGui import QCursor, QIcon
from Qt.QtWidgets import QMenu, QMessageBox, QTreeWidgetItem
from Qt import QtCompat
from blurdev.gui.dialogs.configdialog import ConfigSectionWidget
from blurdev.ide.ideprojectitemdialog import IdeProjectItemDialog
from blurdev.ide.ideproject import IdeProjectItem, IdeProject


class SettingsConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # set up icons for commands
        self.uiInsertArgumentSeparatorBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/separator.png'))
        )
        self.uiAddArgumentBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/add.png')))
        self.uiRemoveArgumentBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/remove.png'))
        )
        self.uiMoveArgumentUpBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/arrow_up.png'))
        )
        self.uiMoveArgumentDownBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/arrow_down.png'))
        )

        self.uiInsertCommandSeparatorBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/separator.png'))
        )
        self.uiAddCommandBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/add.png')))
        self.uiRemoveBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/remove.png')))
        self.uiMoveUpBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/arrow_up.png')))
        self.uiMoveDownBTN.setIcon(
            QIcon(blurdev.resourcePath('img/ide/arrow_down.png'))
        )

        # initialize the project data
        project = self.configData('project')

        if not (project and project.exists()):
            project = IdeProject()

            # update the interface to reflect the current project
            self.uiProjectPATH.setFilePath(osystem.expandvars('$BDEV_PATH_PROJECT'))
            self.uiProjectNameTXT.setText('')
            self.uiProjectPATH.setEnabled(True)
            self.uiProjectNameTXT.setEnabled(True)
        else:
            project = IdeProject.fromXml(project.filename())

            # update the interface to reflect the current project
            self.uiProjectPATH.setFilePath(os.path.split(project.filename())[0])
            self.uiProjectNameTXT.setText(project.text(0))
            self.uiProjectPATH.setEnabled(False)
            self.uiProjectNameTXT.setEnabled(False)

        self._project = project
        self.uiProjectTREE.clear()
        self.uiProjectTREE.addTopLevelItem(self._project)
        self._currentArgumentName = None
        self._currentCommandName = None
        self.refreshArgumentList()
        self.refreshCommandList()

        # create connections
        self.uiProjectNameTXT.textChanged.connect(self.updateProjectName)
        self.uiProjectTREE.customContextMenuRequested.connect(self.showMenu)

    def addProjectArgument(self):
        from Qt.QtWidgets import QInputDialog

        name = QInputDialog.getText(
            self,
            'Name of argument',
            'What do you want to call this argument?',
            text='New Argument',
        )
        if name[1]:
            argList = self._project.argumentList()
            argList.update({name[0]: (len(argList), '')})
            self.refreshArgumentList()

    def addProjectCommand(self):
        from Qt.QtWidgets import QInputDialog

        name = QInputDialog.getText(
            self,
            'Name of command',
            'What do you want to call this command?',
            text='New Command',
        )
        if name[1]:
            cmdList = self._project.commandList()
            cmdList.update({name[0]: (len(cmdList), '')})
            self.refreshCommandList()

    def addItem(self):
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
        # pull the item from the tree
        item = self.uiProjectTREE.currentItem()
        if item:
            IdeProjectItemDialog.edit(item)

    def editProjectArgument(self):
        item = self.uiArgumentTREE.currentItem()
        if item:
            name = item.text(0)
            argList = self._project.argumentList()
            if name in argList:
                self.uiArgumentNameTXT.setText(name)
                self.uiArgumentCmdTXT.setText(argList[name][1])
                self._currentArgumentName = name
                self.uiArgumentUpdateBTN.setEnabled(True)
            else:
                self._currentArgumentName = None
        else:
            self.uiArgumentCmdTXT.setText('')
            self.uiArgumentNameTXT.setText('')
            self.uiArgumentUpdateBTN.setEnabled(False)

    def editProjectCommand(self):
        item = self.uiCommandTREE.currentItem()
        if item:
            name = item.text(0)
            cmdList = self._project.commandList()
            if name in cmdList:
                self.uiCommandNameTXT.setText(name)
                self.uiCommandCmdTXT.setText(cmdList[name][1])
                self._currentCommandName = name
                self.uiCommandUpdateBTN.setEnabled(True)
            else:
                self._currentCommandName = None
        else:
            self.uiCommandCmdTXT.setText('')
            self.uiCommandNameTXT.setText('')
            self.uiCommandUpdateBTN.setEnabled(False)

    def filename(self):
        path = str(self.uiProjectPATH.filename())
        name = str(self.uiProjectNameTXT.text())

        return os.path.join(path, name + '.blurproj')

    def insertArgumentSeparator(self):
        argList = self._project.argumentList()
        sep = "!Separator!%i"
        i = 0
        while sep % i in argList:
            i += 1
        argList.update({sep % i: (len(argList), '')})
        self.refreshArgumentList()

    def insertCommandSeparator(self):
        cmdList = self._project.commandList()
        sep = "!Separator!%i"
        i = 0
        while sep % i in cmdList:
            i += 1
        cmdList.update({sep % i: (len(cmdList), '')})
        self.refreshCommandList()

    def moveProjectArgumentDown(self):
        index = self.uiArgumentTREE.indexFromItem(
            self.uiArgumentTREE.currentItem()
        ).row()
        index += 1
        if index < self.uiArgumentTREE.topLevelItemCount():
            item = self.uiArgumentTREE.takeTopLevelItem(index - 1)
            self.uiArgumentTREE.insertTopLevelItem(index, item)
            self.uiArgumentTREE.setCurrentItem(item)

    def moveProjectCommandDown(self):
        index = self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        index += 1
        if index < self.uiCommandTREE.topLevelItemCount():
            item = self.uiCommandTREE.takeTopLevelItem(index - 1)
            self.uiCommandTREE.insertTopLevelItem(index, item)
            self.uiCommandTREE.setCurrentItem(item)

    def moveProjectArgumentUp(self):
        index = self.uiArgumentTREE.indexFromItem(
            self.uiArgumentTREE.currentItem()
        ).row()
        index -= 1
        if index >= 0:
            item = self.uiArgumentTREE.takeTopLevelItem(index + 1)
            self.uiArgumentTREE.insertTopLevelItem(index, item)
            self.uiArgumentTREE.setCurrentItem(item)

    def moveProjectCommandUp(self):
        index = self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        index -= 1
        if index >= 0:
            item = self.uiCommandTREE.takeTopLevelItem(index + 1)
            self.uiCommandTREE.insertTopLevelItem(index, item)
            self.uiCommandTREE.setCurrentItem(item)

    def recordUi(self):
        """records the latest ui settings to the data"""
        path = str(self.uiProjectPATH.filePath())
        name = str(self.uiProjectNameTXT.text())

        filename = os.path.join(path, name + '.blurproj')

        # check to see if we are saving to a new location
        if os.path.normcase(self._project.filename()) != os.path.normcase(filename):
            if not os.path.exists(path):
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

        # get the changes to the argumentList
        argList = {}
        for index in range(self.uiArgumentTREE.topLevelItemCount()):
            item = self.uiArgumentTREE.topLevelItem(index)
            argList.update({item.text(0): [index, item.text(1)]})
        self._project.setArgumentList(argList)

        # get the changes to the commandList
        cmdList = {}
        for index in range(self.uiCommandTREE.topLevelItemCount()):
            item = self.uiCommandTREE.topLevelItem(index)
            cmdList.update({item.text(0): [index, item.text(1)]})
        self._project.setCommandList(cmdList)

        # record this project as the saved project
        self.setConfigData('saved_project', self._project)

        # save the project settings
        self._project.setConfigSet(self.configSet())
        self._project.save()

    def refreshArgumentList(self):
        self.uiArgumentTREE.clear()
        argList = self._project.argumentList()
        for key in sorted(argList.keys(), key=lambda i: argList[i][0]):
            item = QTreeWidgetItem([key, argList[key][1]])
            self.uiArgumentTREE.addTopLevelItem(item)

    def refreshCommandList(self):
        self.uiCommandTREE.clear()
        cmdList = self._project.commandList()
        for key in sorted(cmdList.keys(), key=lambda i: cmdList[i][0]):
            item = QTreeWidgetItem()
            item.setText(0, key)
            item.setText(1, cmdList[key][1])
            self.uiCommandTREE.addTopLevelItem(item)

    def removeItem(self):
        item = self.uiProjectTREE.currentItem()
        if item.parent():
            item.parent().takeChild(item.parent().indexOfChild(item))

    def removeProjectArgument(self):
        self.uiArgumentTREE.takeTopLevelItem(
            self.uiArgumentTREE.indexFromItem(self.uiArgumentTREE.currentItem()).row()
        )

    def removeProjectCommand(self):
        self.uiCommandTREE.takeTopLevelItem(
            self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        )

    def saveProjectArgument(self):
        key = self._currentArgumentName
        argList = self._project.argumentList()
        if key and key in argList:
            data = argList.pop(key)
            argList.update(
                {self.uiArgumentNameTXT.text(): [data[0], self.uiArgumentCmdTXT.text()]}
            )
        self.refreshArgumentList()

    def saveProjectCommand(self):
        key = self._currentCommandName
        cmdList = self._project.commandList()
        if key and key in cmdList:
            data = cmdList.pop(key)
            cmdList.update(
                {self.uiCommandNameTXT.text(): [data[0], self.uiCommandCmdTXT.text()]}
            )
        self.refreshCommandList()

    def showMenu(self):
        menu = QMenu(self)
        menu.addAction('Add Folder...').triggered.connect(self.addItem)
        menu.addAction('Edit Folder...').triggered.connect(self.editItem)
        menu.addAction('Add File...').triggered.connect(self.addFile)
        menu.addSeparator()
        menu.addAction('Remove Item').triggered.connect(self.removeItem)

        menu.popup(QCursor.pos())

    def updateProjectName(self):
        proj = self._project
        if proj:
            proj.setText(0, self.uiProjectNameTXT.text())


def registerSections(configSet):
    """registers one or many new sections to the config system

    Args:
        configSet (blurdev.gui.dialogs.configdialog.ConfigSet):
    """

    # define section
    group = 'Project'
    section = 'Settings'
    icon = blurdev.relativePath(__file__, 'img/settingsconfig.png')
    cls = SettingsConfig
    params = {}

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
