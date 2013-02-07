##
# 	\namespace	blurdev.cores.core
#
# 	\remarks	The Core class provides all the main shared functionality and signals that need to be distributed between different
# 				pacakges
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

import sys

from PyQt4.QtCore import QObject, pyqtSignal, QEvent
from PyQt4.QtGui import QApplication
from application import Application
import time, os


class Core(QObject):
    # ----------------------------------------------------------------
    # blurdev signals
    environmentActivated = pyqtSignal()
    debugLevelChanged = pyqtSignal()
    fileCheckedIn = pyqtSignal(str)
    fileCheckedOut = pyqtSignal(str)
    aboutToClearPaths = pyqtSignal()  # emited before environment is changed or reloaded

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
        self._defaultPalette = -1
        self._itemQueue = []
        self._maxDelayPerCycle = 0.1

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
        import sys

        if sys.platform != 'win32':
            return
        import platform

        if platform.architecture()[0] == '64bit':
            app.addLibraryPath("c:/windows/system32/blur64/")
        else:
            app.addLibraryPath("c:/blur/common/")

    def allowErrorMessage(self):
        """
            \Remarks	Override this function to disable showing the 'An error has occurred in your Python script.  Would you like to see the log?'
                        messageBox if a error occurs and the LoggerWindow is not open.
            \Return		<bool>
        """
        return True

    def createDefaultPalette(self):
        import blurdev
        from PyQt4.QtGui import QWidget

        w = QWidget(None)

        import PyQt4.uic

        PyQt4.uic.loadUi(blurdev.resourcePath('palette.ui'), w)

        palette = w.palette()

        w.close()
        w.deleteLater()

        return palette

    def configUpdated(self):
        """
            :remarks	Preform any core specific updating of config. Returns if any actions were taken.
            :return		<bool>
        """
        return False

    def connectAppSignals(self):
        """
            \remarks	[virtual] connect the signals emitted by the application we're in to the blurdev core system
        """
        pass

    def connectPlugin(
        self, hInstance, hwnd, style='Plastique', palette=None, stylesheet=''
    ):
        """
            \remarks	creates a QMfcApp instance for the inputed plugin and window if no app is currently running
            \param		hInstance	<int>
            \param		hwnd		<int>
            \param		style		<str>
            \param		palette		<QPalette>
            \param		stylesheet	<str>
            \return		<bool> success
        """

        # check to see if there is an application already running
        if not QApplication.instance():
            from PyQt4.QtWinMigrate import QMfcApp

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
        """
            \remarks	[virtual] method to create macros for a tool, should be overloaded per core
            
            \param		tool	<trax.api.tools.Tool>
            \param		macro	<str>						specific macro for the tool to run
            
            \return		<bool> success
        """
        # print '[blurdev.cores.core.Core.createToolMacro] virtual method not defined'
        import blurdev

        blurdev.osystem.createShortcut(
            tool.displayName(),
            tool.sourcefile(),
            icon=tool.icon(),
            description=tool.toolTip(),
        )

        return True

    def defaultPalette(self):
        if self._defaultPalette == -1:
            self._defaultPalette = self.createDefaultPalette()
        return self._defaultPalette

    def disableKeystrokes(self):
        # disable the client keystrokes
        self._keysEnabled = False

    def dispatch(self, signal, *args):
        """
            \remarks	dispatches a string based signal through the system from an application
            \param		signal	<str>
            \param		*args	<tuple> additional arguments
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
            from PyQt4.QtCore import SIGNAL

            self.emit(SIGNAL(signal), *args)

        # emit linked signals
        if signal in self._linkedSignals:
            for trigger in self._linkedSignals[signal]:
                self.dispatch(trigger)

    def emitEnvironmentActivated(self):
        if not self.signalsBlocked():
            self.environmentActivated.emit()

    def emitDebugLevelChanged(self):
        if not self.signalsBlocked():
            self.debugLevelChanged.emit()

    def enableKeystrokes(self):
        # enable the client keystrokes
        self._keysEnabled = True

    def errorCoreText(self):
        """
            :remarks	Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
                        If a empty string is returned this line will not be shown in the error email.
            :returns	<str>
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
        """
            \remarks	creates a dependency so that when the inputed signal is dispatched, the dependent trigger signal is also dispatched.  This will only work
                        for trigger signals that do not take any arguments for the dispatch.
            \param		signal		<str>
            \param		trigger		<str>
        """
        if not signal in self._linkedSignals:
            self._linkedSignals[signal] = [trigger]
        elif not trigger in self._linkedSignals[signal]:
            self._linkedSignals[signal].append(trigger)

    def init(self):
        """
            \remarks	initializes the core system
        """
        # register protected modules
        self.protectModule(
            'blurdev'
        )  # do not want to affect this module during environment switching
        # we should never remove main. If we do in specific cases it will prevent external tools from
        # running if they use "if __name__ == '__main__':" as __name__ will return None
        self.protectModule('__main__')

        # initialize the tools environments
        import blurdev
        from blurdev.tools import ToolsEnvironment

        ToolsEnvironment.loadConfig(blurdev.resourcePath('tools_environments.xml'))

        # initialize the application
        app = QApplication.instance()
        output = None

        if app:
            if self.isMfcApp():
                from PyQt4.QtCore import Qt

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
        elif not app:
            output = Application([])
            self.addLibraryPaths(output)

        # restore the core settings
        self.restoreSettings()
        self.registerPaths()
        self.connectAppSignals()

        self.restoreToolbar()

        return output

    def isMfcApp(self):
        return self._mfcApp

    def hwnd(self):
        return self._hwnd

    def ideeditor(self, parent=None):
        from blurdev.ide.ideeditor import IdeEditor

        return IdeEditor.instance(parent)

    def isKeystrokesEnabled(self):
        return self._keysEnabled

    def lastFileName(self):
        return self._lastFileName

    def logger(self, parent=None):
        """
            \remarks	creates and returns the logger instance
        """
        from blurdev.gui.windows.loggerwindow import LoggerWindow

        return LoggerWindow.instance(parent)

    def lovebar(self, parent=None):
        from blurdev.tools.toolslovebar import ToolsLoveBarDialog

        return ToolsLoveBarDialog.instance(parent)

    def macroName(self):
        """
            \Remarks	Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Desktop Shortcut...'

    def maxDelayPerCycle(self):
        return self._maxDelayPerCycle

    def newScript(self):
        """
            \remarks	creates a new script window for editing
        """
        from blurdev.ide import IdeEditor

        IdeEditor.createNew()

    def openScript(self, filename=''):
        """
            \remarks	opens the an existing script in a new window for editing
        """
        if not filename:
            from PyQt4.QtGui import QFileDialog

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

            from blurdev.ide import IdeEditor

            IdeEditor.edit(filename=filename)

    def postQueueEvent(self):
        """
            \remarks	Insert a call to processQueueItem on the next event loop
        """
        QApplication.postEvent(self, QEvent(self.qProcessID))

    def processQueueItem(self):
        """
            \remarks	Call the current queue item and post the next queue event if it exists
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
            \Remarks	Process the top item on the queue, catch the error generated if the underlying c/c++ object has been deleted, and alow the queue to continue processing.
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
            \remarks	registers the inputed module name for protection from tools environment switching
            \param		moduleName	<str> || <QString>
        """
        key = str(moduleName)
        if not key in self._protectedModules:
            self._protectedModules.append(str(moduleName))

    def protectedModules(self):
        """
            \remarks	returns the modules that should not be affected when a tools environment changes
            \return		<list> [ <str> ]
        """
        return self._protectedModules

    def pyular(self, parent=None):
        from blurdev.gui.widgets.pyularwidget import PyularDialog

        return PyularDialog.instance(parent)

    def registerPaths(self):
        """
            \remarks	registers the paths that are needed based on this core
        """
        from blurdev.tools import ToolsEnvironment

        env = ToolsEnvironment.activeEnvironment()
        env.registerPath(env.relativePath('maxscript/treegrunt/lib'))
        env.registerPath(env.relativePath('code/python/lib'))

        # Canonical way to check 64-bitness of python interpreter
        # http://docs.python.org/2/library/platform.html#platform.architecture
        is_64bits = hasattr(sys, 'maxsize') and sys.maxsize > (2 ** 32)
        # Add Python26 specific libraries
        if sys.version_info[:2] == (2, 6):
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
        r"""
            \remarks	Subclasses can reimplement this to add data before it is saved
        """
        pref = self.recordCoreSettings()
        pref.save()

    def recordCoreSettings(self):
        from blurdev import prefs

        pref = prefs.find('blurdev/core', coreName=self.objectName())

        # record the tools environment
        from blurdev.tools import ToolsEnvironment

        pref.recordProperty(
            'environment', ToolsEnvironment.activeEnvironment().objectName()
        )

        # record the debug
        from blurdev import debug

        pref.recordProperty('debugLevel', debug.debugLevel())

        return pref

    def recordToolbar(self):
        from blurdev import prefs

        pref = prefs.find('blurdev/toolbar', coreName=self.objectName())

        # record the toolbar
        child = pref.root().findChild('toolbardialog')

        # remove the old instance
        if child:
            child.remove()

        from blurdev.tools.toolstoolbar import ToolsToolBarDialog

        if ToolsToolBarDialog._instance:
            ToolsToolBarDialog._instance.toXml(pref.root())

        pref.save()

    def restoreSettings(self):
        self.blockSignals(True)

        from blurdev import prefs
        from blurdev.tools import ToolsEnvironment, TEMPORARY_TOOLS_ENV

        pref = prefs.find('blurdev/core', coreName=self.objectName())

        # If the environment variable BLURDEV_PATH is defined create a custom environment instead of using the loaded environment
        environPath = os.environ.get('BLURDEV_PATH')
        if environPath:
            env = ToolsEnvironment.findEnvironment(TEMPORARY_TOOLS_ENV)
            if env.isEmpty():
                env = ToolsEnvironment.createNewEnvironment(
                    TEMPORARY_TOOLS_ENV, environPath
                )
                env.setEmailOnError([os.environ.get('BLURDEV_ERROR_EMAIL')])
            env.setActive()
        else:
            # restore the active environment
            env = pref.restoreProperty('environment')
            if env:
                ToolsEnvironment.findEnvironment(env).setActive()

        # restore the active debug level
        level = pref.restoreProperty('debugLevel')
        if level != None:
            from blurdev import debug

            debug.setDebugLevel(level)

        self.blockSignals(False)
        return pref

    def restoreToolbar(self):
        from blurdev import prefs

        pref = prefs.find('blurdev/toolbar', coreName=self.objectName())

        # restore the toolbar
        child = pref.root().findChild('toolbardialog')
        if child:
            self.toolbar().fromXml(pref.root())

    def rootWindow(self):
        """
            \remarks	returns the currently active window
            \return		<QWidget> || None
        """
        # for MFC apps there should be no root window
        if self.isMfcApp():
            return None

        window = None
        if QApplication.instance():
            window = QApplication.instance().activeWindow()

            # grab the root window
            if window:
                while window.parent():
                    window = window.parent()

        return window

    def runDelayed(self, function, *args, **kargs):
        """
            \remarks	Alternative to a for loop that will not block the ui. Each item added with this method will be processed during a single application event loop. If you add 5 items with runDelayed it will process the first item, update the ui, process the second item, update the ui, etc. This is usefull if you have a large amount of items to process, but processing of a individual item does not take a long time. Also it does not need to happen immediately.
            \param		function		<function>	The function to call when ready to process.
            \param		*args, **kargs	<list> || <dict>	any arguments that need to be called on function
            \sa			<blurdev.core.runDelayedReplace>, <blurdev.core._runDelayed>
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
            \remarks	Same as the runDelayed, but will check if the queue contains a matching function, *args, and **kargs. If found it will remove it and append it at the end of the queue.
        """
        self._runDelayed(function, True, *args, **kargs)

    def isDelayed(self, function, *args, **kwargs):
        """
            \remarks	Is the supplied function and arguments are in the runDelayed queue
            \return		<bool>
        """
        if (function, args, kargs) in self._itemQueue:
            return True
        return False

    def _runDelayed(self, function, replace, *args, **kargs):
        """
            \remarks	Alternative to a for loop that will not block the ui. Each item added with this method will be processed during a single application event loop.
                        If you add 5 items with runDelayed it will process the first item, update the ui, process the second item, update the ui, etc.
                        This is usefull if you have a large amount of items to process, but processing of a individual item does not take a long time. Also it does not
                        need to happen immediately.
            \param		function	<>	The function to call when ready to process.
            \param		replace		<bool>	If true, it will attempt to remove the first item in the queue with matching function, *args, **kargs
            \param		*args, **kargs	any arguments that need to be called on function
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
            \remarks	[virtual] Runs a macro command
            \param		command 	<str>		command to run
            \return		<bool> success
        """
        print '[blurdev.cores.core.Core.runMacro] virtual method not defined'
        return False

    def runStandalone(
        self, filename, debugLevel=None, basePath='', environ=None, paths=None
    ):
        from blurdev import osystem

        osystem.startfile(filename, debugLevel, basePath)

    def runScript(self, filename='', scope=None, argv=None, toolType=None):
        """
            \remarks	Runs an inputed file in the best way this core knows how
            
            \param		filename	<str>
            \param		scope		<dict> || None						the scope to run the script in
            \param		argv		<list> [ <str> cmd, .. ] || None	commands to pass to the script at run time
            \param		toolType	<ToolType>							determines the tool type for this tool
            
            \return		<bool> success
        """
        import sys
        from PyQt4.QtGui import QFileDialog, QMessageBox

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
        if scope == None:
            scope = {}

        filename = str(filename)

        # run the script
        from blurdev import debug
        import os

        if filename and os.path.exists(filename):
            self._lastFileName = filename

            ext = os.path.splitext(filename)[1]

            from blurdev.tools import ToolType, ToolsEnvironment

            # always run legacy external tools as standalone - they can cause QApplication conflicts
            if toolType == ToolType.LegacyExternal:
                import os

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
                    ToolsEnvironment.registerScriptPath(filename)

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
                try:
                    import PeyeonScript as eyeon
                except:
                    eyeon = None

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
            \Remarks	Run delayed will process as many items as it can within this time frame every event loop. 
                        Seconds is a float value for seconds. If seconds is -1 it will only process 1 item per event loop.
                        This value does not limit the cycle, it just prevents a new queue item from being called if the total
                        time exceeds this value. If your queue items will take almost the full time, you may want to set this value to -1.
            \Param		seconds	<float>
        """
        self._maxDelayPerCycle = seconds

    def sendEmail(self, sender, targets, subject, message, attachments=None):
        """
            :remarks	Sends a email.
            :param		sender		<string>	The source email address.
            :param		targets		<string>||<list>||<tuple>	The email address(s) to send the email to.
            :param		subject		<string>	The subject of the email.
            :param		message		<string>	The body of the message. Treated as html
            :param		attachments	<list>		File paths for files to be attached.
        """
        from email import Encoders
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase

        output = MIMEMultipart()
        output['Subject'] = str(subject)
        output['From'] = str(sender)

        # convert to string
        if type(targets) in (tuple, list):
            output['To'] = ', '.join(targets)
        else:
            output['To'] = str(targets)

        from PyQt4.QtCore import QDateTime

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
                txt.add_header('Content-Disposition', 'attachment; filename="%s"' % a)
                output.attach(txt)

        import smtplib

        smtp = smtplib.SMTP()

        smtp.connect('mail.blur.com')
        smtp.sendmail(str(sender), output['To'].split(','), str(output.as_string()))

        smtp.close()

    def setObjectName(self, objectName):
        if objectName != self.objectName():
            QObject.setObjectName(self, objectName)

            # clear the caching environments
            from blurdev import prefs

            prefs.clearCache()

            # make sure we have the proper settings restored based on the new application
            self.restoreSettings()

    def shutdown(self):

        # record the settings
        self.recordToolbar()
        self.recordSettings()

        if QApplication.instance():
            QApplication.instance().closeAllWindows()
            QApplication.instance().quit()

    def showIdeEditor(self):
        from blurdev.ide import IdeEditor

        IdeEditor.instance().edit()

    def showToolbar(self, parent=None):
        from blurdev.tools.toolstoolbar import ToolsToolBarDialog

        ToolsToolBarDialog.instance(parent).show()

    def showLovebar(self, parent=None):
        from blurdev.tools.toolslovebar import ToolsLoveBarDialog

        ToolsLoveBarDialog.instance(parent).show()

    def showPyular(self, parent=None):
        from blurdev.gui.widgets.pyularwidget import PyularDialog

        PyularDialog.instance(parent).show()

    def showTreegrunt(self):
        self.treegrunt().show()

    def showLogger(self):
        """
            \remarks	creates the python logger and displays it
        """
        logger = self.logger()
        logger.show()
        logger.activateWindow()
        logger.raise_()
        logger.console().setFocus()

    def unprotectModule(self, moduleName):
        """
            \remarks	removes the inputed module name from protection from tools environment switching
            \param		moduleName	<str> || <QString>
        """
        key = str(moduleName)
        while key in self._protectedModules:
            self._protectedModules.remove(key)

    def toolbar(self, parent=None):
        from blurdev.tools.toolstoolbar import ToolsToolBarDialog

        return ToolsToolBarDialog.instance(parent)

    def toolTypes(self):
        """
            \remarks	Virtual method to determine what types of tools that the trax system should be looking at
            \return		<trax.api.tools.ToolType>
        """
        from blurdev.tools import ToolsEnvironment, ToolType

        output = ToolType.External | ToolType.Fusion | ToolType.LegacyExternal

        return output

    def treegrunt(self, parent=None):
        """
            \remarks	creates and returns the logger instance
        """
        from blurdev.gui.dialogs.treegruntdialog import TreegruntDialog

        return TreegruntDialog.instance(parent)
