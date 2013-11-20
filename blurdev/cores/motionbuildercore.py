from PyQt4.QtGui import QApplication
import pyfbsdk

import blurdev.tools.tool
from blurdev.cores.core import Core


class MotionBuilderCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Studiomax sessions
    """

    def __init__(self):
        Core.__init__(self)
        self.setObjectName('motionbuilder')

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

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def toolTypes(self):
        """
        Method to determine what types of tools that the trax system should be looking at
        """
        output = blurdev.tools.tool.ToolType.MotionBuilder
        return output
