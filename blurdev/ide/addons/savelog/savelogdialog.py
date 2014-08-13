import blurdev.gui
from blurdev import prefs


class SaveLogDialog(blurdev.gui.Dialog):
    def __init__(self, parent=None):
        super(SaveLogDialog, self).__init__(parent)
        blurdev.gui.loadUi(__file__, self)
        self.restoreSettings()

    def accept(self):
        self.recordSettings()
        return super(SaveLogDialog, self).accept()

    def recordSettings(self):
        pref = prefs.find('ide/addons/savelog', coreName='blurdev', reload=True)
        pref.recordProperty('logFile', self.uiLogFileWGT.filePath())
        pref.recordProperty('enabled', self.uiEnabledGRP.isChecked())
        pref.save()

    def restoreSettings(self):
        pref = prefs.find('ide/addons/savelog', coreName='blurdev', reload=True)
        self.uiLogFileWGT.setFilePath(
            pref.restoreProperty('logFile', r'c:\temp\BlurIDESaveLog.log')
        )
        self.uiEnabledGRP.setChecked(pref.restoreProperty('enabled', False))
        self.uiLogFileWGT.setEnabled(self.uiEnabledGRP.isChecked())
