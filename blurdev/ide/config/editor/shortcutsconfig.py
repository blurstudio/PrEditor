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
        """records the latest ui settings to the data"""
        self.section()

    def refreshUi(self):
        """refrshes the ui with the latest data settings"""
        self.section()


def registerSections(configSet):
    """registers one or many new sections to the config system

    Args:
        configSet (blurdev.gui.dialogs.configdialog.ConfigSet):
    """

    # define section
    group = 'Editor'
    section = 'Shortcuts'
    icon = blurdev.relativePath(__file__, 'img/shortcutsconfig.png')
    cls = ShortcutsConfig
    params = {}

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
