from __future__ import absolute_import
import six
import blurdev
import blurdev.tools.tool
import nuke

from blurdev.cores.core import Core
from Qt.QtWidgets import QApplication


class NukeCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Nuke sessions
    """

    ignore_messages = set(['Cancelled', 'No nodes selected'])

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'nuke'
        super(NukeCore, self).__init__(*args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False

    def addLibraryPaths(self):
        # Do not add default library paths
        self._disable_libstone_qt_library_path()

    def initGui(self):
        """
        initGui needs to be called by the nuke plugins so it gets called once the UI is
        created.
        """
        super(NukeCore, self).initGui()
        # Save prefs while the gui is still visible
        self.rootWindow().installEventFilter(self)
        # Shutdown blurdev when Nuke closes
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.shutdown)

    @property
    def headless(self):
        """If true, no Qt gui elements should be used because python is running a
        QCoreApplication."""
        return not nuke.GUI

    def shouldReportException(self, exc_type, exc_value, exc_traceback, actions=None):
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
            actions (dict, optional): default values for the returned dict. A copy
                of this dict is returned with standard defaults applied.

        Returns:
            dict: Boolean values representing whether to perform excepthook
                action, keyed to the name of the excepthook
        """
        if actions is None:
            actions = {}
        if (
            isinstance(exc_value, RuntimeError)
            and six.text_type(exc_value) in self.ignore_messages
        ):
            return dict(email=False, prompt=False, sentry=False)

        return super(NukeCore, self).shouldReportException(
            exc_type, exc_value, exc_traceback, actions=actions
        )

    def quitQtOnShutdown(self):
        """Qt should not be closed when the NukeCore has shutdown called"""
        return False

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override
        in subclasses to provide extra data. If a empty string is returned this line
        will not be shown in the error email.
        """
        try:
            return '<i>Open File:</i> %s' % nuke.scriptName()
        except RuntimeError:
            return ''

    def eventFilter(self, obj, event):
        """`QApplication.aboutToQuit` is only fired after the rootWindow is closed
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

    def macroNames(self):
        """Returns True if the current blurdev core create a tool macro."""
        # Blurdev can not currently make a macro for this DCC.
        return tuple()

    def recordToolbars(self):
        """Records settings for all found toolbars.

        See Also:
            :py:meth:`blurdev.cores.core.Core.recordToolbars`.  This override does not
            record visibility and position info for the toolbars like other core
            overrides. This is to work around the issues discussed in
            :py:meth:`NukeCore.recordToolbars`.
        """
        if self.headless:
            # If running headless, the toolbars were not created, and prefs don't need
            # to be saved
            return

        for toolbar_class in self.toolbars():
            toolbar_class.instanceRecordSettings(gui=False)

    def rootWindow(self):
        """Returns the nuke main window."""
        if self._rootWindow is not None:
            return self._rootWindow

        for widget in QApplication.instance().topLevelWidgets():
            if widget.metaObject().className() == 'Foundry::UI::DockMainWindow':
                self._rootWindow = widget
                break
        else:
            # If we don't find the root window this way, use the original method.
            super(NukeCore, self).rootWindow()

        return self._rootWindow

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """Disabled for Nuke. Attempting to set a useful stylesheet on QApplication
        causes Nuke 11 to crash.
        """
        return

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are
        related to Nuke applications
        """
        output = blurdev.tools.tool.ToolType.Nuke
        return output
