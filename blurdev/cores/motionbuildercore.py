import os
import sys
from Qt.QtWidgets import QApplication
import pyfbsdk

import blurdev.tools.tool
from blurdev.cores.core import Core

# >>> os.path.abspath(os.curdir)
# C:\Program Files\Autodesk\MotionBuilder 2014
# Because the python working directory is the root of the motion builder install
# we have to explicitly add the qt dll paths so any dll's that were not loaded by
# qt itself are properly found when loaded later when they are dynamically loaded.
x64dir = os.path.dirname(sys.executable)
os.environ['path'] = ';'.join((x64dir, os.environ.get('path', '')))


class MotionBuilderCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Studiomax sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'motionbuilder'
        super(MotionBuilderCore, self).__init__(*args, **kargs)
        # The Qt dlls in the motion builder directory cause problems for other dcc's
        # so, we need to remove the directory from the PATH environment variable.
        # See blurdev.osystem.subprocessEnvironment() for more details.
        self._removeFromPATHEnv.add(x64dir)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Motion builder closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def activeWindow(self):
        """
        Make sure the root motion builder window is used, or it won't parent properly
        """
        window = None
        if QApplication.instance():
            window = QApplication.instance().activeWindow()
            while window.parent():
                window = window.parent()
        return window

    def addLibraryPaths(self, app):
        """ There is no need to add library paths for motion builder """
        return

    def createSystemMenu(self):
        """
        Builds our menu for motion builder to launch treegrunt, logger, etc.
        """

        def eventMenu(control, event):
            name = event.Name
            import blurdev

            if name == "Treegrunt":
                blurdev.core.showTreegrunt()
            elif name == "Show Logger...":
                blurdev.core.showLogger()
            elif name == "Show Toolbar...":
                blurdev.core.showToolbar()
            elif name == "Show Lovebar...":
                blurdev.core.showLovebar()

        mgr = pyfbsdk.FBMenuManager()
        blurMenu = mgr.GetMenu('Blur')
        if blurMenu:
            # remove all menus
            item = blurMenu.GetFirstItem()
            while item:
                blurMenu.DeleteItem(item)
                item = blurMenu.GetFirstItem()
        else:
            # create the menu
            blurMenu = mgr.InsertBefore(None, 'Help', 'Blur').Menu
        blurMenu.OnMenuActivate.Add(eventMenu)
        mgr.InsertLast('Blur', 'Treegrunt')
        # -------
        mgr.InsertLast('Blur', '')  # Seperator
        mgr.InsertLast('Blur', 'Show Logger...')
        # -------
        mgr.InsertLast('Blur', '')  # Seperator
        mgr.InsertLast('Blur', 'Show Toolbar...')
        mgr.InsertLast('Blur', 'Show Lovebar...')

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the MayaCore has shutdown called
        """
        return False

    def toolTypes(self):
        """
        Method to determine what types of tools that the treegrunt system should be looking at
        """
        output = blurdev.tools.tool.ToolType.MotionBuilder
        return output
