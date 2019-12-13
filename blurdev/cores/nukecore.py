import re
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core
import nuke
from Qt.QtWidgets import QApplication, QMainWindow
from Qt.QtCore import Qt


class NukeCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Nuke sessions
    """

    ignore_messages = set(['Cancelled', 'No nodes selected'])

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'nuke'
        super(NukeCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False

    def initGui(self):
        """
        initGui needs to be called by the nuke plugins so it gets called once the UI is created.
        """
        super(NukeCore, self).initGui()
        # Save prefs while the gui is still visible
        self.rootWindow().installEventFilter(self)
        # Shutdown blurdev when Nuke closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Nuke application for the inputed Core tool. Not Supported currently.
        """
        return False

    @property
    def headless(self):
        """ If true, no Qt gui elements should be used because python is running a QCoreApplication. """
        return not nuke.GUI

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
        if (
            isinstance(exc_value, RuntimeError)
            and exc_value.message in self.ignore_messages
        ):
            return dict(email=False, prompt=False, sentry=False)

        return super(NukeCore, self).shouldReportException(
            exc_type, exc_value, exc_traceback
        )

    def quitQtOnShutdown(self):
        """ Qt should not be closed when the NukeCore has shutdown called
        """
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        """
        try:
            return '<i>Open File:</i> %s' % nuke.scriptName()
        except RuntimeError:
            return ''

    def eventFilter(self, obj, event):
        """ `QApplication.aboutToQuit` is only fired after the rootWindow is closed
        so we can't save visibility prefs. This event fires each time someone
        tries to close nuke, but **before** the user has a chance to cancel the close.
        This means we can't shutdown blurdev here.
        This code saves the GUI prefs now, and when aboutToQuit is fired, it
        saves calls self.shutdown, but because we have customized
        :py:meth:`NukeCore.recordToolbars` the gui visibility is not saved.
        """
        if event.type() == event.Close and obj == self.rootWindow():
            if not self.headless:
                for toolbar_class in self.toolbars():
                    toolbar_class.instanceRecordSettings()
        return super(NukeCore, self).eventFilter(obj, event)

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Add to Lovebar...'

    def recordToolbars(self):
        """ Records settings for all found toolbars.

        See Also:
            :py:meth:`blurdev.cores.core.Core.recordToolbars`.  This override does not
            record visibility and position info for the toolbars like other core
            overrides. This is to work around the issues discussed in
            :py:meth:`NukeCore.recordToolbars`.
        """
        if self.headless:
            # If running headless, the toolbars were not created, and prefs don't need to be saved
            return

        for toolbar_class in self.toolbars():
            toolbar_class.instanceRecordSettings(gui=False)

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """ Disabled for Nuke. Attempting to set a useful stylesheet on QApplication
        causes Nuke 11 to crash.
        """
        return

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Nuke applications
        """
        output = blurdev.tools.tool.ToolType.Nuke
        return output
