##
# 	\namespace	blurdev.ide.idefilemenu
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

from __future__ import absolute_import
import os.path

from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QApplication, QMenu, QMessageBox

import blurdev


class IdeFileMenu(QMenu):
    # additionalItems is a list of functions that are called when adding menu items to
    # the IdeFileMenu. It passes along the file menu after the menu has been created.
    # def additionalStuff(self, menu):
    additionalItems = []

    def __init__(self, ide, filepath, projectMode=False):
        # initialize the menu
        super(IdeFileMenu, self).__init__(ide)

        # define properties
        self._filepath = filepath
        self._projectMode = projectMode
        self._isfile = os.path.isfile(self._filepath)

        # define the menu
        self.defineMenu()

    def defineMenu(self):
        ide = self.ide()
        projectMode = self.projectMode()

        # add the new from wizard action from the ide
        self.addAction(ide.uiNewFromWizardACT)

        # create the new folder menu item
        act = self.addAction('New Folder...')
        act.setObjectName('uiNewFolderACT')
        act.triggered.connect(ide.createNewFolder)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/newfolder.png')))

        # add the new action from the ide
        self.addAction(ide.uiNewACT)

        sep = self.addSeparator()
        sep.setObjectName('uiExploreSEP')

        # create the explore action
        self.addAction(ide.uiExploreACT)

        # create the launch console action
        self.addAction(ide.uiConsoleACT)

        if not self.isfile():
            # create the find in files action
            act = self.addAction('Find in Files...')
            act.setObjectName('uiFindInFilesACT')
            act.triggered.connect(ide.projectFindInFiles)
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/folder_find.png')))

        # determine if this is in project mode
        if projectMode:
            act = self.addAction('Refresh')
            act.setObjectName('uiRefreshACT')
            act.triggered.connect(ide.projectRefreshItem)
            act.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))

        sep = self.addSeparator()
        sep.setObjectName('uiEditSEP')

        if self.isfile():
            # create the open action
            act = self.addAction('Edit')
            act.setObjectName('uiEditACT')
            act.triggered.connect(ide.documentOpenItem)
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/edit.png')))

            # add the run action
            act = self.addAction('Run...')
            act.setObjectName('uiRunACT')
            act.triggered.connect(ide.runCurrentScript)
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/run.png')))

            # add the run standalone action
            act = self.addAction('Run (Standalone)...')
            act.setObjectName('uiRunStandaloneACT')
            act.triggered.connect(ide.runCurrentStandalone)

            # add the run debug action
            act = self.addAction('Run (Debug)...')
            act.setObjectName('uiRunDebugACT')
            act.triggered.connect(ide.runCurrentStandaloneDebug)

        sep = self.addSeparator()
        sep.setObjectName('uiCopyFilenameSEP')
        self.addAction(ide.uiCopyFilenameACT)
        if projectMode:
            sep = self.addSeparator()
            sep.setObjectName('uiRemoveSEP')

            # create the remove action
            act = self.addAction('Delete')
            act.setObjectName('uiRemoveACT')
            act.triggered.connect(self.removeFilepath)
            act.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))

            # add the edit project action
            self.addAction(ide.uiEditProjectACT)

        # Add any aditional menu items that may have been added.
        for funct in self.additionalItems:
            funct(self)

    def removeFilepath(self):
        msg = (
            'Are you sure you want to remove this from the filesystem? '
            'This is not undoable.'
        )
        req = QMessageBox.question(
            self, 'Removing Filepath', msg, QMessageBox.Yes | QMessageBox.No
        )
        if req == QMessageBox.Yes:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            import os
            import shutil

            fpath = self.filepath()

            if self.isfile():
                os.remove(fpath)
            else:
                shutil.rmtree(fpath)

            item = self.ide().currentProjectItem()
            if item and item.parent():
                item.parent().refresh()

            QApplication.restoreOverrideCursor()

    def filepath(self):
        return self._filepath

    def ide(self):
        return self.parent()

    def isfile(self):
        return self._isfile

    def projectMode(self):
        return self._projectMode
