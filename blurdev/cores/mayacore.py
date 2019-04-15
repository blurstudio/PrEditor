import os
import sys
from Qt import QtCompat
from Qt.QtCore import Qt
from Qt.QtWidgets import QApplication, QMainWindow
import maya.cmds
import maya.OpenMayaUI as mui

import blurdev.tools.tool
from blurdev.cores.core import Core


class MayaCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Maya sessions
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

    def addLibraryPaths(self, app):
        # Do not add default library paths
        pass

    @property
    def headless(self):
        """ If true, no Qt gui elements should be used because python is running a QCoreApplication. """
        return 'mayabatch' in os.path.basename(sys.executable).lower()

    def lovebar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        from blurdev.tools.toolslovebar import ToolsLoveBar

        hasInstance = ToolsLoveBar._instance != None
        lovebar = ToolsLoveBar.instance(parent)
        if not hasInstance and isinstance(parent, QMainWindow):
            parent.addToolBar(Qt.RightToolBarArea, lovebar)
        return lovebar

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the MayaCore has shutdown called
        """
        return False

    def recordToolbarXML(self, pref):
        from blurdev.tools.toolstoolbar import ToolsToolBar

        if ToolsToolBar._instance:
            toolbar = ToolsToolBar._instance
            toolbar.toXml(pref.root())
            child = pref.root().addNode('toolbardialog')
            child.setAttribute('visible', toolbar.isVisible())

    def restoreToolbars(self):
        super(MayaCore, self).restoreToolbars()
        # Restore the toolbar positions if they are visible
        maya.cmds.windowPref(restoreMainWindowState="startupMainWindowState")

    def showLovebar(self, parent=None):
        self.lovebar(parent=parent).show()

    def showToolbar(self, parent=None):
        self.toolbar(parent=parent).show()

    def rootWindow(self):
        """
        Override of core rootWindow function; uses Maya's main window pointer
        to derive rootWindow due to cases where plugins end up as root.
        """
        pointer = long(mui.MQtUtil.mainWindow())
        self._rootWindow = QtCompat.wrapInstance(pointer)
        return self._rootWindow

    def shutdownToolbars(self):
        """ Closes the toolbars and save their prefs if they are used
        
        This is abstracted from shutdown, so specific cores can control how they shutdown
        """
        from blurdev.tools.toolstoolbar import ToolsToolBar
        from blurdev.tools.toolslovebar import ToolsLoveBar

        ToolsToolBar.instanceShutdown()
        ToolsLoveBar.instanceShutdown()

    def shutdown(self):
        # We are using a autorun.bat script to create 30+ doskey aliases. When Maya is shutting
        # down it makes serveral system calls. For some reason in this environment doskey
        # errors out or just takes a long time to run. We don't need these aliases. The batch
        # script will skip the doskey calls if this environment variable is not a empty string.
        varName = 'BDEV_DISABLE_AUTORUN'
        if os.getenv(varName) is None:
            os.environ[varName] = 'true'

        super(MayaCore, self).shutdown()

    def toolbar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        from blurdev.tools.toolstoolbar import ToolsToolBar

        hasInstance = ToolsToolBar._instance != None
        toolbar = ToolsToolBar.instance(parent)
        if not hasInstance and isinstance(parent, QMainWindow):
            parent.addToolBar(Qt.RightToolBarArea, toolbar)
        return toolbar

    def toolTypes(self):
        """
        Method to determine what types of tools that the treegrunt system should be looking at
        """
        output = blurdev.tools.tool.ToolType.Maya
        return output
