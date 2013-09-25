##
#   :namespace  python.blurdev.ide.addons.tortoisemenus
#
#   :remarks    [desc::commented]
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       09/24/13
#

import blurdev
import os
import subprocess
from blurdev.ide.ideaddon import IdeAddon
from blurdev.ide.idefilemenu import IdeFileMenu
from PyQt4.QtGui import QIcon, QAction, QMenu


class TortoiseMenusAddon(IdeAddon):
    def activate(self, ide):
        # create any additional activation code that you would
        # need for the ide editor
        self.path = None
        IdeFileMenu.additionalItems.append(self.createTortoiseMenus)

    def deactivate(self, ide):
        print 'deactivate Tortoise'
        # create any additional deactivation code that you would
        # need for the ide editor
        funcs = IdeFileMenu.additionalItems
        if self.createTortoiseMenus in funcs:
            print 'Removing Tortoise'
            funcs.remove(self.createTortoiseMenus)
        return True

    def callback(self, cmd):
        if self.path:
            subprocess.call(cmd.format(filename=self.path))

    def createAction(self, menu, node):
        act = menu.addAction(node.attribute('name'))
        self.setIconPath(act, node)
        act.triggered.connect(lambda: self.callback(node.attribute('command')))

    def createMenu(self, menu, node):
        subMenu = QMenu(node.attribute('name'), menu)
        self.setIconPath(subMenu.menuAction(), node)
        for child in node.children():
            nodeName = child.name()
            if nodeName == 'Menu':
                self.createMenu(subMenu, child)
            elif nodeName == 'Separator':
                subMenu.addSeparator()
            elif nodeName == 'Action':
                self.createAction(subMenu, child)
        return subMenu

    def createTortoiseMenus(self, menu):
        doc = blurdev.XML.XMLDocument()
        path = os.environ.get('BDEV_TORTOISEMENU_PATH', None)
        if not path:
            path = blurdev.relativePath(__file__, 'settings.xml')
        if doc.load(path):
            self.path = menu.filepath()
            parent = menu.parent().findChild(QAction, 'uiExploreACT')
            for subMenu in doc.root().children():
                tortoiseMenu = self.createMenu(menu, subMenu)
                if parent:
                    menu.insertMenu(parent, tortoiseMenu)
                else:
                    menu.addMenu(tortoiseMenu)
            if parent:
                menu.insertSeparator(parent)
            else:
                menu.addSeparator()

    def setIconPath(self, act, node):
        path = node.attribute('icon', None)
        if path:
            path = path.format(
                relative=blurdev.relativePath(__file__, ''),
                blurdev=blurdev.resourcePath(''),
            )
            act.setIcon(QIcon(path))


# register the addon to the system
IdeAddon.register('TortoiseMenus', TortoiseMenusAddon)

# create the init method (in case this addon doesn't get registered as part of a group)
def init():
    pass
