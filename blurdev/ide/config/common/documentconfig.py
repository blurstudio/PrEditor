##
# 	\namespace	blurdev.ide.config.[module]
#
# 	\remarks	Edit the addon properties for the IDE
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/08/11
#

import os
import blurdev

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class DocumentConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        section = self.section()

        # record section values
        section.setValue('autoIndent', self.uiAutoIndentCHK.isChecked())
        section.setValue('autoComplete', self.uiAutoCompleteCHK.isChecked())
        section.setValue(
            'indentationsUseTabs', self.uiIndentationsUseTabsCHK.isChecked()
        )
        section.setValue('tabIndents', self.uiTabIndentsCHK.isChecked())
        section.setValue('tabWidth', self.uiTabWidthSPN.value())
        section.setValue('caretLineVisible', self.uiCaretLineVisibleCHK.isChecked())
        section.setValue('showWhitespaces', self.uiShowWhitespacesCHK.isChecked())
        section.setValue('showLineNumbers', self.uiShowLineNumbersCHK.isChecked())

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """
        section = self.section()

        # restore section values
        self.uiAutoIndentCHK.setChecked(section.value('autoIndent'))
        self.uiAutoCompleteCHK.setChecked(section.value('autoComplete'))
        self.uiIndentationsUseTabsCHK.setChecked(section.value('indentationsUseTabs'))
        self.uiTabIndentsCHK.setChecked(section.value('tabIndents'))
        self.uiTabWidthSPN.setValue(section.value('tabWidth'))
        self.uiCaretLineVisibleCHK.setChecked(section.value('caretLineVisible'))
        self.uiShowWhitespacesCHK.setChecked(section.value('showWhitespaces'))
        self.uiShowLineNumbersCHK.setChecked(section.value('showLineNumbers'))


def registerSections(configSet):
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Common'
    section = 'Document'
    icon = blurdev.relativePath(__file__, 'img/documentconfig.png')
    cls = DocumentConfig
    params = {
        'autoIndent': True,
        'autoComplete': True,
        'indentationsUseTabs': False,
        'tabIndents': True,
        'tabWidth': 4,
        'caretLineVisible': False,
        'showWhitespaces': False,
        'showLineNumbers': True,
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
