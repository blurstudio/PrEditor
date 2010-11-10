##
# 	\namespace	blurdev.ide.templatebuilder
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from blurdev.gui import Dialog


class IdeTemplateBrowser(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # import the templates
        import templates

        from PyQt4.QtGui import QIcon

        folder = QIcon(blurdev.resourcePath('img/folder.png'))

        from PyQt4.QtCore import Qt, QSize
        from PyQt4.QtGui import QTreeWidgetItem

        for lang in templates.templateLanguages():
            item = QTreeWidgetItem([lang])
            item.setSizeHint(0, QSize(250, 23))
            item.setIcon(0, folder)

            for grp in templates.templateGroups(lang):
                gitem = QTreeWidgetItem([grp])
                gitem.setSizeHint(0, QSize(250, 23))
                gitem.setIcon(0, QIcon(blurdev.resourcePath('img/%s.png' % grp)))
                item.addChild(gitem)

            self.uiTemplateTREE.addTopLevelItem(item)
            item.setExpanded(True)

        # create the thumbnail scene
        from blurdev.gui.scenes.thumbnailscene import ThumbnailScene

        thumbscene = ThumbnailScene(self.uiTemplatesVIEW)
        self.uiTemplatesVIEW.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        thumbscene.setLayoutDirection(Qt.Horizontal)
        thumbscene.setThumbnailSize(QSize(48, 48))

        self.uiTemplatesVIEW.setScene(thumbscene)
        self.uiTemplateTREE.itemSelectionChanged.connect(self.refreshTemplates)
        thumbscene.selectionChanged.connect(self.refreshDescription)
        thumbscene.itemDoubleClicked.connect(self.runWizard)

    def currentTemplate(self):
        items = self.uiTemplatesVIEW.scene().selectedItems()
        if items:
            item = items[0]
            from PyQt4.QtCore import Qt

            import templates

            return templates.find(item.data(Qt.UserRole).toString())
        return None

    def refreshDescription(self):
        templ = self.currentTemplate()
        if templ:
            self.uiDescriptionLBL.setText(templ.desc)
        else:
            self.uiDescriptionLBL.setText('')

    def refreshTemplates(self):
        scene = self.uiTemplatesVIEW.scene()
        scene.clear()
        self.uiDescriptionLBL.setText('')

        item = self.uiTemplateTREE.currentItem()
        if not (item and item.parent()):
            return

        import templates
        from PyQt4.QtCore import Qt

        templs = templates.templates(item.parent().text(0), item.text(0))
        for templ in templs:
            item = scene.addThumbnail(templ.iconFile)

            item.setCaption(templ.name)
            item.setToolTip(templ.toolTip)
            item.setData(Qt.UserRole, templ.templateId)

        scene.recalculate(scene.sceneRect(), True)

    def runWizard(self):
        templ = self.currentTemplate()
        if templ:
            if templ.runWizard():
                self.accept()

    @staticmethod
    def createFromTemplate():

        import blurdev

        if IdeTemplateBrowser(blurdev.core.activeWindow()).exec_():

            return True

        return False
