from __future__ import absolute_import
import atexit
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core
from blurdev.debug import BlurExcepthook
from blurdev.settings import OS_TYPE
from pillar import stream
import hou
from Qt import QtCompat, QtCore
from builtins import int


class HoudiniCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Houdini sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'houdini'
        super(HoudiniCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # Shutdown blurdev when Houdini closes
        atexit.register(self.shutdown)

    def addLibraryPaths(self):
        """There is no need to add library paths for houdini"""
        return

    @property
    def headless(self):
        """
        If true, no Qt gui elements should be used because python is running a
        QCoreApplication.
        """
        return not hou.isUIAvailable()

    def init(self):
        """Initializes the core system"""
        ret = super(HoudiniCore, self).init()
        if not self.headless:
            # hdefereval is only available in a graphical Houdini
            import hdefereval

            # At this point Houdini has not created the main window.
            # Delay blurdev's gui init till houdini is ready.
            hdefereval.executeDeferred(self.initGui)
        return ret

    def initGui(self):
        """Initialize the portions of the core that require GUI initialization to have
        completed.

        Added initializing the logger. This helps with tool error reporting and prevents
        houdini crashes.
        """
        # Capture python output so we can show it in the Python Logger if its shown.
        # This should have already been called by the hsite plugin, but calling it now
        # makes sure we capture the output.
        stream.install_to_std()

        def install_excepthook():
            # Install the BlurExcepthook so we can capture, report and tell the user
            # about errors
            BlurExcepthook.install()

        # RESPECT THE 5 SECOND RULE!
        # NOTE: On linux if the Python Logger is initialized at this point, it will
        # cause a segfault applying stylesheets. After a few seconds of delay using
        # a QTimer, houdini will no longer crash. Disable the prompt on error feature
        # till well after this delay. Initial testing requires ~5 seconds.
        if OS_TYPE == 'Linux':
            # TODO: Using a QTimer like this is a bit of a hack, find a better way
            # to provide this delay. This makes it so we can't show the message box
            # if a error happens before the timer expires. However we are able to
            # include the error text in the Python Logger when it is shown.
            QtCore.QTimer.singleShot(5000, install_excepthook)
        else:
            install_excepthook()

        super(HoudiniCore, self).initGui()

    def quitQtOnShutdown(self):
        """Qt should not be closed when the HoudiniCore has shutdown called"""
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override
        in subclasses to provide extra data. If a empty string is returned this line
        will not be shown in the error email.
        """
        try:
            return '<i>Open File:</i> %s' % hou.hipFile.name()
        except RuntimeError:
            return ''

    def macroNames(self):
        """Returns True if the current blurdev core create a tool macro."""
        # Blurdev can not currently make a macro for this DCC.
        return tuple()

    def rootWindow(self):
        """
        Returns the houdini main window cast to the correct Qt binding.
        """
        if self.headless or self._rootWindow is not None:
            return self._rootWindow

        mainWindow = hou.qt.mainWindow()
        if mainWindow is None:
            return None
        # Cast the PySide2 object houdini returns to PyQt5
        try:
            from PySide2 import shiboken2
        except ImportError:
            # Houdini 18+ have shiboken as a module separate from PySide2.
            import shiboken2

        pointer = int(shiboken2.getCppPointer(mainWindow)[0])
        self._rootWindow = QtCompat.wrapInstance(pointer)
        return self._rootWindow

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are
        related to Houdini applications
        """
        output = blurdev.tools.tool.ToolType.Houdini
        return output
