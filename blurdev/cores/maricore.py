import sys
import re
import os
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core
import mari
from Qt.QtWidgets import QApplication, QMainWindow
from Qt.QtCore import Qt


class MariCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Mari sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'mari'
        super(MariCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Mari closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self, app):
        if sys.platform != 'win32':
            return
        path = os.path.split(sys.executable)[0]
        path = os.path.join(path, '..', 'Qt4')
        if os.path.exists(os.path.join(path, 'QtOpenGL4.dll')):
            # Special case for if max has our pyqt installed inside it
            paths = app.libraryPaths()
            paths.append(u'C:/Program Files/Mari3.1v3/Bundle/Qt4')
            app.setLibraryPaths(paths)

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Mari application for the inputed Core tool. Not Supported currently.
        """
        return False

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the MariCore has shutdown called
        """
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        """
        # Mari does not have a scene file that can be used like most other applications.
        return ''

    def eventFilter(self, obj, event):
        if event.type() == event.Close and obj == self.rootWindow():
            # Because blurdev.core.shutdown() is triggered after the window has already been destroyed,
            # we need to capture the close event and shutdown the toolbars here in order to successfully
            # save preferences for them.
            self.shutdownToolbars()
        return super(MariCore, self).eventFilter(obj, event)

    def lovebar(self, parent=None):
        if parent == None:
            parent = self.rootWindow()
        from blurdev.tools.toolslovebar import ToolsLoveBar

        hasInstance = ToolsLoveBar._instance != None
        lovebar = ToolsLoveBar.instance(parent)
        if not hasInstance and isinstance(parent, QMainWindow):
            parent.addToolBar(Qt.TopToolBarArea, lovebar)
            parent.installEventFilter(self)
        return lovebar

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Add to Lovebar...'

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Mari applications
        """
        output = blurdev.tools.tool.ToolType.Mari
        return output

    def recordToolbarXML(self, pref):
        from blurdev.tools.toolstoolbar import ToolsToolBar

        if ToolsToolBar._instance:
            toolbar = ToolsToolBar._instance
            toolbar.toXml(pref.root())
            child = pref.root().addNode('toolbardialog')
            child.setAttribute('visible', toolbar.isVisible())

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
