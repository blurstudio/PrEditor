import sys
import time
import os
import glob
import platform
from email import Encoders
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
import smtplib

from PyQt4.QtCore import QObject, pyqtSignal, QEvent, QDateTime, Qt, SIGNAL
from PyQt4.QtGui import QApplication, QWidget, QFileDialog, QMessageBox, QSplashScreen
import PyQt4.uic

if sys.platform == 'win32':  # shitty
    from PyQt4.QtWinMigrate import QMfcApp
try:
    import PeyeonScript as eyeon
except ImportError:
    eyeon = None

import blurdev
import blurdev.prefs
import blurdev.debug
import blurdev.XML
import blurdev.osystem
import blurdev.tools
import blurdev.tools.tool
import blurdev.tools.toolsenvironment
import blurdev.tools.toolslovebar
import blurdev.tools.toolstoolbar

if hasattr('PyQt4', 'Qsci'):
    import blurdev.ide.ideeditor
import blurdev.cores.application
from application import Application


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to be distributed between different pacakges.
    """

    # ----------------------------------------------------------------
    # blurdev signals
    environmentActivated = pyqtSignal()
    debugLevelChanged = pyqtSignal()
    fileCheckedIn = pyqtSignal(str)
    fileCheckedOut = pyqtSignal(str)
    aboutToClearPaths = pyqtSignal()  # emited before environment is changed or reloaded
    styleSheetChanged = pyqtSignal(str)

    # ----------------------------------------------------------------
    # 3d Application Signals (common)
    # Depreciated, use blur3d signals

    # scene signals
    sceneClosed = pyqtSignal()
    sceneExportRequested = pyqtSignal()
    sceneExportFinished = pyqtSignal()
    sceneImportRequested = pyqtSignal()
    sceneImportFinished = pyqtSignal()
    sceneInvalidated = pyqtSignal()
    sceneMergeRequested = pyqtSignal()
    sceneMergeFinished = pyqtSignal()
    sceneNewRequested = pyqtSignal()
    sceneNewFinished = pyqtSignal()
    sceneOpenRequested = pyqtSignal(str)
    sceneOpenFinished = pyqtSignal(str)
    sceneReset = pyqtSignal()
    sceneSaveRequested = pyqtSignal(str)
    sceneSaveFinished = pyqtSignal(str)

    # layer signals
    layerCreated = pyqtSignal()
    layerDeleted = pyqtSignal()
    layersModified = pyqtSignal()
    layerStateChanged = pyqtSignal()

    # object signals
    selectionChanged = pyqtSignal()

    # render signals
    rednerFrameRequested = pyqtSignal(int)
    renderFrameFinished = pyqtSignal()
    renderSceneRequested = pyqtSignal(list)
    renderSceneFinished = pyqtSignal()

    # time signals
    currentFrameChanged = pyqtSignal(int)
    frameRangeChanged = pyqtSignal()

    # application signals
    startupFinished = pyqtSignal()
    shutdownStarted = pyqtSignal()

    # the event id for Queue Processing
    qProcessID = 15648

    # ----------------------------------------------------------------

    def __init__(self, hwnd=0):
        QObject.__init__(self)
        QObject.setObjectName(self, 'blurdev')

        # create custom properties
        self._protectedModules = []
        self._hwnd = hwnd
        self._keysEnabled = True
        self._lastFileName = ''
        self._mfcApp = False
        self._logger = None
        self._linkedSignals = {}
        self._itemQueue = []
        self._maxDelayPerCycle = 0.1
        self._stylesheet = None
        self.environment_override_filepath = os.environ.get(
            'bdev_environment_override_filepath', ''
        )

        # create the connection to the environment activiation signal
        self.environmentActivated.connect(self.registerPaths)
        self.environmentActivated.connect(self.recordSettings)
        self.debugLevelChanged.connect(self.recordSettings)

    def activeWindow(self):
        if QApplication.instance():
            return QApplication.instance().activeWindow()
        return None

    def addLibraryPaths(self, app):
        # Set library paths so qt plugins, image formats, sql drivers, etc can be loaded if needed
        if sys.platform != 'win32':
            return
        if platform.architecture()[0] == '64bit':
            app.addLibraryPath("c:/windows/system32/blur64/")
        else:
            app.addLibraryPath("c:/blur/common/")

    def configUpdated(self):
        """ Preform any core specific updating of config. Returns if any actions were taken.
        """
        return False

    def connectAppSignals(self):
        """ Connect the signals emitted by the application we're in to the blurdev core system
        """
        pass

    def connectPlugin(
        self, hInstance, hwnd, style='Plastique', palette=None, stylesheet=''
    ):
        """ Creates a QMfcApp instance for the inputed plugin and window if no app is currently running
            
            :param int hInstance:
            :param int hwnd:
            :param str style:
            :param QPalette palette:
            :param str stylesheet:
            :returns: bool for success
            
        """

        # check to see if there is an application already running
        if not QApplication.instance():
            # create the plugin instance
            if QMfcApp.pluginInstance(hInstance):
                self.setHwnd(hwnd)
                self._mfcApp = True

                app = QApplication.instance()
                if app:
                    app.setStyle(style)
                    if palette:
                        app.setPalette(palette)
                    if stylesheet:
                        app.setStylesheet(stylesheet)

                    # initialize the logger
                    self.logger()

                return True
        return False

    def createToolMacro(self, tool, macro=''):
        """ Method to create macros for a tool, should be overloaded per core
        """
        blurdev.osystem.createShortcut(
            tool.displayName(),
            tool.sourcefile(),
            icon=tool.icon(),
            description=tool.toolTip(),
        )

        return True

    def disableKeystrokes(self):
        # disable the client keystrokes
        self._keysEnabled = False

    def dispatch(self, signal, *args):
        """ Dispatches a string based signal through the system from an application
        """
        if self.signalsBlocked():
            return

        # emit a defined pyqtSignal
        if (
            hasattr(self, signal)
            and type(getattr(self, signal)).__name__ == 'pyqtBoundSignal'
        ):
            getattr(self, signal).emit(*args)

        # otherwise emit a custom signal
        else:
            self.emit(SIGNAL(signal), *args)

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

    def errorCoreText(self):
        """ Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
            If a empty string is returned this line will not be shown in the error email.
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
        """ Creates a dependency so that when the inputed signal is dispatched, the dependent trigger signal is also dispatched.  This will only work
            for trigger signals that do not take any arguments for the dispatch.
        """
        if not signal in self._linkedSignals:
            self._linkedSignals[signal] = [trigger]
        elif not trigger in self._linkedSignals[signal]:
            self._linkedSignals[signal].append(trigger)

    def init(self):
        """ Initializes the core system
        """
        # register protected modules
        # do not want to affect this module during environment switching
        self.protectModule('blurdev')
        # we should never remove main. If we do in specific cases it will prevent external tools from
        # running if they use "if __name__ == '__main__':" as __name__ will return None
        self.protectModule('__main__')

        # initialize the tools environments
        blurdev.tools.toolsenvironment.ToolsEnvironment.loadConfig(
            blurdev.resourcePath('tools_environments.xml')
        )

        # 		# Gets the override filepath, it is defined this way, instead of
        # 		# being defined in the class definition, so that we can change this
        # 		# path, or remove it entirely for offline installs.
        # 		self.environment_override_filepath = os.environ.get('bdev_environment_override_filepath', '')

        # initialize the application
        app = QApplication.instance()
        output = None

        if app:
            if self.isMfcApp():
                # disable all UI effects as this is quite slow in MFC applications
                app.setEffectEnabled(Qt.UI_AnimateMenu, False)
                app.setEffectEnabled(Qt.UI_FadeMenu, False)
                app.setEffectEnabled(Qt.UI_AnimateCombo, False)
                app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
                app.setEffectEnabled(Qt.UI_FadeTooltip, False)
                app.setEffectEnabled(Qt.UI_AnimateToolBox, False)
                app.aboutToQuit.connect(self.recordToolbar)
                app.installEventFilter(self)
            self.addLibraryPaths(app)

        # create a new application
        else:
            output = blurdev.cores.application.Application([])
            self.addLibraryPaths(output)

        # restore the core settings
        self.restoreSettings()
        self.connectAppSignals()
        self.restoreToolbar()
        return output

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

        if not last_timestamp:
            return

        if last_timestamp < threshold_time:
            blurdev.tools.toolsenvironment.ToolsEnvironment.defaultEnvironment().setActive()
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

    def hwnd(self):
        return self._hwnd

    def ideeditor(self, parent=None):
        return blurdev.ide.ideeditor.IdeEditor.instance(parent)

    def isKeystrokesEnabled(self):
        return self._keysEnabled

    def lastFileName(self):
        return self._lastFileName

    def logger(self, parent=None):
        """ Creates and returns the logger instance
        """
        import blurdev.gui.windows.loggerwindow

        return blurdev.gui.windows.loggerwindow.LoggerWindow.instance(parent)

    def lovebar(self, parent=None):

        return blurdev.tools.toolslovebar.ToolsLoveBarDialog.instance(parent)

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Desktop Shortcut...'

    def maxDelayPerCycle(self):
        return self._maxDelayPerCycle

    def newScript(self):
        """
        Creates a new script window for editing
        """
        blurdev.ide.ideeditor.IdeEditor.createNew()

    def openScript(self, filename=''):
        """
        Opens the an existing script in a new window for editing
        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename = str(
                    QFileDialog.getOpenFileName(
                        None,
                        'Select Script File',
                        self._lastFileName,
                        'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                    )
                )
                if not filename:
                    return

        if filename:
            self._lastFileName = filename
            blurdev.ide.ideeditor.IdeEditor.edit(filename=filename)

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
        Process the top item on the queue, catch the error generated if the underlying c/c++ object has been deleted, and alow the queue to continue processing.
        """
        try:
            item = self._itemQueue.pop(0)
            item[0](*item[1], **item[2])
        except RuntimeError, check:
            if str(check) != 'underlying C/C++ object has been deleted':
                if self._itemQueue:
                    self.postQueueEvent()
                raise
        except Exception, value:
            if self._itemQueue:
                self.postQueueEvent()
            raise

    def protectModule(self, moduleName):
        """
        Registers the inputed module name for protection from tools environment switching
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
        import blurdev.gui.widgets.pyularwidget

        return blurdev.gui.widgets.pyularwidget.PyularDialog.instance(parent)

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
        env.registerPath(env.relativePath('maxscript/treegrunt/lib'))
        env.registerPath(env.relativePath('code/python/lib'))

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
        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())

        # record the tools environment
        pref.recordProperty(
            'environment',
            blurdev.tools.toolsenvironment.ToolsEnvironment.activeEnvironment().objectName(),
        )

        # record the debug
        pref.recordProperty('debugLevel', blurdev.debug.debugLevel())

        # record the tools style
        pref.recordProperty('style', self._stylesheet)

        return pref

    def recordToolbar(self):
        pref = blurdev.prefs.find('blurdev/toolbar', coreName=self.objectName())

        # record the toolbar
        child = pref.root().findChild('toolbardialog')

        # remove the old instance
        if child:
            child.remove()

        if blurdev.tools.toolstoolbar.ToolsToolBarDialog._instance:
            blurdev.tools.toolstoolbar.ToolsToolBarDialog._instance.toXml(pref.root())

        pref.save()

    def createEnvironmentOverride(self, env=None, timestamp=None):
        if env is None:
            env = (
                blurdev.tools.toolsenvironment.ToolsEnvironment.defaultEnvironment().objectName()
            )
        if timestamp is None:
            timestamp = QDateTime.currentDateTime()

        fp = self.environment_override_filepath
        if not fp:
            return

        doc = blurdev.XML.XMLDocument()
        root = doc.addNode('environment_overrides')
        root.setAttribute('version', 1.0)
        el = root.addNode('environment_override')
        el.setAttribute('environment', unicode(env))
        el.setAttribute('timestamp', unicode(timestamp.toString('yyyy-MM-dd hh:mm:ss')))
        try:
            doc.save(fp)
        except Exception:
            pass

    def getEnvironmentOverride(self):
        doc = blurdev.XML.XMLDocument()
        self.environment_override_filepath = os.environ.get(
            'bdev_environment_override_filepath', ''
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
        self.blockSignals(True)
        TEMPORARY_TOOLS_ENV = blurdev.tools.TEMPORARY_TOOLS_ENV
        ToolsEnvironment = blurdev.tools.toolsenvironment.ToolsEnvironment

        pref = blurdev.prefs.find('blurdev/core', coreName=self.objectName())

        # If the environment variable BLURDEV_PATH is defined create a custom environment instead of using the loaded environment
        environPath = os.environ.get('BLURDEV_PATH')
        if environPath:
            env = ToolsEnvironment.findEnvironment(TEMPORARY_TOOLS_ENV)
            if env.isEmpty():
                env = ToolsEnvironment.createNewEnvironment(
                    TEMPORARY_TOOLS_ENV, environPath
                )
                env.setEmailOnError([os.environ.get('BLURDEV_ERROR_EMAIL')])
                env.setTemporary(True)
            env.setActive()
        else:
            # restore the active environment
            env = pref.restoreProperty('environment')
            if env:
                ToolsEnvironment.findEnvironment(env).setActive()

        # restore the active debug level
        level = pref.restoreProperty('debugLevel')
        if level is not None:
            blurdev.debug.setDebugLevel(level)

        # restore the active style
        self.setStyleSheet(
            os.environ.get('BDEV_STYLESHEET') or pref.restoreProperty('style'),
            recordPrefs=False,
        )

        self.blockSignals(False)

        self.applyEnvironmentTimeouts()
        self.applyStudioOverrides()
        # Ensure the core has its paths registered
        self.registerPaths()

        return pref

    def restoreToolbar(self):
        pref = blurdev.prefs.find('blurdev/toolbar', coreName=self.objectName())
        # restore the toolbar
        child = pref.root().findChild('toolbardialog')
        if child:
            self.toolbar().fromXml(pref.root())

    def rootWindow(self):
        """
        Returns the currently active window
        """
        # for MFC apps there should be no root window
        if self.isMfcApp():
            return None

        window = None
        if QApplication.instance():
            window = QApplication.instance().activeWindow()
            # Ignore QSplashScreen's, they should never be considered the root window.
            if isinstance(window, QSplashScreen):
                return None

            # grab the root window
            if window:
                while window.parent():
                    parent = window.parent()
                    if isinstance(parent, QSplashScreen):
                        return window
                    else:
                        window = parent

        return window

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
        Same as the runDelayed, but will check if the queue contains a matching function, *args, and **kargs. If found it will remove it and append it at the end of the queue.
        """
        self._runDelayed(function, True, *args, **kargs)

    def isDelayed(self, function, *args, **kwargs):
        """
        Is the supplied function and arguments are in the runDelayed queue
        """
        if (function, args, kargs) in self._itemQueue:
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
        :param bool replace: If true, it will attempt to remove the first item in the queue with matching function, *args, **kargs
        
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
        print '[blurdev.cores.core.Core.runMacro] virtual method not defined'
        return False

    def runStandalone(
        self, filename, debugLevel=None, basePath='', environ=None, paths=None
    ):
        blurdev.osystem.startfile(filename, debugLevel, basePath)

    def runScript(self, filename='', scope=None, argv=None, toolType=None):
        """
        Runs an inputed file in the best way this core knows how
            
        :param str filename:
        :param dict scope: The scope to run the script in (ie. locals(), globals())
        :param list argv: Commands to pass to the script at run time
        :param toolType: determines the tool type for this tool

        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename = str(
                    QFileDialog.getOpenFileName(
                        None,
                        'Select Script File',
                        self._lastFileName,
                        'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                    )
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

            # always run legacy external tools as standalone - they can cause QApplication conflicts
            if toolType == blurdev.tools.tool.ToolType.LegacyExternal:
                os.startfile(filename)

            # run a python file
            elif ext.startswith('.py'):
                # if running in external mode, run a standalone version for python files - this way they won't try to parent to the treegrunt
                if self.objectName() in ('external', 'treegrunt'):
                    self.runStandalone(filename)
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

                    execfile(filename, scope)

                    # restore the system information
                    sys.path = path_bak
                    if argv_bak:
                        sys.argv = argv_bak

                return True

            # run a fusion script
            elif ext.startswith('.eyeonscript'):
                if eyeon:
                    fusion = eyeon.scriptapp('Fusion')
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
                print '[blurdev.cores.core.Core.runScript] Cannot run scripts of type (*%s)' % ext

        return False

    def sdkBrowser(self, parent=None):
        from blurdev.gui.windows.sdkwindow import SdkWindow

        return SdkWindow.instance(parent)

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

    def sendEmail(self, sender, targets, subject, message, attachments=None):
        """
        Sends an email.
        
        :param str sender: The source email address.
        :param targets: A single email string, or a list of email address(s) to send the email to.
        :param str subject: The subject of the email.
        :param str message: The body of the message. Treated as html
        :param list attachments: File paths for files to be attached.
        
        """
        output = MIMEMultipart()
        output['Subject'] = str(subject)
        output['From'] = str(sender)

        # convert to string
        if isinstance(targets, (tuple, list)):
            output['To'] = ', '.join(targets)
        else:
            output['To'] = str(targets)

        output['Date'] = str(
            QDateTime.currentDateTime().toString('ddd, d MMM yyyy hh:mm:ss')
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

        smtp = smtplib.SMTP()
        smtp.connect(os.environ.get('BDEV_SEND_EMAIL_SERVER', 'mail.blur.com'))
        smtp.sendmail(str(sender), output['To'].split(','), str(output.as_string()))
        smtp.close()

    def setObjectName(self, objectName):
        if objectName != self.objectName():
            QObject.setObjectName(self, objectName)
            blurdev.prefs.clearCache()
            # make sure we have the proper settings restored based on the new application
            self.restoreSettings()

    def setStyleSheet(self, stylesheet, recordPrefs=True):
        """ Accepts the name of a stylesheet included with blurdev, or a full
            path to any stylesheet.  If given None, it will remove the 
            stylesheet.
        """
        app = QApplication.instance()
        if app and isinstance(
            app, QApplication
        ):  # Don't set stylesheet if QCoreApplication
            if stylesheet is None or stylesheet == 'None':
                app.setStyleSheet('')
                self._stylesheet = None
            elif os.path.isfile(stylesheet):
                with open(stylesheet) as f:
                    app.setStyleSheet(f.read())
                self._stylesheet = stylesheet
            else:
                # Try to find an installed stylesheet with the given name
                path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'resource',
                    'stylesheet',
                    '{}.css'.format(stylesheet),
                )
                if os.path.isfile(path):
                    with open(path) as f:
                        app.setStyleSheet(f.read())
                    self._stylesheet = stylesheet

        if self.objectName() != 'blurdev':
            # Storing the stylesheet as an environment variable for other external tools.
            os.environ['BDEV_STYLESHEET'] = str(stylesheet)

            if recordPrefs:
                # Recording preferences.
                self.recordSettings()
        # Notify widgets of the stylesheet change
        self.styleSheetChanged.emit(str(stylesheet))

    def styleSheet(self):
        """ Returns the name of the current stylesheet.
        """
        return self._stylesheet

    def styleSheets(self):
        """ Returns a list of installed stylesheet names.
        """
        cssdir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'resource',
            'stylesheet',
        )
        cssfiles = glob.glob(os.path.join(cssdir, '*.css'))
        # Only return the filename without the .css extension
        return [os.path.splitext(os.path.basename(fp))[0] for fp in cssfiles]

    def shutdown(self):
        # record the settings
        self.recordToolbar()
        self.recordSettings()

        if QApplication.instance():
            QApplication.instance().closeAllWindows()
            QApplication.instance().quit()

    def showIdeEditor(self):
        blurdev.ide.ideeditor.IdeEditor.instance().edit()

    def showToolbar(self, parent=None):
        blurdev.tools.toolstoolbar.ToolsToolBarDialog.instance(parent).show()

    def showLovebar(self, parent=None):
        blurdev.tools.toolslovebar.ToolsLoveBarDialog.instance(parent).show()

    def showPyular(self, parent=None):
        self.pyular(parent).show()

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

    def unprotectModule(self, moduleName):
        """
        Removes the inputed module name from protection from tools environment switching
        """
        key = str(moduleName)
        while key in self._protectedModules:
            self._protectedModules.remove(key)

    def toolbar(self, parent=None):
        return blurdev.tools.toolstoolbar.ToolsToolBarDialog.instance(parent)

    def toolTypes(self):
        """
        Determines what types of tools that the trax system should be looking at
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.External | ToolType.Fusion | ToolType.LegacyExternal
        return output

    def treegrunt(self, parent=None):
        """ Creates and returns the logger instance
        """
        from blurdev.gui.dialogs.treegruntdialog import TreegruntDialog

        return TreegruntDialog.instance(parent)
