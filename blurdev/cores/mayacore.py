import os
import sys
from Qt import QtCompat
from Qt.QtWidgets import QApplication
import maya.cmds
from maya import OpenMayaUI

import blurdev.tools.tool
from blurdev.cores.core import Core
from builtins import int


class MayaCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Maya sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'maya'
        self._supportsDocking = True
        super(MayaCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Maya closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self):
        # Do not add default library paths
        pass

    def errorCoreText(self):
        """ Returns text that is included in the error email for the active core.
        If a empty string is returned this line will not be shown in the error email.
        """
        path = maya.cmds.file(query=True, sceneName=True)
        if not path:
            # No idea why but the previous command sometimes fails
            # So let's double check that
            path = maya.cmds.file(query=True, list=True)[0]
            if path.endswith("/untitled"):
                return ''

        return '<i>Open File:</i> %s' % os.path.normpath(path)

    @property
    def headless(self):
        """ If true, no Qt gui elements should be used because python is running a
        QCoreApplication. """
        return 'mayabatch' in os.path.basename(sys.executable).lower()

    def init(self):
        """ Initializes the core system
        """
        ret = super(MayaCore, self).init()
        self.initGui()
        return ret

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the MayaCore has shutdown called
        """
        return False

    def restoreToolbars(self):
        super(MayaCore, self).restoreToolbars()
        # Restore the toolbar positions if they are visible
        maya.cmds.windowPref(restoreMainWindowState="startupMainWindowState")

    def rootWindow(self):
        """
        Override of core rootWindow function; uses Maya's main window pointer
        to derive rootWindow due to cases where plugins end up as root.
        """
        pointer = int(OpenMayaUI.MQtUtil.mainWindow())
        self._rootWindow = QtCompat.wrapInstance(pointer)
        return self._rootWindow

    def shutdown(self):
        # We are using a autorun.bat script to create 30+ doskey aliases. When Maya is
        # shutting down it makes serveral system calls. For some reason in this
        # environment doskey errors out or just takes a long time to run. We don't need
        # these aliases. The batch script will skip the doskey calls if this environment
        # variable is not a empty string.
        varName = 'BDEV_DISABLE_AUTORUN'
        if os.getenv(varName) is None:
            os.environ[varName] = 'true'

        super(MayaCore, self).shutdown()

    def toolTypes(self):
        """
        Method to determine what types of tools that the treegrunt system should be
        looking at
        """
        output = blurdev.tools.tool.ToolType.Maya
        return output
