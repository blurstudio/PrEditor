##
# 	\namespace	blurdev.ide.config.[module]
#
# 	\remarks	Edit the addon properties for the IDE
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/08/11
#

from __future__ import absolute_import
import blurdev

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class ShortcutsConfig(ConfigSectionWidget):
    def initUi(self):
        # create the action editor widget
        import blurdev
        from blurdev.gui.widgets.actionmanagerwidget import ActionManagerWidget

        widget = ActionManagerWidget(self)
        widget.setActionsWidget(blurdev.core.ideeditor())

        # set the layout
        from Qt.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.setMargin(0)
        self.setLayout(layout)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        self.section()

        # record section values

    # 		section.setValue( 'param',  str(self.uiParamTXT.text()) )

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """
        self.section()

        # restore section values


# 		self.uiParamTXT.setText(section.value('param'))


def registerSections(configSet):
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Editor'
    section = 'Shortcuts'
    icon = blurdev.relativePath(__file__, 'img/shortcutsconfig.png')
    cls = ShortcutsConfig
    params = {
        # 		'param': 'test',
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
