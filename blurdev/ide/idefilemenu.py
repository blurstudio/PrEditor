##
# 	\namespace	blurdev.ide.idefilemenu
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import os.path

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMenu, QIcon, QApplication

import blurdev


class IdeFileMenu(QMenu):
    def __init__(self, ide, filepath, projectMode=False):
        # initialize the menu
        super(IdeFileMenu, self).__init__(ide)

        # define properties
        self._filepath = filepath
        self._projectMode = projectMode

        # define the menu
        self.defineMenu()

    def defineMenu(self):
        ide = self.ide()
        projectMode = self.projectMode()
        filepath = self.filepath()

        isfile = os.path.isfile(filepath)

        # add the new from wizard action from the ide
        self.addAction(ide.uiNewFromWizardACT)

        # create the new folder menu item
        act = self.addAction('New Folder...')
        act.setObjectName('uiNewFolderACT')
        act.triggered.connect(ide.createNewFolder)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/newfolder.png')))

        # add the new action from the ide
        self.addAction(ide.uiNewACT)

        self.addSeparator()

        # create the explore action
        self.addAction(ide.uiExploreACT)

        # create the launch console action
        self.addAction(ide.uiConsoleACT)

        if not isfile:
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

        self.addSeparator()

        if isfile:
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

        self.addSeparator()
        self.addAction(ide.uiCopyFilenameACT)
        if projectMode:
            self.addSeparator()

            # create the remove action
            act = self.addAction('Delete')
            act.setObjectName('uiRemoveACT')
            act.triggered.connect(self.removeFilepath)
            act.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))

            # add the edit project action
            self.addAction(ide.uiEditProjectACT)

    def removeFilepath(self):
        from PyQt4.QtGui import QMessageBox as msg

        if (
            msg.question(
                self,
                'Removing Filepath',
                'Are you sure you want to remove this from the filesystem?  This is not undoable.',
                msg.Yes | msg.No,
            )
            == msg.Yes
        ):
            QApplication.setOverrideCursor(Qt.WaitCursor)

            import os, shutil

            fpath = self.filepath()

            if os.path.isfile(fpath):
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
        return os.path.isfile(self._filepath)

    def projectMode(self):
        return self._projectMode
