##
# 	\namespace	blurdev.ide.config.editor.[module]
#
# 	\remarks	Edit settings for the different language configurations for the IDE
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/15/11
#

import os
import blurdev

from PyQt4.QtCore import QSize
from PyQt4.QtGui import QTreeWidgetItem

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class LanguagesConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        header = self.uiLanguageTREE.header()
        header.setResizeMode(0, header.Stretch)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        section = self.section()

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """
        section = self.section()

        from blurdev.ide import lang

        self.uiLanguageTREE.clear()

        languages = lang.languages()
        for name in languages:
            language = lang.byName(name)
            item = QTreeWidgetItem([language.name(), ','.join(language.fileTypes())])
            item.setSizeHint(0, QSize(0, 18))
            self.uiLanguageTREE.addTopLevelItem(item)


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
