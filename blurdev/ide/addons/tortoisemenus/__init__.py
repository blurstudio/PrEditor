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
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction, QMenu


class TortoiseMenusAddon(IdeAddon):
    def activate(self, ide):
        # create any additional activation code that you would
        # need for the ide editor
        IdeFileMenu.additionalItems.append(self.createTortoiseMenus)
        ide.editorCreated.connect(self.editorCreated)

    def deactivate(self, ide):
        # create any additional deactivation code that you would
        # need for the ide editor
        funcs = IdeFileMenu.additionalItems
        if self.createTortoiseMenus in funcs:
            funcs.remove(self.createTortoiseMenus)
        return True

    def callback(self, cmd):
        if cmd:
            subprocess.Popen(cmd)

    def createAction(self, menu, node, path, before=None):
        act = QAction(node.attribute('name'), menu)
        self.setIconPath(act, node)
        act.triggered.connect(
            lambda: self.callback(node.attribute('command').format(filename=path))
        )
        if before:
            menu.insertAction(before, act)
        else:
            menu.addAction(act)
        return act

    def createMenu(self, menu, node, path, before=None):
        if node.name() == 'Menu':
            subMenu = QMenu(node.attribute('name'), menu)
            self.setIconPath(subMenu.menuAction(), node)
        else:
            self.createAction(menu, node, path, before)
            return None
        for child in node.children():
            nodeName = child.name()
            if nodeName == 'Menu':
                self.createMenu(subMenu, child, path, before)
            elif nodeName == 'Separator':
                subMenu.addSeparator()
            elif nodeName == 'Action':
                self.createAction(subMenu, child, path)
        return subMenu

    def createTortoiseMenus(self, menu, path=None):
        doc = blurdev.XML.XMLDocument()
        settings = os.environ.get('BDEV_TORTOISEMENU_PATH', None)
        if not settings:
            settings = blurdev.relativePath(__file__, 'settings.xml')
        if doc.load(settings):
            if path is None:
                path = menu.filepath()
            for subMenu in doc.root().children():
                parentName = subMenu.attribute('parent', 'uiExploreACT')
                parent = menu.parent().findChild(QAction, parentName)
                tortoiseMenu = self.createMenu(menu, subMenu, path, parent)
                if tortoiseMenu:
                    if parent:
                        menu.insertMenu(parent, tortoiseMenu)
                    else:
                        menu.addMenu(tortoiseMenu)
            if parent:
                menu.insertSeparator(parent)
            else:
                menu.addSeparator()

    def editorCreated(self, editor):
        parent = editor.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            menu = parent.systemMenu()
            self.createTortoiseMenus(menu, editor.filename())

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
