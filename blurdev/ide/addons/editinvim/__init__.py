##
#   :namespace  python.blurdev.ide.addons.editinvim
#
#   :remarks    Addes a menu option to edit in vim.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       09/13/13
#

import blurdev
from blurdev.ide.ideaddon import IdeAddon
from blurdev.ide.idefilemenu import IdeFileMenu
from PyQt4.QtGui import QIcon, QAction


class EditInVimAddon(IdeAddon):
    def activate(self, ide):
        print 'Activating editInVim'
        # create any additional activation code that you would
        # need for the ide editor
        self.path = None
        IdeFileMenu.additionalItems.append(self.createEditInVim)

    def deactivate(self, ide):
        print 'deactivate editInVim'
        # create any additional deactivation code that you would
        # need for the ide editor
        funcs = IdeFileMenu.additionalItems
        if self.createEditInVim in funcs:
            print 'Removing editInVim'
            funcs.remove(self.createEditInVim)
        return True

    def createEditInVim(self, menu):
        # limit to just project tab
        # if menu.projectMode():
        if True:
            menu.addSeparator()
            act = QAction(
                QIcon(blurdev.resourcePath('img/ide/goto_def.png')), 'Edit in VIM', menu
            )
            act.setObjectName('uiEditInVimACT')
            self.path = menu.filepath()
            act.triggered.connect(self.editInVim)
            parent = menu.findChild(QAction, r'uiCopyFilenameSEP')
            if parent:
                menu.insertSeparator(parent)
                menu.insertAction(parent, act)
            else:
                menu.insertSeparator()
                menu.addAction(act)

    def editInVim(self):
        if self.path:
            blurdev.osystem.explore(self.path)


# register the addon to the system
IdeAddon.register('EditInVim', EditInVimAddon)

# create the init method (in case this addon doesn't get registered as part of a group)
def init():
    pass
