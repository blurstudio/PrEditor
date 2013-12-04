import os
import platform

# to be in a Softimage session, we need to be able to import the PySoftimage package
from PyQt4.QtGui import QApplication, QCursor
import win32com.client
from win32com.client import constants

xsi = win32com.client.Dispatch('XSI.Application').Application

from blurdev.cores.core import Core
import blurdev.tools.toolsenvironment
import blurdev.tools.tool


SOFTIMAGE_MACRO_TEMPLATE = """
import win32com.client
from win32com.client import constants

def XSILoadPlugin( in_reg ):
    in_reg.Author = "%(author)s"
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
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Softimage sessions
    """

    def __init__(self):
        Core.__init__(self)
        self.setObjectName('softimage')

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        
        """
        return '<i>Open File:</i> %s' % xsi.ActiveProject.ActiveScene.FileName.Value

    def isKeystrokesEnabled(self):
        disabled = False
        if QApplication.instance().focusWidget():
            window = QApplication.instance().focusWidget().window()
            geom = window.geometry()
            disabled = geom.contains(QCursor.pos())
        return not disabled

    def init(self):
        # BlurApplication is used to connect QApplication to Softimage
        if platform.architecture()[0] == '64bit':
            plugin = blurdev.resourcePath('softimage\BlurApplication64.dll')
        else:
            plugin = blurdev.resourcePath('softimage\BlurApplication.dll')
        xsi.loadPlugin(plugin)
        # connect the plugin to Softimage
        self.connectPlugin(xsi.GetPluginInstance(), xsi.GetWindowHandle())
        self.protectModule('PySoftimage')
        # load this file as a plugin for XSI
        xsi.LoadPlugin(__file__)
        # init the base class
        return Core.init(self)

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Studiomax applications
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.Softimage | ToolType.LegacySoftimage
        return output

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a command plugin for the
        Softimage application for the inputed Core tool
        """
        # create the options for the tool macro to run
        options = {
            'tool': tool.objectName(),
            'displayName': os.environ.get('bdev_studio_name', '')
            + 'TG_'
            + tool.displayName().replace(' ', '_'),
            'macro': macro,
            'tooltip': tool.displayName(),
            'id': str(tool.displayName()).replace(' ', '_').replace('::', '_'),
            'author': os.environ.get('bdev_default_author_email'),
        }

        # create the macroscript
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
