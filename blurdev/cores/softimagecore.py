import os
import sys

# to be in a Softimage session, we need to be able to import the PySoftimage package
from Qt.QtCore import QRect
from Qt.QtWidgets import QWidget
import win32gui
import win32com.client
from win32com.client import constants

xsi = win32com.client.Dispatch('XSI.Application').Application

from blurdev.cores.core import Core
import blurdev
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
    in_reg.RegisterCommand("%(displayName)s","%(commandName)s")
    return True

def %(commandName)s_Init( in_ctxt ):
    oCmd = in_ctxt.Source
    oCmd.Description = "%(tooltip)s"
    oCmd.ReturnValue = False
    return True

def %(commandName)s_Execute(  ):
    import blurdev
    blurdev.runTool( "%(toolName)s", "%(macro)s" )
"""


class SoftimageCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Softimage sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'softimage'
        Core.__init__(self, *args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        
        """
        return '<i>Open File:</i> %s' % xsi.ActiveProject.ActiveScene.FileName.Value

    @property
    def headless(self):
        """ If true, no Qt gui elements should be used because python is running a QCoreApplication. """
        ret = 'xsibatch.exe' in sys.executable.lower()
        return ret

    def isKeystrokesEnabled(self):
        # Checks all of the top level windows of Qt against the win32 forground window id to see if qt has focus
        handle = win32gui.GetForegroundWindow()
        if QWidget.find(handle):
            return False
        return True

    def init(self):
        # BlurApplication is used to connect QApplication to Softimage
        if blurdev.osystem.getPointerSize() == 64:
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

    def mainWindowGeometry(self):
        if self.headless:
            raise Exception('You are showing a gui in a headless environment. STOP IT!')
        x, y, w, h = win32gui.GetWindowRect(xsi.GetWindowHandle())
        return QRect(0, 0, w - x, h - y)

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

        # The command name and display name need to the same at the exception of spaces.
        # TODO: Sanitize the display name in order to remove any potential characters that will not translate well to a command name.
        displayName = tool.displayName().replace('_', ' ')
        commandName = displayName.replace(' ', '')

        # create the options for the tool macro to run
        options = {
            'toolName': tool.objectName(),
            'displayName': displayName,
            'commandName': commandName,
            'macro': macro,
            'tooltip': tool.displayName(),
            'author': 'Blur Studio',
        }

        # create the macroscript
        pluginsPath = os.path.join(
            xsi.GetInstallationPath2(constants.siUserPath), 'Application', 'Plugins'
        )
        filename = os.path.join(pluginsPath, tool.objectName().split(':')[-1] + '.py')
        f = open(filename, 'w')
        f.write(SOFTIMAGE_MACRO_TEMPLATE % options)
        f.close()

        # reloading softimage plugins
        xsi.UpdatePlugins()
        return True
