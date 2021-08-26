from __future__ import absolute_import
import sys
import os
import blurdev
import blurdev.tools.tool

# This import mari may have been used to check if we are inside Mari.
# If its not importable it will not init the MariCore.
import mari  # noqa: F401

from blurdev.cores.core import Core
from Qt.QtWidgets import QApplication


class MariCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Mari sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'mari'
        super(MariCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Mari closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self):
        if sys.platform != 'win32':
            return
        path = os.path.split(sys.executable)[0]
        path = os.path.join(path, '..', 'Qt4')
        if os.path.exists(os.path.join(path, 'QtOpenGL4.dll')):
            # Special case for if max has our pyqt installed inside it
            paths = QApplication.libraryPaths()
            paths.append(u'C:/Program Files/Mari3.1v3/Bundle/Qt4')
            QApplication.setLibraryPaths(paths)

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the MariCore has shutdown called
        """
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override
        in subclasses to provide extra data. If a empty string is returned this line
        will not be shown in the error email.
        """
        # Mari does not have a scene file that can be used like most other applications.
        return ''

    def eventFilter(self, obj, event):
        if event.type() == event.Close and obj == self.rootWindow():
            # Because blurdev.core.shutdown() is triggered after the window has already
            # been destroyed, we need to capture the close event and shutdown the
            # toolbars here in order to successfully save preferences for them.
            self.shutdownToolbars()
        return super(MariCore, self).eventFilter(obj, event)

    def macroNames(self):
        """ Returns True if the current blurdev core create a tool macro.
        """
        # Blurdev can not currently make a macro for this DCC.
        return tuple()

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are
        related to Mari applications
        """
        output = blurdev.tools.tool.ToolType.Mari
        return output
