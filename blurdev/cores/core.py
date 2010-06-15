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

from PyQt4.QtCore import QObject, pyqtSignal
from blurdev.tools import ToolsEnvironment


class Core(QObject):
    # CUSTOM SIGNALS
    environmentActivated = pyqtSignal(
        ToolsEnvironment, ToolsEnvironment
    )  # emits that the environment has changed from old to new

    # COMMON SIGNALS

    # \params : frame number
    currentFrameChanged = pyqtSignal(
        int
    )  # emitted when the current frame has been updated				( 3dsMax | Softimage )
    fileExportRequested = (
        pyqtSignal()
    )  # emitted before a client is about to export a file			 	( 3dsMax | Softimage )
    fileExportFinished = (
        pyqtSignal()
    )  # emitted after a client has finished exporting a file			( 3dsMax | Softimage )
    fileImportRequested = (
        pyqtSignal()
    )  # emitted before a client is about to import a file				( 3dsMax | Softimage )
    fileImportFinished = (
        pyqtSignal()
    )  # emitted after a client has finished importing a file			( 3dsMax | Softimage )
    objectAdded = (
        pyqtSignal()
    )  # emitted after a client has created a new scene object			( 3dsMax | Softimage )
    objectRemoved = (
        pyqtSignal()
    )  # emitted after a client has removed a scene object				( 3dsMax | Softimage )

    #  Softimage \params : RenderType, FileName, Frame, Sequence, RenderField
    renderFrameRequested = pyqtSignal(
        int, str, int, int, int
    )  # emitted when a client is going to render a frame				( 3dsMax | Softimage )
    renderFrameFinished = pyqtSignal(
        int, str, int, int, int
    )  # emitted when a client has finished rendering a frame			( 3dsMax | Softimage )

    sceneClosed = (
        pyqtSignal()
    )  # emitted when a client has closed a scene file					( 3dsMax | Softimage )
    sceneNewRequested = (
        pyqtSignal()
    )  # emitted when a client is requesting a new scene				( 3dsMax | Softimage )
    sceneNewFinished = (
        pyqtSignal()
    )  # emitted when a client has created a new scene					( 3dsMax | Softimage )

    # \params : filename
    sceneOpenRequested = pyqtSignal(
        str
    )  # emitted when a client is attempting to open a scene			( 3dsMax | Softiamge )
    sceneOpenFinished = pyqtSignal(
        str
    )  # emitted when a client is finished opening a scene				( 3dsMax | Softimage )
    sceneSaveRequested = (
        pyqtSignal()
    )  # emitted when a client is attempting to save a scene			( 3dsMax | Softimage )
    sceneSaveFinished = (
        pyqtSignal()
    )  # emitted when a client is done saving a scene					( 3dsMax | Softimage )

    # \params : filename
    sceneSaveAsRequested = pyqtSignal(
        str
    )  # emitted when a client is attempting to save a scene			( 3dsMax | Softimage )
    sceneSaveAsFinished = pyqtSignal(
        str
    )  # emitted when a client is done saving a scene to a filename	( 3dsMax | Softimage )
    selectionChanged = (
        pyqtSignal()
    )  # emitted when a client has changed its selection				( 3dsMax | Softimage )

    # SOFTIMAGE SPECIFIC SIGNALS

    # \params : old project, new project
    projectChanged = pyqtSignal(
        str, str
    )  # emitted after a project has been changed						( Softimage )
    refModelSaved = (
        pyqtSignal()
    )  # emitted after a reference model has been saved				( Softimage )
    refModelLoadRequested = (
        pyqtSignal()
    )  # emitted when a model load requested							( Softimage )
    refModelLoadFinished = (
        pyqtSignal()
    )  # emitted when a model is finished loading						( Softimage )

    # \params : RenderType, Filename, Frame, Sequence, RenderField
    sequenceRenderRequested = pyqtSignal(
        int, str, int, int, int
    )  # emitted when a squence is requested to render					( Softimage )
    sequenceRenderFinished = pyqtSignal(
        int, str, int, int, int
    )  # emitted when a sequence is finished rendering					( Softimage )

    # \params : object, fullname, previous value
    valueChanged = pyqtSignal(
        str, str, str
    )  # emitted when an objects value has changed						( Softimage )

    def __init__(self, hwnd=0):
        QObject.__init__(self)

        self.setObjectName('blurdev')

        # create custom properties
        self._protectedModules = []
        self._hwnd = hwnd
        self._keysEnabled = True
        self._lastFileName = ''
        self._mfcApp = False
        self._logger = None
        self._rootWidgets = []

        # create the connection to the environment activiation signal
        self.environmentActivated.connect(self.registerPaths)

    def activeWindow(self):
        """
            \remarks	returns the currently active window
            \return		<QWidget> || None
        """
        from PyQt4.QtGui import QApplication

        window = None
        if QApplication.instance():
            window = QApplication.instance().activeWindow()

            # create a new root widget for Mfc applications
            if not window and self.isMfcApp():
                window = self.createRootWidget()

        return window

    def cleanRootWidgets(self):
        # remove any widgets from the list whose C++ instance has been removed
        for i in range(len(self._rootWidgets) - 1, -1, -1):
            try:
                self._rootWidgets[i].objectName()
            except:
                self._rootWidgets.remove(self._rootWidgets[i])

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
        from PyQt4.QtGui import QApplication

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

                return True
            return False
        return True

    def createRootWidget(self):
        # create a new root widget
        from PyQt4.QtWinMigrate import QWinWidget

        self.cleanRootWidgets()

        # create the widget
        widget = QWinWidget(self.hwnd())

        # parent the widget to the application
        widget.showCentered()
        self._rootWidgets.append(widget)

        return widget

    def createToolMacro(self, tool, macro=''):
        """
            \remarks	[virtual] method to create macros for a tool, should be overloaded per core
            
            \param		tool	<trax.api.tools.Tool>
            \param		macro	<str>						specific macro for the tool to run
            
            \return		<bool> success
        """
        print '[blurdev.cores.core.Core.createToolMacro] virtual method not defined'
        return False

    def disableKeystrokes(self):
        # disable the client keystrokes
        self._keysEnabled = False

    def dispatch(self, signal, *args):
        """
            \remarks	dispatches a string based signal through the system from an application
            \param		signal	<str>
            \param		*args	<tuple> additional arguments
        """
        self.emit(SIGNAL(signal), *args)

    def enableKeystrokes(self):
        # enable the client keystrokes
        self._keysEnabled = True

    def eventFilter(self, object, event):
        from PyQt4.QtCore import QEvent

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
            QEvent.RequestSoftwareInputPanel,
            QEvent.KeyPress,
        ):
            self.disableKeystrokes()

        return QObject.eventFilter(self, object, event)

    def init(self):
        """
            \remarks	initializes the core system
        """
        # register protected modules
        self.protectModule(
            'blurdev'
        )  # do not want to affect this module during environment switching

        # initialize the tools environments
        import os.path

        ToolsEnvironment.loadConfig(
            os.path.abspath(os.path.split(__file__)[0] + '/../config/tools.xml')
        )

        # initialize the application
        from PyQt4.QtGui import QApplication

        app = QApplication.instance()

        if app and self.isMfcApp():
            from PyQt4.QtCore import Qt

            # disable all UI effects as this is quite slow in MFC applications
            app.setEffectEnabled(Qt.UI_AnimateMenu, False)
            app.setEffectEnabled(Qt.UI_FadeMenu, False)
            app.setEffectEnabled(Qt.UI_AnimateCombo, False)
            app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
            app.setEffectEnabled(Qt.UI_FadeTooltip, False)
            app.setEffectEnabled(Qt.UI_AnimateToolBox, False)
            app.installEventFilter(self)

    def isMfcApp(self):
        return self._mfcApp

    def hwnd(self):
        return self._hwnd

    def isKeystrokesEnabled(self):
        return self._keysEnabled

    def lastFileName(self):
        return self._lastFileName

    def newScript(self):
        """
            \remarks	creates a new script window for editing
        """
        from blurdev.gui.windows.scriptwindow import ScriptWindow

        window = ScriptWindow(self.activeWindow())
        window.show()

    def openScript(self, filename=''):
        """
            \remarks	opens the an existing script in a new window for editing
        """
        if not filename:
            from PyQt4.QtGui import QApplication, QFileDialog

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

            from blurdev.gui.windows.scriptwindow import ScriptWindow

            window = ScriptWindow(self.activeWindow())
            window.setFileName(filename)
            window.show()

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

    def registerPaths(self, oldenv, newenv):
        """
            \remarks	registers the paths that are needed based on this core
            \param		oldenv		<blurdev.tools.ToolsEnvironment>
            \param		newenv		<blurdev.tools.ToolsEnvironment>
        """

        newenv.registerPath(newenv.relativePath('maxscript/treegrunt/lib'))
        newenv.registerPath(newenv.relativePath('code/python/lib'))

    def runMacro(self, command):
        """
            \remarks	[virtual] Runs a macro command
            \param		command 	<str>		command to run
            \return		<bool> success
        """
        print '[blurdev.cores.core.Core.runMacro] virtual method not defined'
        return False

    def runScript(self, filename='', scope=None, argv=None):
        """
            \remarks	Runs an inputed file in the best way this core knows how
            
            \param		filename	<str>
            \param		scope		<dict> || None						the scope to run the script in
            \param		argv		<list> [ <str> cmd, .. ] || None	commands to pass to the script at run time
            
            \return		<bool> success
        """
        import sys

        if not filename:
            from PyQt4.QtGui import QApplication, QFileDialog

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

        # run the script
        import os

        if filename and os.path.exists(filename):
            self._lastFileName = filename

            ext = os.path.splitext(filename)[1]

            # run a python file
            if ext.startswith('.py'):
                # create a local copy of the sys variables as they stand right now
                path_bak = list(sys.path)
                argv_bak = sys.argv

                # push the local path to the front of the list
                path = os.path.split(filename)[0]

                # if it is a package, then register the parent path, otherwise register the folder itself
                if os.path.exists(path + '/__init__.py'):
                    path = os.path.abspath(path + '/..')

                path = os.path.normcase(path)

                # if the path does not exist, then register it
                ToolsEnvironment.activeEnvironment().registerPath(path)

                scope['__name__'] = '__main__'
                scope['__file__'] = filename
                sys.argv = [filename] + argv
                scope['sys'] = sys

                execfile(filename, scope)

                # restore the system information
                sys.path = path_bak
                sys.argv = argv_bak

                return True

            # run an external link
            elif ext.startswith('.lnk'):
                os.startfile(filename)
                return True

            # report an unknown format
            else:
                print '[blurdev.cores.core.Core.runScript] Cannot run scripts of type (*%s)' % ext

        return False

    def setLastFileName(self, filename):
        return self._lastFileName

    def setHwnd(self, hwnd):
        self._hwnd = hwnd

    def showLogger(self):
        """
            \remarks	creates the python logger and displays it
        """
        if not self._logger:
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            self._logger = LoggerWindow(self.activeWindow())

        self._logger.show()

    def unprotectModule(self, moduleName):
        """
            \remarks	removes the inputed module name from protection from tools environment switching
            \param		moduleName	<str> || <QString>
        """
        key = str(moduleName)
        while key in self._protectedModules:
            self._protectedModules.remove(key)

    def toolTypes(self):
        """
            \remarks	Virtual method to determine what types of tools that the trax system should be looking at
            \return		<trax.api.tools.ToolType>
        """
        from blurdev.tools import ToolsEnvironment, ToolType

        output = ToolType.External | ToolType.LegacyExternal

        # include trax tools for non-offline environments
        if not ToolsEnvironment.activeEnvironment().isOffline():
            output |= ToolType.Trax

        return output
