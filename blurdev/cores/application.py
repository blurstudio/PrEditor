from __future__ import absolute_import
import sys
import Qt
from Qt.QtWidgets import QApplication
from Qt.QtCore import QCoreApplication, Signal


class CoreApplication(QCoreApplication):
    # Does not get called, but exists in case a script tries to connect to it.
    sessionEnding = Signal()


class Application(QApplication):
    sessionEnding = Signal()

    def __init__(self, args):
        if sys.platform == 'win32' and Qt.IsPyQt5:
            # Make Qt automatically scale based on the monitor the window is
            # currently located.
            args.extend(["--platform", "windows:dpiawareness=0"])
        super(Application, self).__init__(args)

    def commitData(self, sessionManager):
        # allows an application hiding in the background to properly exit on session end
        self.sessionEnding.emit()
        super(Application, self).commitData(sessionManager)
