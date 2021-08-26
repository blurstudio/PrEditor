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

from Qt import QtCompat
from Qt.QtCore import QSize, Qt
from Qt.QtWidgets import QTreeWidgetItem

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class AddonsConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # update the header stretch factors
        header = self.uiAddonsTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.Stretch)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        pass

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """
        from blurdev.ide.ideaddon import IdeAddon

        modules = IdeAddon.modules.values()
        modules.sort(key=lambda x: x.name())
        for module in modules:
            moditem = QTreeWidgetItem([module.name(), module.status()])
            if module.isEnabled():
                moditem.setCheckState(0, Qt.Checked)
            else:
                moditem.setCheckState(0, Qt.Unchecked)

            # update the look of the module item
            font = moditem.font(0)
            font.setBold(True)
            moditem.setFont(0, font)
            moditem.setFont(1, font)
            moditem.setSizeHint(0, QSize(220, 18))

            # set the error feedback
            moditem.setToolTip(0, module.errors())

            # add the addons for this module
            for addon in module.addons():
                additem = QTreeWidgetItem([addon.name(), addon.status()])
                if addon.isEnabled():
                    additem.setCheckState(0, Qt.Checked)
                else:
                    additem.setCheckState(0, Qt.Unchecked)

                additem.setSizeHint(0, QSize(220, 18))
                additem.setToolTip(0, addon.errors())
                moditem.addChild(additem)

            self.uiAddonsTREE.addTopLevelItem(moditem)
            moditem.setExpanded(True)


def registerSections(configSet):
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Common'
    section = 'Addons'
    icon = blurdev.relativePath(__file__, 'img/addonsconfig.png')
    cls = AddonsConfig
    params = {
        # 		'param': 'test',
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
