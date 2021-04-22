from __future__ import print_function
from __future__ import absolute_import
import sys
import time
import os
import glob
from past.builtins import execfile

from Qt.QtCore import QCoreApplication, QDateTime, QEvent, QObject, QRect, Qt, Signal
from Qt.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QSplashScreen,
)
from Qt import QtCompat
import sentry_bootstrap

import blurdev
import blurdev.prefs
import blurdev.debug
import blurdev.osystem
import blurdev.tools
import blurdev.tools.tool
import blurdev.tools.toolsenvironment
import blurdev.cores.application
import blurdev.settings
from blurdev.decorators import pendingdeprecation
from blurdev.utils.error import sentry_before_send_callback


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to
    be distributed between different pacakges.
    """

    # ----------------------------------------------------------------
    # blurdev signals
    environmentActivated = Signal()
    environmentsUpdated = Signal()
    debugLevelChanged = Signal()
    fileCheckedIn = Signal(str)
    fileCheckedOut = Signal(str)
    aboutToClearPaths = Signal()  # Emitted before environment is changed or reloaded
    styleSheetChanged = Signal(str)
    selectedToolTypesChanged = Signal()  # Emitted if selectedToolTypes is changed

    # ----------------------------------------------------------------
    # 3d Application Signals (common)
    # Depreciated, use blur3d signals

    # scene signals
    sceneClosed = Signal()
    sceneExportRequested = Signal()
    sceneExportFinished = Signal()
    sceneImportRequested = Signal()
    sceneImportFinished = Signal()
    sceneInvalidated = Signal()
    sceneMergeRequested = Signal()
    sceneMergeFinished = Signal()
    sceneNewRequested = Signal()
    sceneNewFinished = Signal()
    sceneOpenRequested = Signal(str)
    sceneOpenFinished = Signal(str)
    sceneReset = Signal()
    sceneSaveRequested = Signal(str)
    sceneSaveFinished = Signal(str)

    # layer signals
    layerCreated = Signal()
    layerDeleted = Signal()
    layersModified = Signal()
    layerStateChanged = Signal()

    # object signals
    selectionChanged = Signal()

    # render signals
    rednerFrameRequested = Signal(int)
    renderFrameFinished = Signal()
    renderSceneRequested = Signal(list)
    renderSceneFinished = Signal()

    # time signals
    currentFrameChanged = Signal(int)
    frameRangeChanged = Signal()

    # application signals
    startupFinished = Signal()
    shutdownStarted = Signal()

    # the event id for Queue Processing
    qProcessID = 15648

    # ----------------------------------------------------------------

    def __init__(self, hwnd=0, objectName=None):
        QObject.__init__(self)
        if objectName is None:
            objectName = 'blurdev'
        QObject.setObjectName(self, objectName)

        # create custom properties
        self._protectedModules = []
        self._hwnd = hwnd
        self._keysEnabled = True
        self._lastFileName = ''
        self._mfcApp = False
        self._logger = None
        self._supportsDocking = False
        self._linkedSignals = {}
        self._itemQueue = []
        self._maxDelayPerCycle = 0.1
        self._stylesheet = None
        self._headless = False
        self._useAppUserModelID = None
        self._rootWindow = None
        self._toolbars = None
        self._selected_tool_types = None

        # Controls if launching a treegrunt tool in external python will use a
        # subprocess. The blurdev cli launcher sets this to `"once"`, so when it
        # launches the requested tool it is done in the same process. Then this variable
        # is changed to True. This speeds up loading of the tool as it prevents
        # repeating imports in a new process. If True, then all tool launches are done
        # in a subprocess if using external python.
        self.launchExternalInProcess = True

        # Applications like 3ds Max 2018 use stylesheets, when blurdev installs custom
        # stylesheets it will automatically add this to the start of that stylesheet.
        # This makes it so we don't have to include that stylesheet info into our
        # stylesheets, but still don't cause horrible eye gouging things to happen to
        # the application.
        self._defaultStyleSheet = ''

        # Paths in this variable will be removed in
        # blurdev.osystem.subprocessEnvironment
        self._removeFromPATHEnv = set()
        self.environment_override_filepath = os.environ.get(
            'BDEV_ENVIRONMENT_OVERRIDE_FILEPATH', ''
        )
        # When Using Fusion, this will be populated with a PeyeonScript.scriptapp
        # connected to the parent fusion process. Otherwise this will be None
        self.fusionApp = None

        # create the connection to the environment activation signal
        self.environmentActivated.connect(self.registerPaths)
        self.environmentActivated.connect(self.recordSettings)
        self.debugLevelChanged.connect(self.recordSettings)

    @classmethod
    def _disable_libstone_qt_library_path(cls):
        """By default libstone adds "C:\\Windows\\System32\\blur64" or "C:\\blur\\common"
        to QApplication.libraryPaths(). This works well for external python applications
        but doesn't work well in DCC's. If Qt5 is installed globally its msvc compiled
        version may conflict with the DCC's msvc compile and cause it to crash.

        This sets the LIBSTONE_QT_LIBRARY_PATH to a invalid path disabling that feature
        of libstone. `blurdev.osystem.subprocessEnvironment` removes this env var to
        prevent launching a external python process from a DCC getting this var.
        """
        os.environ["LIBSTONE_QT_LIBRARY_PATH"] = "false"

    def aboutBlurdev(self):
        """Useful info about blurdev and its dependencies as a string."""
        from Qt import (
            __binding__,
            __binding_version__,
            __version__ as qtpy_version,
            __qt_version__,
        )

        msg = [
            'blurdev: {}'.format(blurdev.__version__),
            '    {}'.format(os.path.dirname(blurdev.__file__)),
        ]
        # When trax is imported it creates this env var for error reporting. We don't
        # want to inport trax to generate version info, but show it if possible.
        if os.getenv('BDEV_EMAILINFO_TRAX_VERSION'):
            msg.append('trax: {}'.format(os.getenv('BDEV_EMAILINFO_TRAX_VERSION')))
            if 'trax' in sys.modules:
                import trax
                from trax.api.data import Database, User
                import getpass

                msg.append('    {}'.format(os.path.dirname(trax.__file__)))
                msg.append('    Usernames:')
                msg.append('        os: {}'.format(getpass.getuser()))
                msg.append('        trax: {}'.format(User.currentUser().username()))
                msg.append(
                    '        db: {}'.format(Database.current().connection().userName())
                )

        msg.append('Qt: {}'.format(__qt_version__))
        msg.append('{qt}: {qtver}'.format(qt=__binding__, qtver=__binding_version__))
        msg.append('Qt.py: {}'.format(qtpy_version))

        try:
            # QtSiteConfig is optional
            import QtSiteConfig

            msg.append('QtSiteConfig: {}'.format(QtSiteConfig.__version__))
        except (ImportError, AttributeError):
            pass

        # Include the python version info
        msg.append('Python:')
        msg.append('    {}'.format(sys.version))

        return '\n'.join(msg)

    def activeWindow(self):
        if QApplication.instance():
            return QApplication.instance().activeWindow()
        return None

    def addLibraryPaths(self):
        """Add default Qt plugin paths to the QCoreApplication.

        It is safe to call this multiple times as addLibraryPath won't add the
        same path twice.
        """
        # Set library paths so qt plugins, image formats, sql drivers, etc can be loaded
        # if needed
        if sys.platform != 'win32':
            return
        if blurdev.osystem.getPointerSize() == 64:
            QCoreApplication.addLibraryPath("c:/windows/system32/blur64/")
        else:
            QCoreApplication.addLibraryPath("c:/blur/common/")

    def configUpdated(self):
        """Preform any core specific updating of config. Returns if any actions were
        taken.
        """
        return False

    def connectAppSignals(self):
        """Connect the signals emitted by the application we're in to the blurdev core
        system
        """
        pass

    def connectPlugin(self, hInstance, hwnd, style=None, palette=None, stylesheet=''):
        """Creates a QMfcApp instance for the inputted plugin and window if no
        app is currently running.

        Args:
            hInstance (int):
            hwnd (int):
            style (str, optional): If None blurdev.core.defaultStyle() is used.
            palette (QPalette, optional): Legacy, use stylesheet to style.
            stylesheet (str, optional):

        Returns:
            bool: success
        """

        # check to see if there is an application already running
        if not QApplication.instance():
            self.addLibraryPaths()
            if sys.platform == 'win32':  # shitty
                from Qt.QtWinMigrate import QMfcApp
            # create the plugin instance
            if QMfcApp.pluginInstance(hInstance):
                self.setHwnd(hwnd)
                self._mfcApp = True

                app = QApplication.instance()
                if app:
                    if style is None:
                        style = self.defaultStyle()
                    app.setStyle(style)
                    if palette:
                        app.setPalette(palette)
                    if stylesheet:
                        app.setStylesheet(stylesheet)

                    # initialize the logger
                    if not self.headless:
                        self.logger()

                return True
        return False

    def createToolMacro(self, tool, macro_name):
        """Method to create macros for a tool.

        Creates a shortcut if `self.macroNames()` has any names. If a DCC
        supports macros, it should override this function with its own implementation.

        Args:
            tool (blurdev.tools.tool.Tool): The tool to create the desktop shortcut for.
            macro_name (str): One of the returned strings of the `macroNames` method.
                This is used to create the macro for the requested menu item.

        Returns:
            bool: If a macro was created.
        """
        if not self.macroNames():
            return False

        from ..utils import shortcut

        # If the user requested a start menu shortcut, create it in the blur folder.
        if macro_name == 'Create Start Menu Shortcut':
            path = ('start menu', 'Blur')
        else:
            # Otherwise create it on the desktop
            path = ('desktop',)

        # Using treegrunt-tool makes it so the desktop shortcuts launch using the same
        # treegrunt environment used by external treegrunt.
        shortcut.createShortcutTool(tool, path=path)

        return True

    def defaultEnvironmentPath(self):
        return os.path.normpath(
            os.environ['BDEV_MASTER_TOOLS_ENV_CONFIG']
            % {'filepath': blurdev.resourcePath()}
        )

    def defaultStyle(self):
        """The default style name used when setting up the QApplication.

        In Qt4 this is Plastique, in Qt5 this is Fusion.
        """
        from Qt import IsPyQt4, IsPySide

        if IsPyQt4 or IsPySide:
            return 'Plastique'
        return 'Fusion'

    def disableKeystrokes(self):
        # disable the client keystrokes
        self._keysEnabled = False

    def dispatch(self, signal, *args):
        """Dispatches a string based signal through the system from an application"""
        if self.signalsBlocked():
            return

        # emit a defined Signal
        if (
            hasattr(self, signal)
            and type(getattr(self, signal)).__name__ == 'pyqtBoundSignal'
        ):
            getattr(self, signal).emit(*args)

        # otherwise emit a custom signal
        else:
            self.emit(signal, *args)

        # emit linked signals
        if signal in self._linkedSignals:
            for trigger in self._linkedSignals[signal]:
                self.dispatch(trigger)

    def emitEnvironmentActivated(self):
        if not self.signalsBlocked():
            self.environmentActivated.emit()

            # This records the last time a user deliberately changed the
            # environment.  If the environment has a timeout, it will use
            # this timestamp to enforce the timeout.
            pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())
            pref.recordProperty(
                'environment_set_timestamp', QDateTime.currentDateTime()
            )
            pref.save()

    def emitDebugLevelChanged(self):
        if not self.signalsBlocked():
            self.debugLevelChanged.emit()

    def enableKeystrokes(self):
        # enable the client keystrokes
        self._keysEnabled = True

    def flashWindow(self, window=None, dwFlags=None, count=1, timeout=0, hwnd=None):
        """Flashes the application depending on the os.

        On Windows this calls FlashWindowEx. See this documentation.
        http://docs.activestate.com/activepython/2.7/pywin32/win32gui__FlashWindowEx_meth.html
        https://msdn.microsoft.com/en-us/library/ms679348(v=vs.85).aspx

        Args: window (QWidget|None): This widget will be flashed. Attempts to get the
            hwnd from this widget. Note: This is ignored if hwnd is passed in.

            dwFlags (blurdev.osystem.FlashTimes): A enum value used to control the
                flashing behavior. See
                https://msdn.microsoft.com/en-us/library/ms679348(v=vs.85).aspx for more
                details. Defaults to FLASHW_TIMERNOFG.

            count (int): The number of times to flash the window. Defaults to 1.

            timeout (int): The rate at which the window is to be flashed in
                milliseconds. if zero is passed, the default cursor blink rate is used.

            hwnd (int or None): Flash this hwnd. If None(default) it will flash window
                if provided, otherwise it will flash blurdev.core.rootWindow().

        Returns:
            bool: Was anything attempted. On windows this always returns True.
        """
        if blurdev.settings.OS_TYPE == 'Windows':
            import ctypes

            if dwFlags is None:
                dwFlags = blurdev.osystem.FlashTimes.FLASHW_TIMERNOFG
            if hwnd is None:
                if window is None:
                    if self.isMfcApp():
                        hwnd = self.hwnd()
                    else:
                        hwnd = self.rootWindow().winId().__int__()
                else:
                    hwnd = window.winId().__int__()

            ctypes.windll.user32.FlashWindow(hwnd, int(dwFlags), count, timeout)
            return True
        return False

    def runOnDccStartup(self):
        """When starting a DCC like 3ds Max, execute this code on startup.

        This provides a location for defining additional startup behavior when a DCC is
        initalized. Currently it is used to check if trax should be imported on startup
        and if the studio.internal scene callbacks should be initialized.

        This module is safe to call without trax or blur3d being installed.
        """
        # Don't run studio callbacks in this dcc when in quiet mode(rendering) or if its
        # disabled by the environment variable BDEV_TRAX_ON_DCC_STARTUP.
        enableTraxOnDccStartup = os.environ.get(
            'BDEV_TRAX_ON_DCC_STARTUP', 'true'
        ).lower()
        if not self.quietMode() and enableTraxOnDccStartup == 'true':
            try:
                # A full trax install is required to work with the blur specific blur3d
                # api
                import trax

                if trax.isValid:
                    # Initializing the pipe layer of blur3d. On import trax.api will be
                    # imported and pipeline specific signals will be connected. See the
                    # studio/internal/__init__.py for more information.
                    import studio.internal  # noqa: F401
            # This is to prevent errors if modules do not exist.
            except (ImportError, AttributeError):
                pass

    def errorCoreText(self):
        """Returns text that is included in the error email for the active core.
        Override in subclasses to provide extra data. If a empty string is returned
        this line will not be shown in the error email.
        """
        return ''

    def event(self, event):
        if event.type() == self.qProcessID:
            # process the next item in the queue
            self.processQueueItem()
            return True
        return False

    def eventFilter(self, object, event):

        # Events that enable client keystrokes
        if event.type() in (QEvent.FocusOut, QEvent.HoverLeave, QEvent.Leave):
            self.enableKeystrokes()

        # Events that disable client keystrokes
        if event.type() in (
            QEvent.FocusIn,
            QEvent.MouseButtonPress,
            QEvent.Enter,
            QEvent.ToolTip,
            QEvent.HoverMove,
            QEvent.KeyPress,
        ):
            self.disableKeystrokes()

        return QObject.eventFilter(self, object, event)

    def linkSignals(self, signal, trigger):
        """Creates a dependency so that when the inputed signal is dispatched, the
        dependent trigger signal is also dispatched.  This will only work for
        trigger signals that do not take any arguments for the dispatch.
        """
        if signal not in self._linkedSignals:
            self._linkedSignals[signal] = [trigger]
        elif trigger not in self._linkedSignals[signal]:
            self._linkedSignals[signal].append(trigger)

    def shouldReportException(self, exc_type, exc_value, exc_traceback, actions=None):
        """
        Allow core to control how exceptions are handled. Currently being used
        by `BlurExcepthook`, informing which excepthooks should or should not
        be executed.

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
        # Create a shallow copy so we don't modify the passed in dict and don't
        # need to use a default value of None
        actions = actions.copy()

        # provide the expected default values
        actions.setdefault('email', True)
        # If blurdev is running headless, there is no way to show a gui prompt
        actions.setdefault('prompt', not self.headless)
        return actions

    def init(self):
        """Initializes the core system"""
        ret = self.initCore()
        return ret

    def initCore(self):
        """Work method to initialize the core system -- breaking the initialization
        apart allows the gui-dependant initialization to be delayed in applications
        where that is necessary by overloading init().
        """
        # register protected modules
        # do not want to affect this module during environment switching
        self.protectModule('blurdev')
        # we should never remove main. If we do in specific cases it will prevent
        # external tools from running if they use "if __name__ == '__main__':" as
        # __name__ will return None
        self.protectModule('__main__')
        # Pillar is used by blurdev so reloading it breaks blurdev. Devs may have pillar
        # in their tools virtualenv to aid in installing other pip packages.
        self.protectModule('pillar')
        # pkg_resources is found in the tools virtualenv and we use it when switching
        # treegrunt environments to find `blurdev.tools.paths` entry_points.
        self.protectModule('pkg_resources')

        # initialize sentry client
        sentry_bootstrap.init_sentry(force=True)
        sentry_bootstrap.add_external_callback(sentry_before_send_callback)

        # Gets the override filepath, it is defined this way, instead of
        # being defined in the class definition, so that we can change this
        # path, or remove it entirely for offline installs.
        # self.environment_override_filepath = os.environ.get(
        #     'BDEV_ENVIRONMENT_OVERRIDE_FILEPATH', '')

        # initialize the application
        app = QApplication.instance()
        output = None

        self.addLibraryPaths()
        if app:
            if self.isMfcApp():
                # disable all UI effects as this is quite slow in MFC applications
                app.setEffectEnabled(Qt.UI_AnimateMenu, False)
                app.setEffectEnabled(Qt.UI_FadeMenu, False)
                app.setEffectEnabled(Qt.UI_AnimateCombo, False)
                app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
                app.setEffectEnabled(Qt.UI_FadeTooltip, False)
                app.setEffectEnabled(Qt.UI_AnimateToolBox, False)
                app.aboutToQuit.connect(self.recordToolbars)
                app.installEventFilter(self)

        # create a new application
        else:
            from blurdev.cores.application import CoreApplication, Application

            # Check for headless environment's
            if blurdev.settings.OS_TYPE == 'Linux':
                if os.environ.get('DISPLAY') is None:
                    output = CoreApplication([])
                    self._headless = True
            if output is None:
                output = Application([])

        self.updateApplicationName(output)

        # initialize the tools environments after the applicationName is set.
        blurdev.tools.toolsenvironment.ToolsEnvironment.loadConfig(
            self.defaultEnvironmentPath()
        )

        # restore the core settings
        self.restoreSettings()
        self.connectAppSignals()
        return output

    def initGui(self):
        """Initialize the portions of the core that require GUI initialization to have
            completed.

        This function should be called by each subclass of Core if needed, or by
        a dcc plugin implementation when it is safe to initialize gui objects.
        """
        self.restoreToolbars()

    def applyEnvironmentTimeouts(self):
        """
        Checks the current environment to see if has a timeout and if it has
        exceeded that timeout.  If so, it will reset the environment to the
        default environment.

        """
        env = blurdev.tools.toolsenvironment.ToolsEnvironment.activeEnvironment()
        threshold_time = env.timeoutThreshold()
        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())
        last_timestamp = pref.restoreProperty('environment_set_timestamp', None)

        if not last_timestamp or not threshold_time:
            return

        if last_timestamp < threshold_time:
            env = blurdev.tools.toolsenvironment.ToolsEnvironment.defaultEnvironment()
            print(
                'Environment timeout exceeded, Resetting to default environment:',
                env.objectName(),
            )
            env.setActive()
            pref.recordProperty(
                'environment_set_timestamp', QDateTime.currentDateTime()
            )
            pref.save()

    def applyStudioOverrides(self):
        """
        Checks a studio environment override file.  If there

        """
        # Checks for the studio environment override file
        override_dict = self.getEnvironmentOverride()
        if not override_dict:
            return

        env = override_dict['environment']
        timestamp = override_dict['timestamp']
        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())
        last_timestamp = pref.restoreProperty(
            'last_environment_override_timestamp', None
        )
        if last_timestamp and last_timestamp >= timestamp:
            return
        blurdev.tools.toolsenvironment.ToolsEnvironment.findEnvironment(env).setActive()
        pref.recordProperty(
            'last_environment_override_timestamp', QDateTime.currentDateTime()
        )
        pref.save()

    def isMfcApp(self):
        return self._mfcApp

    @property
    def headless(self):
        """If true, no Qt gui elements should be used because python is running a
        QCoreApplication.
        """
        return self._headless

    def hwnd(self):
        if self.objectName() == 'assfreezer':
            return int(self.rootWindow().winId())
        return self._hwnd

    def ideeditor(self, parent=None):
        from blurdev.ide.ideeditor import IdeEditor

        return IdeEditor.instance(parent)

    def isKeystrokesEnabled(self):
        return self._keysEnabled

    def lastFileName(self):
        return self._lastFileName

    def logger(self, parent=None):
        """Creates and returns the logger instance"""
        from blurdev.gui.windows.loggerwindow import LoggerWindow

        return LoggerWindow.instance(parent)

    def macroNames(self):
        """Returns the names to display for the create macro action in treegrunt.

        The selected name is passed to the macro_name argument of createToolMacro.
        """
        return ('Create Start Menu Shortcut', 'Create Desktop Shortcut')

    def mainWindowGeometry(self):
        """QWinWidget doesn't properly center its children.

        In MFC apps this function returns the size of the main window.

        Note: Qt doesn't include the titlebar so the position may be off by that
        ammount.
        """
        if self.headless:
            raise Exception('You are showing a gui in a headless environment. STOP IT!')
        return QRect()

    def maxDelayPerCycle(self):
        return self._maxDelayPerCycle

    def newScript(self):
        """
        Creates a new script window for editing
        """
        from blurdev.ide.ideeditor import IdeEditor

        IdeEditor.createNew()

    def openScript(self, filename=''):
        """
        Opens the an existing script in a new window for editing
        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename, _ = QtCompat.QFileDialog.getOpenFileName(
                    None,
                    'Select Script File',
                    self._lastFileName,
                    'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                )
                if not filename:
                    return

        if filename:
            self._lastFileName = filename
            from blurdev.ide.ideeditor import IdeEditor

            IdeEditor.edit(filename=filename)

    def postQueueEvent(self):
        """
        Insert a call to processQueueItem on the next event loop
        """
        QApplication.postEvent(self, QEvent(self.qProcessID))

    def processQueueItem(self):
        """
        Call the current queue item and post the next queue event if it exists
        """
        if self._itemQueue:
            if self._maxDelayPerCycle == -1:
                self._runQueueItem()
            else:
                t = time.time()
                t2 = t
                while self._itemQueue and (t2 - t) < self._maxDelayPerCycle:
                    t2 = time.time()
                    self._runQueueItem()
            if self._itemQueue:
                # if there are still items in the queue process the next item
                self.postQueueEvent()

    def _runQueueItem(self):
        """
        Process the top item on the queue, catch the error generated if the underlying
        c/c++ object has been deleted, and alow the queue to continue processing.
        """
        try:
            item = self._itemQueue.pop(0)
            item[0](*item[1], **item[2])
        except RuntimeError as check:
            if str(check) != 'underlying C/C++ object has been deleted':
                if self._itemQueue:
                    self.postQueueEvent()
                raise
        except Exception:
            if self._itemQueue:
                self.postQueueEvent()
            raise

    def protectModule(self, moduleName):
        """
        Registers the inputed module name for protection from tools environment
        switching
        """
        key = str(moduleName)
        if key not in self._protectedModules:
            self._protectedModules.append(str(moduleName))

    def protectedModules(self):
        """
        Returns the modules that should not be affected when a tools environment changes
        """
        return self._protectedModules

    def pyular(self, parent=None):
        from blurdev.gui.widgets.pyularwidget import PyularDialog

        return PyularDialog.instance(parent)

    def quietMode(self):
        """
        Use this to decide if you should provide user input.
        """
        return False

    def registerPaths(self):
        """
        Registers the paths that are needed based on this core
        """
        env = blurdev.tools.toolsenvironment.ToolsEnvironment.activeEnvironment()

        # Canonical way to check 64-bitness of python interpreter
        # http://docs.python.org/2/library/platform.html#platform.architecture
        is_64bits = hasattr(sys, 'maxsize') and sys.maxsize > (2 ** 32)
        # Add Python24 specific libraries
        if sys.version_info[:2] == (2, 4):
            path = 'code/python/lib_python24'
            env.registerPath(env.relativePath(path))
        # Add Python26 specific libraries
        elif sys.version_info[:2] == (2, 6):
            path = 'code/python/lib_python26'
            if is_64bits:
                path = 'code/python/lib_python26_64'
            env.registerPath(env.relativePath(path))
        # Add Python27 specific libraries
        elif sys.version_info[:2] == (2, 7):
            path = 'code/python/lib_python27'
            if is_64bits:
                path = 'code/python/lib_python27_64'
            env.registerPath(env.relativePath(path))

    def recordSettings(self):
        """
        Subclasses can reimplement this to add data before it is saved
        """
        pref = self.recordCoreSettings()
        pref.save()

    def recordCoreSettings(self):
        """Returns a prefs object recording standard core settings.

        This function does not actually save the preferences, you must call save.
        """
        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())

        # record the tools environment
        env = blurdev.tools.toolsenvironment.ToolsEnvironment.activeEnvironment()
        envName = env.objectName()
        if envName != os.environ.get('BDEV_TOOL_ENVIRONMENT'):
            pref.recordProperty('environment', envName)

        # record the debug if it was not set by the environment variable
        if 'BDEV_DEBUG_LEVEL' not in os.environ:
            pref.recordProperty('debugLevel', blurdev.debug.debugLevel())

        # record the tools style
        pref.recordProperty('style', self._stylesheet)

        return pref

    def recordToolbars(self):
        """Records settings for all found toolbars."""
        if self.headless:
            # If running headless, the toolbars were not created, and prefs don't need
            # to be saved
            return

        for toolbar_class in self.toolbars():
            toolbar_class.instanceRecordSettings()

    def refreshStyleSheet(self):
        """Reload the current stylesheet to force a update of the display of widgets."""
        app = QApplication.instance()
        if app and isinstance(
            app, QApplication
        ):  # Don't set stylesheet if QCoreApplication
            app.setStyleSheet(app.styleSheet())

    def createEnvironmentOverride(self, env=None, timestamp=None):
        from blurdev.XML import XMLDocument

        if env is None:
            env = blurdev.tools.toolsenvironment.ToolsEnvironment.defaultEnvironment()
            env = env.objectName()

        if timestamp is None:
            timestamp = QDateTime.currentDateTime()

        fp = self.environment_override_filepath
        if not fp:
            return

        doc = XMLDocument()
        root = doc.addNode('environment_overrides')
        root.setAttribute('version', 1.0)
        el = root.addNode('environment_override')
        el.setAttribute('environment', env)
        el.setAttribute('timestamp', timestamp.toString('yyyy-MM-dd hh:mm:ss'))
        try:
            doc.save(fp)
        except Exception:
            pass

    def getEnvironmentOverride(self):
        from blurdev.XML import XMLDocument

        doc = XMLDocument()
        self.environment_override_filepath = os.environ.get(
            'BDEV_ENVIRONMENT_OVERRIDE_FILEPATH', ''
        )
        try:
            if not self.environment_override_filepath:
                return None
            if not os.path.exists(self.environment_override_filepath):
                return None
            if not doc.load(self.environment_override_filepath):
                return None

            root = doc.root()
            if not root:
                return None

            element = root.findChild('environment_override')
            if not element:
                return None

            attrs = element.attributeDict()
            if not attrs:
                return None

            if not attrs.get('environment'):
                return None

            try:
                timestamp = attrs.get('timestamp')
                if not timestamp:
                    return None
                attrs['timestamp'] = QDateTime.fromString(
                    timestamp, 'yyyy-MM-dd hh:mm:ss'
                )
            except Exception:
                return None

            return attrs

        except Exception:
            return None

    def restoreSettings(self):
        from blurdev.tools.toolsenvironment import ToolsEnvironment

        self.blockSignals(True)

        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())

        env = ToolsEnvironment.findEnvironment(os.environ.get('BDEV_TOOL_ENVIRONMENT'))
        if not env.isEmpty():
            env.setActive()
        else:
            # restore the active environment
            env = pref.restoreProperty('environment')
            if env:
                ToolsEnvironment.findEnvironment(env).setActive()

        # restore the active style
        self.setStyleSheet(
            os.environ.get('BDEV_STYLESHEET') or pref.restoreProperty('style'),
            recordPrefs=False,
        )

        self.blockSignals(False)

        # restore the active debug level if it was not set by the environment variable
        if 'BDEV_DEBUG_LEVEL' not in os.environ:
            level = pref.restoreProperty('debugLevel')
            if level is not None:
                blurdev.debug.setDebugLevel(level)

        self.applyEnvironmentTimeouts()
        self.applyStudioOverrides()
        # Ensure the core has its paths registered
        self.registerPaths()

        return pref

    def restoreToolbars(self):
        """Create and restore the settings for any toolbar plugins."""
        if self.headless:
            # If running headless, do not try to create gui elements
            return

        # The toolbars will end up calling findTool(tool_name). This doesn't end up
        # fully loading the index and results in multiple json file reads. This can
        # cause duplicate tools to show up in the index. This is visible in the
        # Treegrunt category view. Calling load here prevents all of this and means
        # we only need to parse the json files once.
        blurdev.activeEnvironment().index().load()

        for toolbar_class in self.toolbars():
            toolbar = toolbar_class.instance(blurdev.core.rootWindow())
            toolbar.restoreSettings()

    def rootWindow(self):
        """
        Returns the currently active window
        """
        if self._rootWindow is not None:
            return self._rootWindow

        # for MFC apps there should be no root window
        if self.isMfcApp():
            # Do not cache WinWidget's to self._rootWindow. From the docs: "If the child
            # widget is a top level window that uses the WDestructiveClose flag,
            # QWinWidget will destroy itself when the child window closes down."
            # WDestructiveClose is Qt3's version of Qt.WA_DeleteOnClose(The docs are out
            # of date) This means that as soon as a widget with WA_DeleteOnClose set is
            # closed the cached self._rootWindow is garbage collected.
            # https://github.com/qtproject/qt-solutions/blob/master/qtwinmigrate/doc/
            # html/qwinwidget.html#L75
            from blurdev.gui.winwidget import WinWidget

            return WinWidget.newInstance(self.hwnd())

        if QApplication.instance():
            self._rootWindow = QApplication.instance().activeWindow()
            # Ignore QSplashScreen's, they should never be considered the root window.
            if isinstance(self._rootWindow, QSplashScreen):
                self._rootWindow = None
            # If the application does not have focus try to find A top level widget
            # that doesn't have a parent and is a QMainWindow or QDialog
            if self._rootWindow is None:
                windows = []
                dialogs = []
                for w in QApplication.instance().topLevelWidgets():
                    if w.parent() is None:
                        if isinstance(w, QMainWindow):
                            windows.append(w)
                        elif isinstance(w, QDialog):
                            dialogs.append(w)
                if windows:
                    self._rootWindow = windows[0]
                elif dialogs:
                    self._rootWindow = dialogs[0]

            # grab the root window
            if self._rootWindow:
                while self._rootWindow.parent():
                    parent = self._rootWindow.parent()
                    if isinstance(parent, QSplashScreen):
                        return self._rootWindow
                    else:
                        self._rootWindow = parent
        return self._rootWindow

    def runDelayed(self, function, *args, **kargs):
        """
        Alternative to a for loop that will not block the ui. Each item added
        with this method will be processed during a single application event
        loop. If you add 5 items with runDelayed it will process the first item,
        update the ui, process the second item, update the ui, etc. This is
        usefull if you have a large amount of items to process, but processing
        of a individual item does not take a long time. Also it does not need
        to happen immediately.

        :param function: The function to call when ready to process.

        Any additional arguments or keyword arguments passed to this function
        will be passed along to the provided function

        | #A simplified code example of what is happening.
        | queue = []
        | for i in range(100): queue.append(myFunction)
        | while True:	# program event loop
        | 	updateUI()	# update the programs ui
        |	if queue:
        |		item = queue.pop(0)	# remove the first item in the list
        |		item()	# call the stored function

        """
        self._runDelayed(function, False, *args, **kargs)

    def runDelayedReplace(self, function, *args, **kargs):
        """
        Same as the runDelayed, but will check if the queue contains a matching
        function, *args, and **kargs. If found it will remove it and append it at the
        end of the queue.
        """
        self._runDelayed(function, True, *args, **kargs)

    def isDelayed(self, function, *args, **kwargs):
        """
        Is the supplied function and arguments are in the runDelayed queue
        """
        if (function, args, kwargs) in self._itemQueue:
            return True
        return False

    def _runDelayed(self, function, replace, *args, **kargs):
        """
        Alternative to a for loop that will not block the ui. Each item added
        with this method will be processed during a single application event loop.
        If you add 5 items with runDelayed it will process the first item, update
        the ui, process the second item, update the ui, etc. This is usefull if
        you have a large amount of items to process, but processing of a
        individual item does not take a long time. Also it does not need to
        happen immediately.

        :param function: The function to call when ready to process.
        :param bool replace: If true, it will attempt to remove the first item in the
            queue with matching function, *args, **kargs

        Any additional arguments or keyword arguments passed to this function
        will be passed along to the provided function


        | #A simplified code example of what is happening.
        | queue = []
        | for i in range(100): queue.append(myFunction)
        | while True:	# program event loop
        | 	updateUI()	# update the programs ui
        |	if queue:
        |		item = queue.pop(0)	# remove the first item in the list
        |		item()	# call the stored function

        """
        isProcessing = bool(self._itemQueue)
        queueItem = (function, args, kargs)
        if replace:
            if queueItem in self._itemQueue:
                self._itemQueue.remove(queueItem)
        self._itemQueue.append((function, args, kargs))
        if not isProcessing:
            # start the queue processing if it was empty
            self.postQueueEvent()

    def runMacro(self, command):
        """
        Runs a macro command
        """
        print('[blurdev.cores.core.Core.runMacro] virtual method not defined')
        return False

    def runStandalone(
        self,
        filename,
        debugLevel=None,
        basePath='',
        env=None,
        architecture=None,
        tool=None,
    ):
        if tool is not None:
            if env is None:
                env = blurdev.osystem.subprocessEnvironment()
            # Pass the tool's objectName to the child process so we can update
            # its QApplication.applicationName on import of blurdev.
            appName = blurdev.settings.environStr(tool.objectName())
            # This variable should be removed in the child process so it doesn't
            # affect child subprocesses. importing blurdev will remove it.
            env['BDEV_APPLICATION_NAME'] = appName
        blurdev.osystem.startfile(
            filename, debugLevel, basePath, architecture=architecture, env=env
        )

    def runScript(
        self, filename='', scope=None, argv=None, tool=None, architecture=None
    ):
        """Runs an inputted file in the best way this core knows how

        Args:
            filename (str, optional): The filename of the script to run. If not
                provided, open a QFileDialog that the user can pick a script to run.
            scope (dict or None, optional): The scope to run the script in
                (ie. locals(), globals()). Defaults to None.
            argv (list or None, optional): Commands to pass to the script at run time
            tool (blurdev.tools.Tool or None, optional): If specified, then additional
                info is used to control how the script is run. This is used to populate
                the BDEV_APPLICATION_NAME env variable when launching a external tool.
            architecture (int or None, optional): 32 or 64 bit. If None use system
                default. Defaults to None.

        Returns:
            success (bool or None): True is returned if the script was run. None is
                returned if filename was blank and the user didn't select a file.
        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename, _ = QtCompat.QFileDialog.getOpenFileName(
                    None,
                    'Select Script File',
                    self._lastFileName,
                    'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                )
                if not filename:
                    return

        if not argv:
            argv = []

        if not filename:
            return False

        # build the scope
        if scope is None:
            scope = {}

        filename = str(filename)

        # run the script
        if filename and os.path.exists(filename):
            self._lastFileName = filename
            ext = os.path.splitext(filename)[1]

            # run a python file
            if ext.startswith('.py'):
                if self.launchExternalInProcess == 'once':
                    self.launchExternalInProcess = True
                    launchExternalInProcess = False
                else:
                    launchExternalInProcess = self.launchExternalInProcess
                # if running in external mode, run a standalone version for python files
                # - this way they won't try to parent to the treegrunt
                if launchExternalInProcess and self.objectName() in (
                    'external',
                    'treegrunt',
                    'logger',
                ):
                    self.runStandalone(filename, architecture=architecture, tool=tool)
                else:
                    # create a local copy of the sys variables as they stand right now
                    path_bak = list(sys.path)
                    try:
                        argv_bak = sys.argv
                    except AttributeError:
                        argv_bak = None

                    # if the path does not exist, then register it
                    blurdev.tools.toolsenvironment.ToolsEnvironment.registerScriptPath(
                        filename
                    )

                    scope['__name__'] = '__main__'
                    scope['__file__'] = filename
                    sys.argv = [filename] + argv
                    scope['sys'] = sys

                    # create a tool stopwatch used to debug
                    env = blurdev.activeEnvironment()
                    if env.stopwatchEnabled:
                        toolName = filename if tool is None else tool.displayName()
                        env.stopwatch = blurdev.debug.Stopwatch(toolName)
                    execfile(filename, scope)
                    if env.stopwatchEnabled:
                        env.stopwatch.stop()

                    # restore the system information
                    sys.path = path_bak
                    if argv_bak:
                        sys.argv = argv_bak

                return True

            # run a fusion script
            elif ext.startswith('.eyeonscript'):

                # Moved import here because even attempting this import causes
                # win32 errors in Motionbuilder.
                try:
                    import PeyeonScript
                except ImportError:
                    PeyeonScript = None

                if PeyeonScript:
                    fusion = PeyeonScript.scriptapp('Fusion')
                    if fusion:
                        comp = fusion.GetCurrentComp()
                        if comp:
                            comp.RunScript(str(filename))
                        else:
                            QMessageBox.critical(
                                None,
                                'No Fusion Comp',
                                'There is no comp running in your Fusion.',
                            )
                    else:
                        QMessageBox.critical(
                            None,
                            'Fusion Not Found',
                            'You need to have Fusion running to run this file.',
                        )
                else:
                    QMessageBox.critical(
                        None,
                        'PeyonScript Missing',
                        'Could not import Fusion Python Libraries.',
                    )
                return True

            # run an external link
            elif ext.startswith('.lnk'):
                os.startfile(filename)
                return True

            # report an unknown format
            else:
                msg = (
                    '[blurdev.cores.core.Core.runScript] '
                    'Cannot run scripts of type (*%s)'
                )
                print(msg % ext)

        return False

    def setLastFileName(self, filename):
        return self._lastFileName

    def setHwnd(self, hwnd):
        self._hwnd = hwnd

    def setMaxDelayPerCycle(self, seconds):
        """
        Run delayed will process as many items as it can within this time
        frame every event loop.  Seconds is a float value for seconds. If
        seconds is -1 it will only process 1 item per event loop. This value
        does not limit the cycle, it just prevents a new queue item from being
        called if the total time exceeds this value. If your queue items will
        take almost the full time, you may want to set this value to -1.

        """
        self._maxDelayPerCycle = seconds

    def emailAddressMd5Hash(self, text, address=None):
        """Turns the text into a md5 string and inserts it in the address.

        This is useful for controlling how messages are threaded into conversations on
        gmail.

        Args:
            text (str): This text will be converted into a md5 hash.

            address (str or None): The md5 hash will be inserted using str.format on the
            "hash" key. If None, it will use the value stored in the BDEV_ERROR_EMAIL
            environment variable.

        Returns:
            str: The formatted address.

        """
        import hashlib

        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        if address is None:
            address = os.environ.get('BDEV_ERROR_EMAIL')
        return address.format(hash=m.hexdigest())

    def sendEmail(
        self, sender, targets, subject, message, attachments=None, refId=None
    ):
        """Sends an email.
        Args:
            sender (str): The source email address.

            targets (str or list): A single email string, or a list of email address(s)
                to send the email to.

            subject (str): The subject of the email.
            message (str): The body of the message. Treated as html
            attachments (list or None): File paths for files to be attached.

            refId (str or None): If not None "X-Entity-Ref-ID" is added to the header
                with this value. For gmail passing a empty string appears to be the same
                as passing real data.
        """
        try:
            from email import Encoders
            from email.MIMEText import MIMEText
            from email.MIMEMultipart import MIMEMultipart
            from email.MIMEBase import MIMEBase
        except ImportError:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase

        import smtplib

        output = MIMEMultipart()
        output['Subject'] = str(subject)
        output['From'] = str(sender)
        if refId is not None:
            output['X-Entity-Ref-ID'] = refId

        # convert to string
        if isinstance(targets, (tuple, list)):
            output['To'] = ', '.join(targets)
        else:
            output['To'] = str(targets)

        output['Date'] = (
            QDateTime.currentDateTime().toUTC().toString('ddd, d MMM yyyy hh:mm:ss')
        )
        output['Content-type'] = 'Multipart/mixed'
        output.preamble = 'This is a multi-part message in MIME format.'
        output.epilogue = ''

        # Build Body
        msgText = MIMEText(str(message), 'html')
        msgText['Content-type'] = 'text/html'

        output.attach(msgText)

        # Include Attachments
        if attachments:
            for a in attachments:
                fp = open(str(a), 'rb')
                txt = MIMEBase('application', 'octet-stream')
                txt.set_payload(fp.read())
                fp.close()

                Encoders.encode_base64(txt)
                txt.add_header(
                    'Content-Disposition',
                    'attachment; filename="%s"' % os.path.basename(a),
                )
                output.attach(txt)

        try:
            smtp = smtplib.SMTP('mail.blur.com', timeout=1)
            # smtp.starttls()
            # smtp.connect(os.environ.get('BDEV_SEND_EMAIL_SERVER', 'mail.blur.com'))
            smtp.sendmail(str(sender), output['To'].split(','), output.as_string())
            smtp.close()
        except Exception:
            # TODO: Proper logging

            import inspect

            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])

            import traceback

            traceback.print_exc()

            print(
                'Module {0} @ {1} failed to send email\n{2}\n{3}\n{4}\n{5}'.format(
                    module.__name__, module.__file__, sender, targets, subject, message
                )
            )

            raise

    def setObjectName(self, objectName):
        if objectName != self.objectName():
            QObject.setObjectName(self, objectName)
            blurdev.prefs.clearCache()
            # make sure we have the proper settings restored based on the new
            # application
            self.restoreSettings()

    def readStyleSheet(self, stylesheet='', path=None):
        """Returns the contents of the requested stylesheet.

        Args:

            stylesheet (str): the name of the stylesheet. Attempt to load stylesheet.css
                shipped with blurdev. Ignored if path is provided.

            path (str): Return the contents of this file path.

        Returns:
            str: The contents of stylesheet or blank if stylesheet was not found.
            valid: A stylesheet was found and loaded.
        """
        if path is None:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'resource',
                'stylesheet',
                '{}.css'.format(stylesheet),
            )
        if os.path.isfile(path):
            with open(path) as f:
                return f.read(), True
        return '', False

    def reloadStyleSheet(self):
        self.setStyleSheet(self.styleSheet())

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """Accepts the name of a stylesheet included with blurdev, or a full
        path to any stylesheet.  If given None, it will remove the
        stylesheet.
        """

        def mergeDefaultStyleSheet(newSheet):
            """If the core has backed up a stylesheet, always include it."""
            return self._defaultStyleSheet + newSheet

        app = QApplication.instance()
        if app and isinstance(
            app, QApplication
        ):  # Don't set stylesheet if QCoreApplication
            if stylesheet is None or stylesheet == 'None':
                app.setStyleSheet(mergeDefaultStyleSheet(''))
                self._stylesheet = None
            elif os.path.isfile(stylesheet):
                with open(stylesheet) as f:
                    app.setStyleSheet(mergeDefaultStyleSheet(f.read()))
                self._stylesheet = stylesheet
            else:
                # Try to find an installed stylesheet with the given name
                sheet, valid = self.readStyleSheet(stylesheet)
                if valid:
                    self._stylesheet = stylesheet
                app.setStyleSheet(mergeDefaultStyleSheet(sheet))
                path = self.styleSheetPath(stylesheet)
                if os.path.isfile(path):
                    with open(path) as f:
                        app.setStyleSheet(mergeDefaultStyleSheet(f.read()))
                    self._stylesheet = stylesheet

        if self.objectName() != 'blurdev':
            # Storing the stylesheet as an environment variable for other external
            # tools.
            os.environ['BDEV_STYLESHEET'] = str(stylesheet)

            if recordPrefs:
                # Recording preferences.
                self.recordSettings()
        # Notify widgets of the stylesheet change
        self.styleSheetChanged.emit(str(stylesheet))

    def styleSheetPath(self, styleSheet, subFolder=None):
        if not styleSheet or styleSheet == 'None':
            return ''
        components = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'resource',
            'stylesheet',
        ]
        if subFolder is not None:
            components.append(subFolder)
        components.append('{}.css'.format(styleSheet))
        return os.path.join(*components)

    def styleSheet(self):
        """Returns the name of the current stylesheet."""
        return self._stylesheet

    def styleSheets(self, subFolder=None):
        """Returns a list of installed stylesheet names.

        Args:
            subFolder (str or None, optional): Use this to access sub-folders of
                the stylesheet resource directory.

        Returns:
            list: A list .css file paths in the target directory.
        """
        components = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'resource',
            'stylesheet',
        ]
        if subFolder is not None:
            components.append(subFolder)
        cssdir = os.path.join(*components)
        cssfiles = sorted(glob.glob(os.path.join(cssdir, '*.css')))
        # Only return the filename without the .css extension
        return [os.path.splitext(os.path.basename(fp))[0] for fp in cssfiles]

    def quitQtOnShutdown(self):
        """If true is returned, all windows will be closed and
        QApplication.instance().quit() will be called. This can be overridden in cores
        to prevent shutdown.
        """
        return True

    def shutdown(self):
        # record the settings
        self.recordToolbars()
        self.recordSettings()

        if self.quitQtOnShutdown():
            if QApplication.instance():
                QApplication.instance().closeAllWindows()
                QApplication.instance().quit()
        else:
            # The app is probably nuke, maya or Motionbuilder, so closing all windows,
            # and killing the app is not what we want to do. This saves prefs and closes
            # any of the instance windows if they are active

            # Make sure to close the toolbar plugins
            self.shutdownToolbars()
            # Make sure to close Treegrunt
            from blurdev.gui.dialogs.treegruntdialog import TreegruntDialog

            TreegruntDialog.instanceShutdown()
            # Make sure to close the Logger window
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            LoggerWindow.instanceShutdown()

    def shutdownToolbars(self):
        """Shutdown toolbar plugins."""
        for toolbar in self.toolbars():
            toolbar.instanceShutdown()

    def showIdeEditor(self):
        from blurdev.ide.ideeditor import IdeEditor

        IdeEditor.instance().edit()

    @pendingdeprecation("Use blurdev.core.showToolbar('Favorites')")
    def showLovebar(self, parent=None):
        """TODO: Remove this function. It was left here so this code works with
        existing dcc integration's. Remove it once these have been updated.
        """
        self.toolbar('Favorites').instance().show()

    def showPyular(self, parent=None):
        self.pyular(parent).show()

    def showToolbar(self, name='User'):
        """Show a toolbar by its name.

        Args:
            name (str): The name of the toolbar to show.

        Returns:
            bool: If the toolbar was found and show called on it.
        """
        # TODO: name should not be optional. It is currently defaulting to User
        # to emulate the old showToolbar method currently being used by dcc
        # integration's. Remove it once these have been updated.
        toolbar = self.toolbar(name)
        if toolbar:
            toolbar.instance().show()
            return True
        return False

    def showTreegrunt(self):
        treegrunt = self.treegrunt()
        treegrunt.show()
        treegrunt.raise_()
        treegrunt.setWindowState(
            treegrunt.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )

    def showLogger(self):
        """
        Creates the python logger and displays it
        """
        logger = self.logger()
        logger.show()
        logger.activateWindow()
        logger.raise_()
        logger.console().setFocus()

    def supportsDocking(self):
        return self._supportsDocking

    def unprotectModule(self, moduleName):
        """
        Removes the inputed module name from protection from tools environment switching
        """
        key = str(moduleName)
        while key in self._protectedModules:
            self._protectedModules.remove(key)

    def updateApplicationName(self, application=None, name=None):
        """Sets the application name based on the environment.

        Args:
            application (
                Qt.QtCore.QCoreApplication or Qt.QtWidgets.QApplication, optional):
                The Qt application that should have its name set to match the
                BDEV_APPLICATION_NAME environment variable. This env variable is
                removed by calling this function so it is not passed to child
                subprocesses. If None is provided, then blurdev.application is used.

        Returns:
            bool: If the application name was set. This could be because the
                application was None.
        """
        if application is None:
            application = blurdev.application
        if application is None:
            return False
        # Remove the BDEV_APPLICATION_NAME variable if defined so it is not
        # passed to child processes.
        appName = os.environ.pop('BDEV_APPLICATION_NAME', None)
        if name is not None:
            # If a name was passed in, use it instead of the env variable, but still
            # remove the env variable so it doesn't affect child subprocesses.
            appName = name
        if application and appName:
            # This name can be used in filePaths, so remove the invalid separator
            # used by older tools.
            appName = appName.replace('::', '_')
            # If a application name was passed, update the QApplication's
            # application name.
            application.setApplicationName(appName)
            return True
        return False

    def uuid(self):
        """Application specific unique identifier

        Returns:
            None:
        """
        return None

    def toolbar(self, name):
        """Returns the toolbar plugin class for the given name or None.

        In most cases you will want to call ``.instance()`` on the return to get
        the toolbar used in the application. If ``restoreToolbars``` was not called
        you should pass the desired toolbar parent to ``.instance(parent)```.
        """
        for toolbar in self.toolbars():
            if toolbar._name == name:
                return toolbar
        return None

    def toolbars(self):
        """Returns a list of toolbars using the blurdev.toolbars entry_point.

        All toolbars in the entry_point are added to the main window of the application.
        To register a toolbar you need to add a ``blurdev.toolbars`` section in your
        codes setup.py ``entry_point`` section. The key should match your toolbar's
        _name property and the value should be ``the.import.path:ToolbarClass``. See
        blurdev's setup.py for a example.
        """
        if self._toolbars is None:
            # importing pkg_resources takes ~0.8 seconds only import it
            # if we need to.
            import pkg_resources

            bars = pkg_resources.iter_entry_points('blurdev.toolbars')
            # Remove duplicate toolbar definitions. If the pip package is found
            # in sys.path it will show up more than once in bars.
            # example key: `User = blurdev.gui.toolbars.toolstoolbar:UserToolbar`
            entries = {str(entry_point): entry_point for entry_point in bars}
            # Sort the entries alphabetically and resolve the imports
            self._toolbars = [entries[key].load() for key in sorted(entries)]
        return self._toolbars

    def toolTypes(self):
        """
        Determines what types of tools that the treegrunt system should be looking at
        """
        ToolType = blurdev.tools.tool.ToolType
        if self.objectName() == 'multiprocessing':
            import blurdev.external as external

            if external.External().parentCore == 'fusion':
                return ToolType.Fusion
        return ToolType.External | ToolType.LegacyExternal

    def selectedToolTypes(self):
        """Returns a user updated list of ToolTypes to show.
        Returns self.toolTypes() if the user has not set selected tool types.
        """
        if self._selected_tool_types is None:
            return self.toolTypes()
        return self._selected_tool_types

    def setSelectedToolTypes(self, tool_types):
        """Updates selectedToolTypes to the provided list of ToolTypes.

        Args:
            tool_types (blurdev.tools.tool.ToolType): One or more ToolTypes
                |'ed together. None will reset to self.toolTypes()
        """
        self._selected_tool_types = tool_types
        self.selectedToolTypesChanged.emit()

    def treegrunt(self, parent=None):
        """Creates and returns the logger instance"""
        from blurdev.gui.dialogs.treegruntdialog import TreegruntDialog

        return TreegruntDialog.instance(parent)

    def useAppUserModelID(self):
        """Returns a boolean value controlling if calling blurdev.setAppUserModelID
        will do anyting."""
        # Core subclasses Can simply set _useAppUserModelID to True or False if they
        # want to blanket enable or disable setAppUserModelID.
        if self._useAppUserModelID is None:
            # By default allow all core names. If a specific core name needs to be
            # excluded, it should be added to this list.
            return self.objectName() not in ('assfreezer', 'designer')
        return self._useAppUserModelID

    def setUseAppUserModelID(self, value):
        self._useAppUserModelID = value
