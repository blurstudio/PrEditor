##
# 	\namespace	blurdev.ide.config.editor.[module]
#
# 	\remarks	Edit settings for the different language configurations for the IDE
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/15/11
#

from __future__ import absolute_import
import os
import blurdev
from blurdev.ide import lang

from Qt import QtCompat
from Qt.QtCore import QSize
from Qt.QtGui import QIcon
from Qt.QtWidgets import QMessageBox, QTreeWidgetItem

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class LanguageItem(QTreeWidgetItem):
    def __init__(self, language):
        super(LanguageItem, self).__init__(
            [language.name(), ','.join(language.fileTypes())]
        )
        self.setSizeHint(0, QSize(0, 18))
        self.setToolTip(0, 'Loaded from: %s' % language.sourcefile())
        self._language = language

    def language(self):
        return self._language


class LanguagesConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        header = self.uiLanguageTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.Stretch)

        header = self.uiUserLanguageTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.Stretch)

        # update the icons
        self.uiAddBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self.uiEditBTN.setIcon(QIcon(blurdev.resourcePath('img/edit.png')))
        self.uiRemoveBTN.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))

        # create connections
        self.uiAddBTN.clicked.connect(self.addLanguage)
        self.uiEditBTN.clicked.connect(self.editLanguage)
        self.uiRemoveBTN.clicked.connect(self.removeLanguage)
        self.uiUserLanguageTREE.itemDoubleClicked.connect(self.editLanguage)
        self.uiLanguageTREE.itemDoubleClicked.connect(self.editBaseLanguage)

    def addLanguage(self):
        from blurdev.ide.idelanguagedialog import IdeLanguageDialog

        language = lang.Language()
        language.setCustom(True)
        if IdeLanguageDialog.edit(language, self):
            lang.refresh()
            self.refreshUi()

    def editLanguage(self):
        from blurdev.ide.idelanguagedialog import IdeLanguageDialog

        item = self.uiUserLanguageTREE.currentItem()
        if item:
            if IdeLanguageDialog.edit(item.language(), self):
                lang.refresh()
                self.refreshUi()

    def editBaseLanguage(self, item):
        from blurdev.ide.idelanguagedialog import IdeLanguageDialog

        IdeLanguageDialog.edit(item.language(), self)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        self.section()

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """
        self.section()

        self.uiLanguageTREE.clear()
        self.uiUserLanguageTREE.clear()

        languages = lang.languages()
        for name in languages:
            language = lang.byName(name)
            item = LanguageItem(language)

            if not language.isCustom():
                self.uiLanguageTREE.addTopLevelItem(item)
            else:
                self.uiUserLanguageTREE.addTopLevelItem(item)

    def removeLanguage(self):
        item = self.uiUserLanguageTREE.currentItem()

        if (
            item
            and QMessageBox.question(
                self,
                'Remove Template',
                'Are you sure you want to remove the selected language?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            filename = item.language().sourcefile()
            if os.path.exists(filename):
                os.remove(filename)

            # refresh the languages
            lang.refresh()
            self.refreshUi()


def registerSections(configSet):
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Editor'
    section = 'Languages'
    icon = blurdev.relativePath(__file__, 'img/languagesconfig.png')
    cls = LanguagesConfig
    params = {
        # 		'param': 'test',
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
