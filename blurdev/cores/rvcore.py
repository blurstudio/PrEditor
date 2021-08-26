from __future__ import absolute_import
import sys
import blurdev
import blurdev.tools.tool

from blurdev.cores.core import Core
from Qt.QtWidgets import QApplication


class RVCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Fusion sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'rv'
        super(RVCore, self).__init__(*args, **kargs)
        # Shutdown blurdev when RV closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def addLibraryPaths(self):
        if sys.platform == 'linux2':
            QApplication.addLibraryPath(r'/usr/lib64/qt4/plugins')
            # TODO: Use the following code to dynamicly look up this path. It must be
            # run externally from RV or it will return the wrong path.
            # 			from Qt.QtCore import QLibraryInfo
            # 			QLibraryInfo.location( QLibraryInfo.PluginsPath)
            return
        # NOTE: If the system has the global pyqt4.dll file installed (Most likely in
        # "C:\Windows\System32\blur64\designer\pyqt4.dll") RV will load it when
        # screening_room-1.65.rvpkg is loaded and if you load the Shotgun Browser, or
        # are forced to log into shotgun. This can cause RV to crash, assuming it's
        # msvc(Visual Studio) compiler doesn't match RV.
        # To prevent this you must never add the global plugin path to
        # QApplication.libraryPaths().
        # If using blur.Stone, make sure to set 'LIBSTONE_QT_LIBRARY_PATH' = 'false'
        # in the environment before importing blur.Stone (blurdev imports blur.Stone)
        # To replicate the crash I am opening the Image Loader 3 tool then using the
        # Launch Shotgun... menu to open the shotgun browser. RV will then crash.

        # NOTE: DO NOT CALL SUPER for this reason on windows.

    def macroNames(self):
        """ Returns True if the current blurdev core create a tool macro.
        """
        # Blurdev can not currently make a macro for this DCC.
        return tuple()

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the RVCore has shutdown called
        """
        return False

    def refreshStyleSheet(self):
        """ Reloading stylesheets in RV breaks the interface. """
        # For now, modifying the stylesheet causes undesireable side affects to the RV
        # interface don't modify the stylesheet with blurdev.
        pass

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """ Accepts the name of a stylesheet included with blurdev, or a full
            path to any stylesheet.  If given None, it will remove the
            stylesheet.
        """
        # For now, modifying the stylesheet causes undesireable side affects to the RV
        # interface don't modify the stylesheet with blurdev.
        return

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are
        related to Fusion applications
        """
        return blurdev.tools.tool.ToolType.RV
