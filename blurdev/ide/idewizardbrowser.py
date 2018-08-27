##
# 	\namespace	blurdev.ide.idewizardbrowser
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin wizards
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from Qt.QtCore import QSize, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QTreeWidgetItem
import blurdev
import blurdev.gui
from blurdev.gui import Dialog


class IdeWizardBrowser(Dialog):
    def __init__(self, parent):
        super(IdeWizardBrowser, self).__init__(parent)

        # load the ui
        blurdev.gui.loadUi(__file__, self)
        self.setWindowIcon(QIcon(blurdev.resourcePath('img/ide/newwizard.png')))

        # import the wizards
        import wizards

        folder = QIcon(blurdev.resourcePath('img/folder.png'))

        for lang in wizards.wizardLanguages():
            item = QTreeWidgetItem([lang])
            item.setSizeHint(0, QSize(250, 23))
            item.setIcon(0, folder)

            for grp in wizards.wizardGroups(lang):
                gitem = QTreeWidgetItem([grp])
                gitem.setSizeHint(0, QSize(250, 23))
                gitem.setIcon(
                    0, QIcon(blurdev.resourcePath('img/%s.png' % grp.lower()))
                )
                item.addChild(gitem)

            self.uiWizardTREE.addTopLevelItem(item)
            item.setExpanded(True)

        # create the thumbnail scene
        from blurdev.gui.scenes.thumbnailscene import ThumbnailScene

        thumbscene = ThumbnailScene(self.uiWizardsVIEW)
        self.uiWizardsVIEW.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        thumbscene.setLayoutDirection(Qt.Horizontal)
        thumbscene.setThumbnailSize(QSize(48, 48))

        self.uiWizardsVIEW.setScene(thumbscene)
        self.uiWizardTREE.itemSelectionChanged.connect(self.refreshWizards)
        thumbscene.selectionChanged.connect(self.refreshDescription)
        thumbscene.itemDoubleClicked.connect(self.runWizard)

    def currentWizard(self):
        items = self.uiWizardsVIEW.scene().selectedItems()
        if items:
            item = items[0]
            from . import wizards

            return wizards.find(item.data(Qt.UserRole))
        return None

    def refreshDescription(self):
        templ = self.currentWizard()
        if templ:
            self.uiDescriptionLBL.setText(templ.desc)
        else:
            self.uiDescriptionLBL.setText('')

    def refreshWizards(self):
        scene = self.uiWizardsVIEW.scene()
        scene.clear()
        self.uiDescriptionLBL.setText('')

        item = self.uiWizardTREE.currentItem()
        if not (item and item.parent()):
            return

        from . import wizards

        templs = wizards.wizards(item.parent().text(0), item.text(0))
        for templ in templs:
            item = scene.addThumbnail(templ.iconFile)
            item.setCaption(templ.name)
            item.setToolTip(templ.toolTip)
            item.setData(Qt.UserRole, templ.wizardId)

        scene.recalculate(scene.sceneRect(), True)

    def runWizard(self):
        templ = self.currentWizard()
        if templ:
            if templ.runWizard():
                self.accept()

    @staticmethod
    def createFromWizard():
        if IdeWizardBrowser(blurdev.core.activeWindow()).exec_():
            return True
        return False
