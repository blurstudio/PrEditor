import re
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core
from PyQt4.QtGui import QApplication


class RVCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Fusion sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'rv'
        super(RVCore, self).__init__(*args, **kargs)
        # TODO: Shutdown blurdev when RV closes

    # 		if QApplication.instance():
    # 			QApplication.instance().aboutToQuit.connect(self.shutdown)

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Fusion application for the inputed Core tool. Not Supported currently.
        """
        return False

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the RVCore has shutdown called
        """
        return False

    def refreshStyleSheet(self):
        """ Reloading stylesheets in RV breaks the interface. """
        # For now, modifying the stylesheet causes undesireable side affects to the RV interface
        # don't modify the stylesheet with blurdev.
        pass

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """ Accepts the name of a stylesheet included with blurdev, or a full
            path to any stylesheet.  If given None, it will remove the 
            stylesheet.
        """
        # For now, modifying the stylesheet causes undesireable side affects to the RV interface
        # don't modify the stylesheet with blurdev.
        return

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Fusion applications
        """
        return blurdev.tools.tool.ToolType.RV
