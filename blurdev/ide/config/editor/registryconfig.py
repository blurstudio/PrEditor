##
# 	\namespace	linux-2011-07-19.ide.config.editor.[module]
#
# 	\remarks	Controls the way files will be loaded and run from a registry
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		07/20/11
#

from __future__ import absolute_import
import blurdev

from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QTreeWidgetItem,
    QVBoxLayout,
)

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class RegistryDialog(QDialog):
    def __init__(self, parent):
        super(RegistryDialog, self).__init__(parent)

        self.setWindowTitle('Registry Key')

        # create the key, value editor
        self.uiKeyTXT = QLineEdit(self)
        self.uiValueTXT = QLineEdit(self)
        self.uiDialogBTNS = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        self.uiKeyTXT.setMaximumWidth(100)

        # create the layouts
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.uiKeyTXT)
        hlayout.addWidget(self.uiValueTXT)

        # create the vertical layout
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.uiDialogBTNS)

        # set the main layout
        self.setLayout(vlayout)
        self.adjustSize()

        # create connections
        self.uiDialogBTNS.accepted.connect(self.accept)
        self.uiDialogBTNS.rejected.connect(self.reject)

    def accept(self):
        if not self.uiKeyTXT.text():
            QMessageBox.critical(
                self,
                'No Key Provided',
                'You need to provide a key for the environment key/value.',
            )
            return False

        super(RegistryDialog, self).accept()

    def entry(self):
        return (self.uiKeyTXT.text(), self.uiValueTXT.text())

    def setEntry(self, key, value):
        self.uiKeyTXT.setText(str(key))
        self.uiValueTXT.setText(str(value))


class RegistryConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # create icons
        self.uiAddBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self.uiEditBTN.setIcon(QIcon(blurdev.resourcePath('img/edit.png')))
        self.uiRemoveBTN.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))

        # create connections
        self.uiAddBTN.clicked.connect(self.addEntry)
        self.uiEditBTN.clicked.connect(self.editEntry)
        self.uiRemoveBTN.clicked.connect(self.removeEntry)

    def addEntry(self):
        dlg = RegistryDialog(self)
        if dlg.exec_():
            key, value = dlg.entry()
            self.uiGlobalRegistryTREE.addTopLevelItem(
                QTreeWidgetItem([key, 'Global Override', value])
            )

    def editEntry(self):
        item = self.uiGlobalRegistryTREE.currentItem()
        if not item:
            return False

        dlg = RegistryDialog(self)
        dlg.setEntry(item.text(0), item.text(2))
        if dlg.exec_():
            key, value = dlg.entry()
            item.setText(0, key)
            item.setText(2, value)

    def recordUi(self):
        """
            \remarks	records the latest ui settings to the data
        """
        section = self.section()

        # record section values
        entries = {}
        for i in range(self.uiGlobalRegistryTREE.topLevelItemCount()):
            item = self.uiGlobalRegistryTREE.topLevelItem(i)
            entries[str(item.text(0))] = str(item.text(2))

        section.setValue('entries', entries)

    def removeEntry(self):
        item = self.uiGlobalRegistryTREE.currentItem()

        if (
            item
            and QMessageBox.question(
                self,
                'Remove Entry',
                'Are you sure you want to remove this entry?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.uiGlobalRegistryTREE.takeTopLevelItem(
                self.uiGlobalRegistryTREE.indexOfTopLevelItem(item)
            )

    def refreshUi(self):
        """
            \remarks	refrshes the ui with the latest data settings
        """

        self.uiGlobalRegistryTREE.clear()
        self.uiInstalledRegistryTREE.clear()

        # collect the registry
        ide = self.configData('ide')
        if not ide:
            return

        from blurdev import osystem
        from blurdev.ide.ideregistry import RegistryType

        # load the installed registry data
        self.uiInstalledRegistryTREE.setUpdatesEnabled(False)
        self.uiInstalledRegistryTREE.blockSignals(True)
        self.uiGlobalRegistryTREE.setUpdatesEnabled(False)
        self.uiGlobalRegistryTREE.blockSignals(True)

        commands = ide.registry().commands()
        for commandType in commands:
            for key, value in commands[commandType].items():
                # add to the installed registry
                if commandType not in (
                    RegistryType.GlobalOverride,
                    RegistryType.ProjectOverride,
                ):
                    item = QTreeWidgetItem(
                        [key, RegistryType.labelByValue(commandType), str(value)]
                    )
                    item.setToolTip(2, osystem.expandvars(str(value)))
                    self.uiInstalledRegistryTREE.addTopLevelItem(item)

                # add to the override registry
                elif commandType == RegistryType.GlobalOverride:
                    item = QTreeWidgetItem(
                        [key, RegistryType.labelByValue(commandType), str(value)]
                    )
                    item.setToolTip(2, osystem.expandvars(str(value)))
                    self.uiGlobalRegistryTREE.addTopLevelItem(item)

        self.uiInstalledRegistryTREE.sortByColumn(0, Qt.AscendingOrder)
        self.uiGlobalRegistryTREE.sortByColumn(0, Qt.AscendingOrder)

        self.uiGlobalRegistryTREE.setUpdatesEnabled(True)
        self.uiGlobalRegistryTREE.blockSignals(False)
        self.uiInstalledRegistryTREE.setUpdatesEnabled(True)
        self.uiInstalledRegistryTREE.blockSignals(False)


def registerSections(configSet):
    """
        \remarks	registers one or many new sections to the config system
        \param		configSet 	<blurdev.gui.dialogs.configdialog.ConfigSet>
    """

    # define section
    group = 'Editor'
    section = 'Registry'
    icon = blurdev.relativePath(__file__, 'img/registryconfig.png')
    cls = RegistryConfig
    params = {
        'entries': {},
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
