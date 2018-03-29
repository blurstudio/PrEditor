##
#   :namespace  python.blurdev.ide.addons.gitgui
#
#   :remarks    Addes a menu option to open git gui.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       09/13/13
#

import blurdev
import os
import subprocess
from blurdev.ide.ideaddon import IdeAddon
from blurdev.ide.idefilemenu import IdeFileMenu
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction


class GitGuiAddon(IdeAddon):
    def activate(self, ide):
        # create any additional activation code that you would
        # need for the ide editor
        IdeFileMenu.additionalItems.append(self.createGitGui)
        ide.editorCreated.connect(self.editorCreated)

    def deactivate(self, ide):
        # create any additional deactivation code that you would
        # need for the ide editor
        funcs = IdeFileMenu.additionalItems
        if self.createGitGui in funcs:
            funcs.remove(self.createGitGui)
        return True

    def createGitGui(self, menu, path=None):
        if path is None:
            path = menu.filepath()

        try:
            # Avoid redundant disk access if from the IdeFileMenu
            isFile = menu.isfile()
        except:
            isFile = os.path.isfile(path)
        dirname = path
        if isFile:
            dirname = os.path.dirname(path)

        menu.addSeparator()
        parent = menu.parent().findChild(QAction, 'uiExploreACT')

        guiAct = QAction(
            QIcon(blurdev.resourcePath('img/ide/git-gui.png')), 'Git Gui', menu
        )
        guiAct.setObjectName('uiGitGuiACT')
        guiAct.triggered.connect(lambda: self.runGitGui(dirname))
        bashAct = QAction(
            QIcon(blurdev.resourcePath('img/ide/git-bash.png')), 'Git Bash', menu
        )
        bashAct.setObjectName('uiGitBashACT')
        bashAct.triggered.connect(lambda: self.runGitBash(dirname))
        gitkAct = QAction(QIcon(blurdev.resourcePath('img/ide/gitk.png')), 'Gitk', menu)
        gitkAct.setObjectName('uiGitkACT')
        gitkAct.triggered.connect(lambda: self.runGitk(isFile, path))
        blameAct = QAction(
            QIcon(blurdev.resourcePath('img/ide/git-gui.png')), 'Git Blame', menu
        )
        blameAct.setObjectName('uiGitBlameACT')
        blameAct.triggered.connect(lambda: self.runGitBlame(path))

        if parent:
            menu.insertAction(parent, guiAct)
            menu.insertAction(parent, bashAct)
            menu.insertAction(parent, gitkAct)
            if isFile:
                menu.insertAction(parent, blameAct)
            menu.insertSeparator(parent)
        else:
            menu.addAction(guiAct)
            menu.addAction(bashAct)
            menu.addAction(gitkAct)
            if isFile:
                menu.addAction(blameAct)
            menu.addSeparator()

    def editorCreated(self, editor):
        parent = editor.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            menu = parent.systemMenu()
            self.createGitGui(menu, editor.filename())

    def runGitBash(self, path):
        if path:
            cmd = os.getenv(
                'BDEV_PLUGIN_GIT_GUI_CMD',
                r'"C:\Program Files\Git\git-bash.exe" "--cd={filename}"',
            )
            subprocess.Popen(cmd.format(filename=path))

    def runGitBlame(self, path):
        if path:
            cmd = os.getenv(
                'BDEV_PLUGIN_GIT_GUI_CMD',
                r'"C:\Program Files\Git\cmd\git-gui.exe" --working-dir {dirname} blame "{filename}"',
            )
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            subprocess.Popen(cmd.format(dirname=dirname, filename=basename))

    def runGitGui(self, path):
        # HKEY_CLASSES_ROOT\Directory\Background\shell\git_gui
        if path:
            cmd = os.getenv(
                'BDEV_PLUGIN_GIT_GUI_CMD',
                r'"C:\Program Files\Git\cmd\git-gui.exe" --working-dir "{filename}"',
            )
            subprocess.Popen(cmd.format(filename=path))

    def runGitk(self, isFile, path):
        if path:
            cmd = os.getenv(
                'BDEV_PLUGIN_GITK_CMD',
                r'"C:\Program Files\Git\cmd\gitk.exe" "{filename}"',
            )
            # gitk only works when run from somwhere inside the git directory
            if isFile:
                dirname = os.path.dirname(path)
            else:
                dirname = path
                # path = ''
            subprocess.Popen(cmd.format(filename=path), cwd=dirname)


# register the addon to the system
IdeAddon.register('GitGui', GitGuiAddon)

# create the init method (in case this addon doesn't get registered as part of a group)
def init():
    pass
