import os
import sys

# to be in a 3dsmax session, we need to be able to import the Py3dsMax package
import Py3dsMax
from Py3dsMax import mxs
from PyQt4.QtGui import QApplication, QFileDialog, QImage
from PyQt4.QtCore import Qt, QSize, QRect

import blurdev
import blurdev.ini
import blurdev.tools.tool
import blurdev.tools.toolsenvironment
from blurdev.cores.core import Core


STUDIOMAX_MACRO_TEMPLATE = """
macroscript %(studioName)s_%(id)s_Macro
category: "%(studioName)s Tools"
toolTip: "%(tooltip)s"
buttonText: "%(displayName)s"
icon:#( "%(studioName)s_%(id)s_Macro", 1 )
(
    local blurdev 	= pymax.import "blurdev"
    blurdev.runTool "%(tool)s" macro:"%(macro)s"
)
"""

# initialize callback scripts
STUDIOMAX_CALLBACK_TEMPLATE = """
global pyblurdev
if ( pyblurdev == undefined ) then ( pyblurdev = pymax.import "blurdev" )
if ( pyblurdev != undefined ) then ( 
    local ms_args = (callbacks.notificationParam())
    pyblurdev.core.dispatch "%(signal)s" %(args)s 
)
"""


class StudiomaxCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Studiomax sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'studiomax'
        Core.__init__(self, *args, **kargs)
        self._supportLegacy = True
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False

    def addLibraryPaths(self, app):
        if sys.platform != 'win32':
            return
        if mxs.maxVersion()[0] / 1000 == 16 and blurdev.osystem.getPointerSize() == 64:
            path = os.path.split(sys.executable)[0]
            if os.path.exists(os.path.join(path, 'QtOpenGL4.dll')):
                # Special case for if max has our pyqt installed inside it
                app.addLibraryPath(os.path.split(sys.executable)[0])
                return
        super(StudiomaxCore, self).addLibraryPaths(app)

    def configUpdated(self):
        """
        Preform any core specific updating of config. Returns if any actions were taken.
        """
        blurlib = mxs._blurLibrary
        if blurlib:
            blurlib.LoadConfigData()
        return False

    def connectAppSignals(self):
        # moved to blur3d
        return

    def connectStudiomaxSignal(self, maxSignal, blurdevSignal, args=''):
        # store the maxscript methods needed
        _n = mxs.pyhelper.namify
        callbacks = mxs.callbacks
        blurdevid = _n('blurdev')
        callbacks.addScript(
            _n(maxSignal),
            STUDIOMAX_CALLBACK_TEMPLATE % {'signal': blurdevSignal, 'args': args},
        )

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Studiomax application for the inputed Core tool
        """
        # create the options for the tool macro to run
        options = {
            'tool': tool.objectName(),
            'displayName': tool.displayName(),
            'macro': macro,
            'tooltip': tool.displayName(),
            'id': str(tool.displayName()).replace(' ', '_').replace('::', '_'),
            'studioName': os.environ.get('bdev_studio_name', ''),
        }

        # create the macroscript
        filename = mxs.pathConfig.resolvePathSymbols(
            '$usermacros/%s_%s_Macro.mcr'
            % (os.environ.get('bdev_studio_name', ''), options['id'])
        )
        f = open(filename, 'w')
        f.write(STUDIOMAX_MACRO_TEMPLATE % options)
        f.close()

        # convert icon files to max standard ...
        def resizeImage(image, outSize):
            difWidth = image.size().width() - outSize.width()
            difHeight = image.size().height() - outSize.height()
            if difWidth < 0 or difHeight < 0:
                ret = image.copy(
                    difWidth / 2, difHeight / 2, outSize.width(), outSize.height()
                )
            else:
                ret = image.scaled(outSize, Qt.KeepAspectRatio)
            return ret

        outSize = QSize(24, 24)
        icon24 = tool.image()
        icon24 = resizeImage(icon24, outSize)

        # ... for 24x24 pixels (image & alpha icons)
        basename = mxs.pathConfig.resolvePathSymbols(
            '$usericons/%s_%s_Macro'
            % (os.environ.get('bdev_studio_name', ''), options['id'])
        )
        icon24.save(basename + '_24i.bmp')
        icon24.alphaChannel().save(basename + '_24a.bmp')

        # ... and for 16x16 pixels (image & alpha icons)
        outSize = QSize(16, 16)
        # Attempt to load the 16 pixel icon if present
        icon16 = tool.image(replace=('24', ''))
        icon16 = resizeImage(icon16, outSize)
        icon16.save(basename + '_16i.bmp')
        icon16.alphaChannel().save(basename + '_16a.bmp')

        # run the macroscript & refresh the icons
        mxs.filein(filename)
        mxs.colorman.setIconFolder('.')
        mxs.colorman.setIconFolder('Icons')
        return True

    def disableKeystrokes(self):
        """
        Disables keystrokes in maxscript
        """
        mxs.enableAccelerators = False
        return Core.disableKeystrokes(self)

    def enableKeystrokes(self):
        """
        Disables keystrokes in maxscript - max will always try to turn them on
        """
        mxs.enableAccelerators = False
        return Core.enableKeystrokes(self)

    def errorCoreText(self):
        """
        Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
        If a empty string is returned this line will not be shown in the error email.
        """
        return '<i>Open File:</i> %s' % mxs.maxFilePath + mxs.maxFileName

    def init(self):
        # connect the plugin to 3dsmax
        hInstance = Py3dsMax.GetPluginInstance()
        hwnd = Py3dsMax.GetWindowHandle()

        # create a max plugin connection
        if not self.connectPlugin(hInstance, hwnd):

            # initialize the look for the application instance
            app = QApplication.instance()
            app.setStyle('plastique')

            # we will still need these variables set to work properly
            self.setHwnd(hwnd)
            self._mfcApp = True

            # initialize the logger
            self.logger()

        # init the base class
        return Core.init(self)

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def mainWindowGeometry(self):
        if self.headless:
            raise Exception('You are showing a gui in a headless environment. STOP IT!')
        if mxs.maxVersion()[0] / 1000 < 16:
            # mxs.windows.getWindowPos is new in max 2014, so dont try to call it in previous
            # versions of max
            return QRect()
        box = mxs.windows.getWindowPos(Py3dsMax.GetWindowHandle())
        return QRect(0, 0, box.w, box.h)

    def quietMode(self):
        """
        Use this to decide if you should provide user input. 
        """
        if mxs.MAXSCRIPTHOST == 1 or mxs.GetQuietMode():
            # This is set in startup/blurStartupMaxLib.ms
            # It should signify that max was started with assburner
            # GetQuietMode returns true if max was started to render frames.
            return True
        return False

    def recordSettings(self):
        pref = self.recordCoreSettings()
        pref.recordProperty('supportLegacy', True)
        pref.save()

    def restoreSettings(self):
        pref = super(StudiomaxCore, self).restoreSettings()
        self.setSupportLegacy(pref.restoreProperty('supportLegacy', False))

    def registerPaths(self):
        env = blurdev.tools.toolsenvironment.ToolsEnvironment.activeEnvironment()
        if QApplication.instance():
            shiftPressed = (
                QApplication.instance().keyboardModifiers() == Qt.ShiftModifier
            )

        # update the old blur maxscript library system
        envname = env.legacyName()

        # update the old library system
        if self.supportLegacy() and not env.isTemporary():
            if not envname:
                envname = env.objectName()
            if envname:
                # update the maxscript code only if we are actually changing code environments
                if (
                    shiftPressed
                    or blurdev.ini.GetINISetting(
                        blurdev.ini.configFile, 'GLOBALS', 'environment'
                    )
                    != envname
                ):
                    print 'Switching maxscript environments from', blurdev.ini.GetINISetting(
                        blurdev.ini.configFile, 'GLOBALS', 'environment'
                    ), 'To', envname
                    blurdev.ini.SetINISetting(
                        blurdev.ini.configFile, 'GLOBALS', 'environment', envname
                    )
                    mxs.filein(
                        os.path.join(blurdev.ini.GetCodePath(), 'Lib', 'blurStartup.ms')
                    )

        # register standard paths
        return Core.registerPaths(self)

    def runScript(
        self,
        filename='',
        scope=None,
        argv=None,
        toolType=None,
        toolName=None,
        architecture=None,
    ):
        """
        Handle maxscript script running
        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename = str(
                    QFileDialog.getOpenFileName(
                        None,
                        'Select Script File',
                        '',
                        'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                    )
                )
                if not filename:
                    return
        filename = str(filename)

        # run a maxscript file
        if os.path.splitext(filename)[1] in ('.ms', '.mcr', '.mse'):
            if os.path.exists(filename):
                return mxs.filein(filename)
            return False
        return Core.runScript(
            self,
            filename,
            scope,
            argv,
            toolType,
            toolName=toolName,
            architecture=architecture,
        )

    def setSupportLegacy(self, state):
        pass

    def supportLegacy(self):
        return True

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Studiomax applications
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.Studiomax | ToolType.LegacyStudiomax
        return output
