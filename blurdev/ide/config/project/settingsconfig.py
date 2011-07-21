##
# 	\namespace	linux-2011-07-19.ide.config.project.[module]
#
# 	\remarks	Modify the overall project settings
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		07/20/11
#

import os
import blurdev
from blurdev import osystem

from PyQt4.QtGui import QMessageBox, QFileDialog, QMenu, QCursor, QIcon, QTreeWidgetItem
from blurdev.gui.dialogs.configdialog import ConfigSectionWidget
from blurdev.ide.ideprojectitemdialog import IdeProjectItemDialog
from blurdev.ide.ideproject import IdeProjectItem, IdeProject


class SettingsConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # set up icons for commands
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
        self._currentCommandName = None
        self.refreshCommandList()

        # create connections
        self.uiProjectNameTXT.textChanged.connect(self.updateProjectName)
        self.uiProjectTREE.customContextMenuRequested.connect(self.showMenu)

    def addProjectCommand(self):
        from PyQt4.QtGui import QInputDialog

        name = QInputDialog.getText(
            self,
            'Name of command',
            'What do you want to call this command?',
            text='New Command',
        )
        if name[1]:
            cmdList = self._project.commandList()
            cmdList.update({unicode(name[0]): (len(cmdList), '')})
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
        filename = QFileDialog.getOpenFileName(
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

    def editProjectCommand(self):
        item = self.uiCommandTREE.currentItem()
        if item:
            name = unicode(item.text(0))
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

    def moveProjectCommandDown(self):
        index = self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        index += 1
        if index < self.uiCommandTREE.topLevelItemCount():
            item = self.uiCommandTREE.takeTopLevelItem(index - 1)
            self.uiCommandTREE.insertTopLevelItem(index, item)
            self.uiCommandTREE.setCurrentItem(item)

    def moveProjectCommandUp(self):
        index = self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        index -= 1
        if index >= 0:
            item = self.uiCommandTREE.takeTopLevelItem(index + 1)
            self.uiCommandTREE.insertTopLevelItem(index, item)
            self.uiCommandTREE.setCurrentItem(item)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        path = str(self.uiProjectPATH.filePath())
        name = str(self.uiProjectNameTXT.text())

        filename = os.path.join(path, name + '.blurproj')

        # check to see if we are saving to a new location
        if os.path.normcase(self._project.filename()) != os.path.normcase(filename):
            if not os.path.exists(path):
                QMessageBox.critical(
                    None,
                    'Invalid Project Path',
                    'Please specify a valid path for your project.  Cannot create the project at: %s'
                    % path,
                )
                return False

            if os.path.exists(filename):
                results = QMessageBox.question(
                    None,
                    'Project Already Exists',
                    'The project you are trying to create already exists.  Do you want to overwrite?',
                    (QMessageBox.Yes | QMessageBox.No),
                )
                if results == QMessageBox.No:
                    return False

            self._project.setFilename(filename)

        # get the changes to the commandList
        cmdList = {}
        for index in range(self.uiCommandTREE.topLevelItemCount()):
            item = self.uiCommandTREE.topLevelItem(index)
            cmdList.update({unicode(item.text(0)): [index, unicode(item.text(1))]})
        self._project.setCommandList(cmdList)

        # record this project as the saved project
        self.setConfigData('saved_project', self._project)

        # save the project settings
        self._project.setConfigSet(self.configSet())
        self._project.save()

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

    def removeProjectCommand(self):
        self.uiCommandTREE.takeTopLevelItem(
            self.uiCommandTREE.indexFromItem(self.uiCommandTREE.currentItem()).row()
        )

    def saveProjectCommand(self):
        key = self._currentCommandName
        cmdList = self._project.commandList()
        if key and key in cmdList:
            data = cmdList.pop(key)
            cmdList.update(
                {
                    unicode(self.uiCommandNameTXT.text()): [
                        data[0],
                        unicode(self.uiCommandCmdTXT.text()),
                    ]
                }
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
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Project'
    section = 'Settings'
    icon = blurdev.relativePath(__file__, 'img/settingsconfig.png')
    cls = SettingsConfig
    params = {
        # 		'param': 'test',
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
