import re
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core
import hou
from Qt.QtWidgets import QApplication, QMainWindow
from Qt.QtCore import Qt


class HoudiniCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Houdini sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'houdini'
        super(HoudiniCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Houdini closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self, app):
        """ There is no need to add library paths for houdini """
        return

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Houdini application for the inputed Core tool. Not Supported currently.
        """
        return False

    @property
    def headless(self):
        """ If true, no Qt gui elements should be used because python is running a QCoreApplication. """
        return not hou.isUIAvailable()

    def shouldReportException(self, exc_type, exc_value, exc_traceback):
        """
        Allow core to control how exceptions are handled. Currently being used
        by `BlurExcepthook`, informing which excepthooks should or should not
        be executed.

        Note: We override this method to ignore a `RuntimeError`-Exception
            raised when the user closes an open file dialog box without a
            selection.

        Args:
            exc_type (type): exception type class object
            exc_value (Exception): class instance of exception parameter
            exc_traceback (traceback): encapsulation of call stack for exception

        Returns:
            dict: booleon values representing whether to perform excepthook
                action, keyed to the name of the excepthook
        """
        if isinstance(exc_value, RuntimeError) and exc_value.message == "Cancelled":
            return dict(email=False, prompt=False, sentry=False)

        return super(HoudiniCore, self).shouldReportException(
            exc_type, exc_value, exc_traceback
        )

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the HoudiniCore has shutdown called
        """
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        """
        try:
            return '<i>Open File:</i> %s' % hou.hipFile.name()
        except RuntimeError:
            return ''

    def lovebar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        from blurdev.tools.toolslovebar import ToolsLoveBar

        hasInstance = ToolsLoveBar._instance != None
        lovebar = ToolsLoveBar.instance(parent)
        if not hasInstance and isinstance(parent, QMainWindow):
            parent.addToolBar(Qt.TopToolBarArea, lovebar)
        return lovebar

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Add to Lovebar...'

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Houdini applications
        """
        output = blurdev.tools.tool.ToolType.Houdini
        return output

    def recordToolbarXML(self, pref):
        from blurdev.tools.toolstoolbar import ToolsToolBar

        if ToolsToolBar._instance:
            toolbar = ToolsToolBar._instance
            toolbar.toXml(pref.root())
            child = pref.root().addNode('toolbardialog')
            child.setAttribute('visible', toolbar.isVisible())

    def restoreToolbars(self):
        super(HoudiniCore, self).restoreToolbars()
        # Restore the toolbar positions if they are visible
        # maya.cmds.windowPref(restoreMainWindowState="startupMainWindowState")

    def showLovebar(self, parent=None):
        self.lovebar(parent=parent).show()

    def showToolbar(self, parent=None):
        self.toolbar(parent=parent).show()

    def shutdownToolbars(self):
        """ Closes the toolbars and save their prefs if they are used
        
        This is abstracted from shutdown, so specific cores can control how they shutdown
        """
        from blurdev.tools.toolstoolbar import ToolsToolBar
        from blurdev.tools.toolslovebar import ToolsLoveBar

        ToolsToolBar.instanceShutdown()
        ToolsLoveBar.instanceShutdown()

    def toolbar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        from blurdev.tools.toolstoolbar import ToolsToolBar

        hasInstance = ToolsToolBar._instance != None
        toolbar = ToolsToolBar.instance(parent)
        if not hasInstance and isinstance(parent, QMainWindow):
            parent.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar
