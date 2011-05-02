##
# 	\namespace	blurdev.cores.softimagecore
#
# 	\remarks	This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Softimage sessions
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/12/10
#

# to be in a 3dsmax session, we need to be able to import the Py3dsMax package
import PySoftimage
from blurdev.cores.core import Core

# -------------------------------------------------------------------------------------------------------------

SOFTIMAGE_MACRO_TEMPLATE = """
import win32com.client
from win32com.client import constants

def XSILoadPlugin( in_reg ):
    in_reg.Author = "beta@blur.com"
    in_reg.Name = "%(displayName)s"
    in_reg.Major = 1
    in_reg.Minor = 0
    in_reg.RegisterCommand("%(displayName)s","%(displayName)s")
    return True

def %(displayName)s_Init( in_ctxt ):
    oCmd = in_ctxt.Source
    oCmd.Description = "%(tooltip)s"
    oCmd.ReturnValue = False
    return True

def %(displayName)s_Execute(  ):
    import blurdev
    blurdev.runTool( "%(tool)s", "%(macro)s" )
"""


class SoftimageCore(Core):
    def __init__(self):
        Core.__init__(self)
        self.setObjectName('softimage')

    def isKeystrokesEnabled(self):
        from PyQt4.QtGui import QApplication, QCursor

        disabled = False
        if QApplication.instance().focusWidget():
            window = QApplication.instance().focusWidget().window()
            geom = window.geometry()
            disabled = geom.contains(QCursor.pos())

        return not disabled

    def init(self):
        # connect the plugin to 3dsmax
        from PySoftimage import xsi

        self.connectPlugin(xsi.GetPluginInstance(), xsi.GetWindowHandle())

        self.protectModule('PySoftimage')

        # load this file as a plugin for XSI
        xsi.LoadPlugin(__file__)

        # init the base class
        return Core.init(self)

    def toolTypes(self):
        """
            \remarks	Overloads the toolTypes method from the Core class to show tool types that are related to
                        Studiomax applications
                        
            \return		<blurdev.tools.ToolType>
        """
        from blurdev.tools import ToolsEnvironment, ToolType

        output = ToolType.Softimage | ToolType.LegacySoftimage

        return output

    def createToolMacro(self, tool, macro=''):
        """
            \remarks	Overloads the createToolMacro virtual method from the Core class, this will create a command plugin for the
                        Softimage application for the inputed Core tool
            
            \return		<bool> success
        """
        import win32com.client
        from win32com.client import constants

        # create the options for the tool macro to run
        options = {
            'tool': tool.objectName(),
            'displayName': tool.displayName(),
            'macro': macro,
            'tooltip': tool.displayName(),
            'id': str(tool.displayName()).replace(' ', '_').replace('::', '_'),
        }

        # create the macroscript
        from PySoftimage import xsi

        import os

        pluginsPath = os.path.join(
            xsi.GetInstallationPath2(constants.siUserPath), 'Application', 'Plugins'
        )
        filename = os.path.join(pluginsPath, options['displayName'] + '.py')
        f = open(filename, 'w')
        f.write(SOFTIMAGE_MACRO_TEMPLATE % options)
        f.close()

        # reloading softimage plugins
        xsi.UpdatePlugins()

        return True
