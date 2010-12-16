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
    debugLevelChanged = pyqtSignal()
    fileCheckedIn = pyqtSignal(str)
    fileCheckedOut = pyqtSignal(str)

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

        # create the connection to the environment activiation signal
        self.environmentActivated.connect(self.registerPaths)

    def activeWindow(self):
        from PyQt4.QtGui import QApplication

        if QApplication.instance():
            return QApplication.instance().activeWindow()
        return None

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

                    # initialize the logger

                    self.logger()

                return True
            return False
        return True

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
            QEvent.KeyPress,
        ):
            self.disableKeystrokes()

        return QObject.eventFilter(self, object, event)

    def shutdown(self):
        from PyQt4.QtGui import QApplication

        if QApplication.instance():
            QApplication.instance().closeAllWindows()
            QApplication.instance().quit()

    def init(self):
        """
            \remarks	initializes the core system
        """
        # register protected modules
        self.protectModule(
            'blurdev'
        )  # do not want to affect this module during environment switching

        # initialize the tools environments
        import blurdev

        ToolsEnvironment.loadConfig(blurdev.resourcePath('tools_environments.xml'))

        # initialize the application
        from PyQt4.QtGui import QApplication

        app = QApplication.instance()

        output = None

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

        # create a new application

        elif not app:

            output = QApplication([])

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

            from blurdev.ide import IdeEditor

            IdeEditor.edit(filename=filename)

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

    def rootWindow(self):
        """
            \remarks	returns the currently active window
            \return		<QWidget> || None
        """
        # for MFC apps there should be no root window
        if self.isMfcApp():
            return None

        from PyQt4.QtGui import QApplication

        window = None
        if QApplication.instance():
            window = QApplication.instance().activeWindow()

            # grab the root window
            if window:
                while window.parent():
                    window = window.parent()

        return window

    def runMacro(self, command):
        """
            \remarks	[virtual] Runs a macro command
            \param		command 	<str>		command to run
            \return		<bool> success
        """
        print '[blurdev.cores.core.Core.runMacro] virtual method not defined'
        return False

    def runStandalone(self, filename, debugLevel=None, basePath=''):

        from blurdev import debug

        if debugLevel == None:

            debugLevel = debug.debugLevel()

        import os.path
        from PyQt4.QtCore import QProcess

        filename = str(filename)

        if not basePath:

            basePath = os.path.split(filename)[0]

        success = False

        if debugLevel == debug.DebugLevel.High:
            # run a python file
            if os.path.splitext(filename)[1].startswith('.py'):
                success, value = QProcess.startDetached(
                    'cmd.exe', ['/k', 'python.exe %s' % filename], basePath
                )
            else:
                success, value = QProcess.startDetached(
                    'cmd.exe', ['/k', filename], basePath
                )

        elif os.path.splitext(filename)[1].startswith('.py'):
            success, value = QProcess.startDetached('pythonw.exe', [filename], basePath)

        else:
            success, value = QProcess.startDetached(filename, [], basePath)

        if not success:

            import os

            try:

                os.startfile(filename)

                success = True

            except:

                pass

        return success

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
        from PyQt4.QtGui import QApplication, QFileDialog, QMessageBox

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

            from blurdev.tools import ToolType

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
                    argv_bak = sys.argv

                    # if the path does not exist, then register it
                    ToolsEnvironment.registerScriptPath(filename)

                    scope['__name__'] = '__main__'
                    scope['__file__'] = filename
                    sys.argv = [filename] + argv
                    scope['sys'] = sys

                    execfile(filename, scope)

                    # restore the system information
                    sys.path = path_bak
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

    def sendEmail(self, sender, targets, subject, message, attachments=None):
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

    def showIdeEditor(self):

        from blurdev.ide import IdeEditor

        IdeEditor.instance().edit()

    def showTreegrunt(self):
        self.treegrunt().show()

    def showLogger(self):
        """
            \remarks	creates the python logger and displays it
        """

        self.logger().show()

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

        output = ToolType.External | ToolType.Fusion | ToolType.LegacyExternal

        return output

    def treegrunt(self, parent=None):
        """
            \remarks	creates and returns the logger instance
        """

        from blurdev.gui.dialogs.treegruntdialog import TreegruntDialog

        return TreegruntDialog.instance(parent)
