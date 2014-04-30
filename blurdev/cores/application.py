from PyQt4.QtGui import QApplication
from PyQt4.QtCore import pyqtSignal, QCoreApplication


class CoreApplication(QCoreApplication):
    # Does not get called, but exists incase a script tries to connect to it.
    sessionEnding = pyqtSignal()


class Application(QApplication):
    sessionEnding = pyqtSignal()

    def __init__(self, args):
        super(Application, self).__init__(args)

    def commitData(self, sessionManager):
        self.sessionEnding.emit()  # allows an application hiding in the background to properly exit on session end
        super(Application, self).commitData(sessionManager)
