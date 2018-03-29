##
#   :namespace  python.blurdev.ide.addons.savelog
#
#   :remarks    Creates a log file of what files were saved when.
#
#   :author     [author::email]
#   :author     [author::company]
#   :date       08/12/14
#

import os
import logging
import blurdev
from blurdev import prefs
from blurdev.ide.ideaddon import IdeAddon
from logging.handlers import RotatingFileHandler


class SaveLogAddon(IdeAddon):
    def activate(self, ide):
        self.ide = ide
        # add the menu actions
        self.uiSeparator = ide.uiToolsMENU.addSeparator()
        self.uiSaveLogMENU = ide.uiToolsMENU.addMenu('Save Log')
        self.uiEnabledACT = self.uiSaveLogMENU.addAction('Enabled')
        self.uiEnabledACT.setCheckable(True)
        self.uiEnabledACT.toggled.connect(self.setEnabled)
        self.uiSaveLogMENU.addSeparator()
        act = self.uiSaveLogMENU.addAction('View Log File')
        act.triggered.connect(self.viewLogFile)
        act = self.uiSaveLogMENU.addAction('Browse Log File')
        act.triggered.connect(self.browseLogFile)
        self.uiSaveLogMENU.addSeparator()
        act = self.uiSaveLogMENU.addAction('Change Log File...')
        act.triggered.connect(self.editLogFile)
        # restoreSettings must be called to create class variables
        self.restoreSettings()
        self.createLogger()
        for document in ide.documents():
            document.documentSaved.connect(self.documentSaved)
        ide.editorCreated.connect(self.editorCreated)
        ide.settingsRecorded.connect(self.recordSettings)
        ide.ideClosing.connect(self.ideIsClosing)

    def deactivate(self, ide):
        for document in ide.documents():
            document.documentSaved.disconnect(self.documentSaved)
        ide.editorCreated.disconnect(self.editorCreated)
        # remove the menu actions
        ide.uiToolsMENU.removeAction(self.uiSeparator)
        ide.uiToolsMENU.removeAction(self.uiSaveLogMENU.menuAction())
        # Document that the plugin was deactivated.
        if self.enabled:
            self.logger.info(
                '--- SaveLogAddon deactivated Pid: {} ---'.format(os.getpid())
            )
        return True

    def browseLogFile(self):
        blurdev.osystem.explore(self.logFile)

    def createLogger(self):
        logDir = os.path.split(self.logFile)[0]
        logName = os.path.basename(self.logFile)
        loggingName, ext = os.path.splitext(logName)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        loggingFormat = '%(asctime)s :: %(message)s'
        logLevel = logging.INFO
        logging.basicConfig(format=loggingFormat, level=logLevel)
        self.logger = logging.getLogger(loggingName)
        self.logger.setLevel(logLevel)
        handler = RotatingFileHandler(
            os.path.join(logDir, loggingName + ext), maxBytes=999999, backupCount=99
        )
        handler.setLevel(logLevel)
        formatter = logging.Formatter(loggingFormat)
        handler.setFormatter(formatter)
        for h in self.logger.handlers:
            h.setFormatter(formatter)
        self.logger.addHandler(handler)
        # Document that the plugin was created.
        if self.enabled:
            self.logger.info(
                '--- SaveLogAddon activated   Pid: {} ---'.format(os.getpid())
            )

    def documentSaved(self, document, filename):
        if self.enabled:
            self.logger.info(filename)

    def editorCreated(self, editor):
        editor.documentSaved.connect(self.documentSaved)

    def editLogFile(self):
        import savelogdialog

        dlg = savelogdialog.SaveLogDialog(self.ide)
        if dlg.exec_():
            self.restoreSettings()

    def ideIsClosing(self):
        # Document that the plugin was deactivated.
        if self.enabled:
            self.logger.info(
                '--- SaveLogAddon IDE Closed  Pid: {} ---'.format(os.getpid())
            )

    def recordSettings(self):
        pref = prefs.find('ide/addons/savelog', coreName='blurdev', reload=True)
        pref.recordProperty('logFile', self.logFile)
        pref.recordProperty('enabled', self.enabled)
        pref.save()

    def restoreSettings(self):
        pref = prefs.find('ide/addons/savelog', coreName='blurdev', reload=True)
        self.logFile = pref.restoreProperty('logFile', r'c:\temp\BlurIDESaveLog.log')
        self.enabled = pref.restoreProperty('enabled', False)
        self.uiEnabledACT.setChecked(self.enabled)

    def setEnabled(self, state):
        self.enabled = state
        self.recordSettings()

    def viewLogFile(self):
        self.ide.load(self.logFile)


# register the addon to the system
IdeAddon.register('Save Log', SaveLogAddon)

# create the init method (in case this addon doesn't get registered as part of a group)
def init():
    pass
