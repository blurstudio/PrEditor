##
# 	\namespace	linux-2011-07-19.ide.config.editor.[module]
#
# 	\remarks	Modify the scripting templates that can get used
#
# 	\author		[author::email]
# 	\author		[author::company]
# 	\date		07/20/11
#

from __future__ import absolute_import
import os
import blurdev

from Qt.QtCore import QSize, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QInputDialog, QMessageBox, QTreeWidgetItem

from blurdev import template

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class TemplatesConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self.splitter.widget(0).setMaximumWidth(200)

        # create icons
        self.uiAddBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self.uiRemoveBTN.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))
        self.uiSaveBTN.setIcon(QIcon(blurdev.resourcePath('img/save.png')))

        # create connections
        self.uiAddBTN.clicked.connect(self.addTemplate)
        self.uiRemoveBTN.clicked.connect(self.removeTemplate)
        self.uiSaveBTN.clicked.connect(self.saveTemplate)

        self.uiUserTemplateTREE.itemSelectionChanged.connect(self.editUserTemplate)
        self.uiTemplateTREE.itemSelectionChanged.connect(self.editTemplate)

    def addTemplate(self):
        name, accepted = QInputDialog.getText(
            self, 'Template Name', 'New Template Name'
        )
        if not accepted:
            return False

        if os.path.exists(template.userTemplFilename(name)):
            QMessageBox.critical(
                None, 'Template Exists', '%s is already a user defined template.'
            )
            return False

        item = QTreeWidgetItem([name])
        item.setSizeHint(0, QSize(0, 18))
        self.uiUserTemplateTREE.addTopLevelItem(item)
        self.uiUserTemplateTREE.sortByColumn(0, Qt.AscendingOrder)
        self.uiUserTemplateTREE.setCurrentItem(item)

    def editUserTemplate(self):
        self.uiTemplateTREE.blockSignals(True)
        self.uiTemplateTREE.setCurrentItem(None)
        self.uiTemplateTREE.blockSignals(False)

        self.uiTemplateTXT.setReadOnly(False)
        item = self.uiUserTemplateTREE.currentItem()
        if not item:
            self.uiTemplateTXT.setText('')
            return False

        filename = template.userTemplFilename(item.text(0))
        if os.path.exists(filename):
            f = open(filename, 'r')
            data = f.read()
            f.close()
        else:
            data = ''

        self.uiTemplateTXT.setText(data)

    def editTemplate(self):
        self.uiUserTemplateTREE.blockSignals(True)
        self.uiUserTemplateTREE.setCurrentItem(None)
        self.uiUserTemplateTREE.blockSignals(False)

        self.uiTemplateTXT.setReadOnly(True)
        item = self.uiTemplateTREE.currentItem()
        if not item:
            self.uiTemplateTXT.setText('')
            return False

        filename = template.templFilename(item.text(0))
        if os.path.exists(filename):
            f = open(filename, 'r')
            data = f.read()
            f.close()
        else:
            data = ''

        self.uiTemplateTXT.setText(data)

    def recordUi(self):
        """records the latest ui settings to the data"""
        self.saveTemplate()

    def refreshUi(self):
        """refreshes the ui with the latest data settings"""

        # add the user templates
        self.uiUserTemplateTREE.clear()

        for templName in template.userTemplNames():
            item = QTreeWidgetItem([templName])
            item.setSizeHint(0, QSize(0, 18))
            self.uiUserTemplateTREE.addTopLevelItem(item)

        self.uiUserTemplateTREE.sortByColumn(0, Qt.AscendingOrder)

        # restore section values
        self.uiTemplateTREE.clear()

        # add the templates to the tree
        for templName in template.templNames():
            item = QTreeWidgetItem([templName])
            item.setSizeHint(0, QSize(0, 18))
            self.uiTemplateTREE.addTopLevelItem(item)

        self.uiTemplateTREE.sortByColumn(0, Qt.AscendingOrder)

    def removeTemplate(self):
        item = self.uiUserTemplateTREE.currentItem()

        if (
            item
            and QMessageBox.question(
                self,
                'Remove Template',
                'Are you sure you want to remove the selected template?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            filename = template.userTemplFilename(item.text(0))
            if os.path.exists(filename):
                os.remove(filename)

            self.uiUserTemplateTREE.takeTopLevelItem(
                self.uiUserTemplateTREE.indexOfTopLevelItem(item)
            )
            # refresh the ide
            ide = self.configData('ide')
            if ide:
                ide.refreshTemplateCompleter()

    def saveTemplate(self):
        item = self.uiUserTemplateTREE.currentItem()
        if not item:
            return

        filename = template.userTemplFilename(item.text(0))
        path = os.path.dirname(filename)

        # ensure the path exists
        if not os.path.exists(path):
            os.makedirs(path)

        # save the file
        f = open(filename, 'w')
        f.write(self.uiTemplateTXT.toPlainText())
        f.close()

        # refresh the ide
        ide = self.configData('ide')
        if ide:
            ide.refreshTemplateCompleter()


def registerSections(configSet):
    """registers one or many new sections to the config system

    Args:
        configSet (blurdev.gui.dialogs.configdialog.ConfigSet):
    """

    # define section
    group = 'Editor'
    section = 'Templates'
    icon = blurdev.relativePath(__file__, 'img/templatesconfig.png')
    cls = TemplatesConfig
    params = {}

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
