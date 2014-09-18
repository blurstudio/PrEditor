from PyQt4.QtGui import QApplication
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

    # 	def addLibraryPaths(self, app):
    # 		# Do not add default library paths
    # 		pass

    # 	def activeWindow(self):
    # 		"""
    # 		Make sure the root Maya window is used, or it won't parent properly
    # 		"""
    # 		window = None
    # 		if QApplication.instance():
    # 			window = QApplication.instance().activeWindow()
    # 			while window.parent():
    # 				window = window.parent()
    # 		return window

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
        output = blurdev.tools.tool.ToolType.Maya
        return output
