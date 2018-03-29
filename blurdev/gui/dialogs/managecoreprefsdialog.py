##
#   :namespace  managecoreprefsdialog
#
#   :remarks    This tool allows you to modify the treegrunt environment loaded for any blurdev core.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       12/07/17
#


import os
import glob
import blurdev

from Qt.QtCore import QRect, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QTreeWidgetItem, QComboBox, QInputDialog

# we import from blurdev.gui vs. QtGui becuase there are some additional management features for running the Dialog in multiple environments
from blurdev.gui import Dialog


class ManageCorePrefsDialog(Dialog):
    def __init__(self, parent=None):
        super(ManageCorePrefsDialog, self).__init__(parent)
        # load the ui
        blurdev.gui.loadUi(__file__, self)
        self.setWindowIcon(QIcon(blurdev.resourcePath('img/treegruntedit.png')))
        self.uiRefreshBTN.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))
        self.uiAddCoreBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self._envNames = []
        self.uiEnvironmentTREE.setDelegate(self)

        # restore settings from last session
        self.restoreSettings()
        self.refresh()

    def addCore(self):
        label = 'Use this to add a corename that does not currently exist. Use lowercase, no special characters or spaces. No validity checks are made.'
        corename, success = QInputDialog.getText(self, 'Type Core Name', label)
        if success:
            default = blurdev.activeEnvironment().defaultEnvironment().objectName()
            blurdev.setActiveEnvironment(default, corename)
            self.refresh()

    def closeEvent(self, event):
        self.recordSettings()
        super(ManageCorePrefsDialog, self).closeEvent(event)

    def createEditor(self, parent, option, index, tree=None):
        if index.column() == 1:
            editor = QComboBox(parent)
            editor.addItems(self._envNames)
            editor.setCurrentIndex(editor.findText(index.data(Qt.DisplayRole)))
            return editor
        return None

    def corenames(self):
        """ Returns a list of all corename folders in the prefs system.

        Checks the filesystem for blurdev corename prefs folders.

        Returns:
            list: A list of all corename folders that exist
        """
        ret = []
        basepath = os.path.dirname(blurdev.prefs.Preference.path())
        for path in sorted(glob.glob(os.path.join(basepath, 'app_*'))):
            ret.append(os.path.basename(path).replace('app_', ''))
        return ret

    def refresh(self):
        # Rebuild the environment tree
        self.uiEnvironmentTREE.clear()
        for corename in self.corenames():
            # Don't show the current corename to avoid confusion with the environment
            # Not being updated as expected.
            if corename != blurdev.core.objectName():
                activeEnv = blurdev.activeEnvironment(corename)
                if not activeEnv.isEmpty():
                    item = QTreeWidgetItem(
                        self.uiEnvironmentTREE, [corename, activeEnv.objectName()]
                    )
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.uiEnvironmentTREE.resizeColumnsToContents()

        # rebuild the setAll drop down and reset the env name cache
        selected = self.uiSetAllDDL.currentText()
        self.uiSetAllDDL.clear()
        self._envNames = [
            env.objectName() for env in blurdev.tools.ToolsEnvironment.environments
        ]
        self.uiSetAllDDL.addItems(self._envNames)
        self.uiSetAllDDL.setCurrentIndex(self.uiSetAllDDL.findText(selected))

    def setAll(self):
        """ Sets all corenames to the selected environment and refreshes.
        """
        envName = self.uiSetAllDDL.currentText()
        for corename in self.corenames():
            blurdev.setActiveEnvironment(envName, corename)
        self.refresh()

    def setEditorData(self, editor, index, tree=None):
        if isinstance(editor, QComboBox):
            editor.showPopup()

    def recordSettings(self):
        """ records settings to be used for another session
        """
        from blurdev import prefs

        pref = prefs.find('blurdev/managecoreprefsdialog')

        # record the geometry
        pref.recordProperty('geom', self.geometry())
        # save the settings
        pref.save()

    def restoreSettings(self):
        """ restores settings that were saved by a previous session
        """
        from blurdev import prefs

        pref = prefs.find('blurdev/managecoreprefsdialog')

        # reload the geometry
        geom = pref.restoreProperty('geom', QRect())
        if geom and not geom.isNull():
            self.setGeometry(geom)

    def setModelData(self, editor, model, index, tree=None):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText())
            item = self.uiEnvironmentTREE.itemFromIndex(index)
            item.setText(1, editor.currentText())
            blurdev.setActiveEnvironment(editor.currentText(), item.text(0))
