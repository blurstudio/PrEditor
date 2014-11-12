from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QMainWindow
import maya.cmds

import blurdev.tools.tool
from blurdev.cores.core import Core


class MayaCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Maya sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'maya'
        super(MayaCore, self).__init__(*args, **kargs)
        # Shutdown blurdev when Maya closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self, app):
        # Do not add default library paths
        pass

    def lovebar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        hasInstance = blurdev.tools.toolslovebar.ToolsLoveBar._instance != None
        lovebar = blurdev.tools.toolslovebar.ToolsLoveBar.instance(parent)
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

    def restoreToolbars(self):
        super(MayaCore, self).restoreToolbars()
        # Restore the toolbar positions if they are visible
        maya.cmds.windowPref(restoreMainWindowState="startupMainWindowState")

    def showLovebar(self, parent=None):
        self.lovebar(parent=parent).show()

    def shutdownToolbars(self):
        """ Closes the toolbars and save their prefs if they are used
        
        This is abstracted from shutdown, so specific cores can control how they shutdown
        """
        blurdev.tools.toolstoolbar.ToolsToolBarDialog.instanceShutdown()
        blurdev.tools.toolslovebar.ToolsLoveBar.instanceShutdown()

    def toolTypes(self):
        """
        Method to determine what types of tools that the treegrunt system should be looking at
        """
        output = blurdev.tools.tool.ToolType.Maya
        return output
