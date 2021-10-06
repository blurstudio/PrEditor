##
# 	\namespace	linux-2011-07-19.ide.config.editor.[module]
#
#   \remarks    Allows the user to view and edit the environment variables used for the
#               editor
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		07/20/11
#

from __future__ import absolute_import
import blurdev

from Qt import QtCompat
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

from blurdev import settings
from blurdev.gui.dialogs.configdialog import ConfigSectionWidget


class EnvironmentVariableDialog(QDialog):
    def __init__(self, parent):
        super(EnvironmentVariableDialog, self).__init__(parent)

        self.setWindowTitle('Environment Variable')

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

        super(EnvironmentVariableDialog, self).accept()

    def setVariable(self, key, value):
        self.uiKeyTXT.setText(str(key))
        self.uiValueTXT.setText(str(value))

    def variable(self):
        return (self.uiKeyTXT.text(), self.uiValueTXT.text())


class EnvironmentConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # update the header items
        header = self.uiSystemTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.ResizeToContents)

        header = self.uiEditorTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.ResizeToContents)

        # create icons
        self.uiAddBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self.uiEditBTN.setIcon(QIcon(blurdev.resourcePath('img/edit.png')))
        self.uiRemoveBTN.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))

        # create connections
        self.uiAddBTN.clicked.connect(self.createVariable)
        self.uiEditBTN.clicked.connect(self.editVariable)
        self.uiRemoveBTN.clicked.connect(self.removeVariable)

    def createVariable(self):
        """prompts the user to create a new variable"""
        dlg = EnvironmentVariableDialog(self)
        if dlg.exec_():
            self.uiEditorTREE.addTopLevelItem(QTreeWidgetItem(dlg.variable()))

    def editVariable(self):
        """edits the current variable"""
        item = self.uiEditorTREE.currentItem()
        if not item:
            return False

        dlg = EnvironmentVariableDialog(self)
        dlg.setVariable(item.text(0), item.text(1))
        if dlg.exec_():
            key, value = dlg.variable()
            item.setText(0, key)
            item.setText(1, value)

    def recordUi(self):
        """records the latest ui settings to the data"""
        section = self.section()

        # record section values
        data = {}
        for i in range(self.uiEditorTREE.topLevelItemCount()):
            item = self.uiEditorTREE.topLevelItem(i)
            data[str(item.text(0))] = str(item.text(1))

        section.setValue('variables', data)

    def refreshUi(self):
        """refreshes the ui with the latest data settings"""
        section = self.section()

        # load system environment variables
        keys = sorted(settings.startup_environ.keys())

        self.uiSystemTREE.clear()
        for key in keys:
            self.uiSystemTREE.addTopLevelItem(
                QTreeWidgetItem([key, settings.startup_environ[key]])
            )

        # load editor environment variables
        vars = section.value('variables')
        keys = sorted(vars.keys())

        self.uiEditorTREE.clear()
        for key in keys:
            self.uiEditorTREE.addTopLevelItem(QTreeWidgetItem([key, vars[key]]))

    def removeVariable(self):
        item = self.uiEditorTREE.currentItem()

        if (
            item
            and QMessageBox.question(
                self,
                'Remove Variable',
                'Are you sure you want to remove this key/value?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.uiEditorTREE.takeTopLevelItem(
                self.uiEditorTREE.indexOfTopLevelItem(item)
            )


def registerSections(configSet):
    """Registers one or many new sections to the config system

    Args:
        configSet (blurdev.gui.dialogs.configdialog.ConfigSet):
    """

    # define section
    group = 'Editor'
    section = 'Environment'
    icon = blurdev.relativePath(__file__, 'img/environmentconfig.png')
    cls = EnvironmentConfig
    params = {'variables': {}}

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
