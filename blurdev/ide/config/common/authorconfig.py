##
# 	\namespace	blurdev.config.authorconfig
#
# 	\remarks	Drives the Author config settings for the blurdev system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/19/10
#

import blurdev

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class AuthorConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

    def recordUi(self):
        section = self.section()
        section.setValue('name', str(self.uiNameTXT.text()))
        section.setValue('email', str(self.uiEmailTXT.text()))
        section.setValue('company', str(self.uiCompanyTXT.text()))
        section.setValue('initials', str(self.uiInitialsTXT.text()))

    def refreshUi(self):
        section = self.section()
        self.uiNameTXT.setText(section.value('name'))
        self.uiEmailTXT.setText(section.value('email'))
        self.uiCompanyTXT.setText(section.value('company'))
        self.uiInitialsTXT.setText(section.value('initials'))


def registerSections(configSet):
    """
        \remarks	registers the classes in this module to the inputed configSet instance
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # create the properties
    # define section
    group = 'Common'
    section = 'Author'
    icon = blurdev.relativePath(__file__, 'img/authorconfig.png')
    cls = AuthorConfig
    params = {'name': '', 'email': '', 'company': '', 'initials': ''}

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
