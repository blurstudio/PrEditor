##
# 	\namespace	[FILENAME]
#
# 	\remarks	[ADD REMARKS]
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/02/10
#

import os
import blurdev
import blurdev.gui
from blurdev.gui import Dialog
from blurdev import osystem
from Qt import QtCompat
from Qt.QtCore import Qt
from Qt.QtGui import QIcon, QCursor
from Qt.QtWidgets import QMessageBox, QTreeWidgetItem, QMenu
from .ideproject import IdeProject


class IdeProjectFavoritesDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        blurdev.gui.loadUi(__file__, self)

        self.uiFavoriteTREE.customContextMenuRequested.connect(self.showMenu)

        self.refresh()

    def addFavorite(self):

        filename, _ = QtCompat.QFileDialog.getOpenFileName(
            self,
            'Blur IDE Project',
            osystem.expandvars(os.environ.get('BDEV_PATH_PROJECT', '')),
            'Blur IDE Projects (*.blurproj);;XML Files (*.xml);;All Files (*.*)',
        )

        if filename and filename not in IdeProject.Favorites:
            IdeProject.Favorites.append(filename)
            self.refresh()

    def currentProject(self):
        item = self.uiFavoriteTREE.currentItem()
        if not item:
            return None

        filename = item.data(0, Qt.UserRole)
        if not os.path.exists(filename):
            QMessageBox.critical(
                self,
                'Could not Find Favorite',
                'Could not find the favorites file at: %s' % filename,
            )
            return None

        return IdeProject.fromXml(filename)

    def refresh(self):
        self.uiFavoriteTREE.blockSignals(True)
        self.uiFavoriteTREE.setUpdatesEnabled(False)
        self.uiFavoriteTREE.clear()

        filenames = IdeProject.Favorites
        filenames.sort()

        favicon = QIcon(blurdev.resourcePath('img/favorite.png'))

        for filename in filenames:
            name = os.path.basename(filename).split('.')[0]
            item = QTreeWidgetItem([name])
            item.setToolTip(
                0, '<b>%s Project</b><hr><small>%s</small>' % (name, filename)
            )
            item.setData(0, Qt.UserRole, filename)
            item.setIcon(0, favicon)
            self.uiFavoriteTREE.addTopLevelItem(item)

        self.uiFavoriteTREE.setUpdatesEnabled(True)
        self.uiFavoriteTREE.blockSignals(False)

    def removeFavorite(self):
        item = self.uiFavoriteTREE.currentItem()
        if not item:
            return

        IdeProject.Favorites.remove(item.data(0, Qt.UserRole))
        self.refresh()

    def showMenu(self):

        menu = QMenu(self)
        menu.addAction('Add Favorite...').triggered.connect(self.addFavorite)
        menu.addSeparator()
        menu.addAction('Remove from Favorites').triggered.connect(self.removeFavorite)

        menu.popup(QCursor.pos())

    @staticmethod
    def getProject():

        dlg = IdeProjectFavoritesDialog(blurdev.core.activeWindow())
        if dlg.exec_():
            return dlg.currentProject()
        return None
