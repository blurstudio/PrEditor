from __future__ import print_function
import os
import sys
import logging

# to be in a 3dsmax session, we need to be able to import the Py3dsMax package
import Py3dsMax
from Py3dsMax import mxs
from Qt.QtGui import QImage
from Qt.QtWidgets import QApplication, QFileDialog, QMainWindow
from Qt.QtCore import QRect, QSize, Qt, QByteArray
from Qt import QtCompat

import blurdev
import blurdev.ini
import blurdev.tools.tool
import blurdev.tools.toolsenvironment
from blurdev.cores.core import Core

# 3ds max version breakdown = {version: year, 16: 2014, 18:2016, 20: 2018}
_maxVersion = mxs.maxVersion()[0] / 1000

# These modules are needed for 3ds Max 2017 or newer(19+)
if _maxVersion > 18:
    import MaxPlus
    import PySide2

STUDIOMAX_MACRO_TEMPLATE = """
macroscript %(studioName)s_%(id)s_Macro
category: "%(studioName)s Tools"
toolTip: "%(tooltip)s"
buttonText: "%(displayName)s"
icon:#( "%(studioName)s_%(id)s_Macro", 1 )%(iconName)s
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


def _focusChanged(old, now):
    """ Disables Max keyboard shotcuts when a widget in a window gets focus.

    This is called after both old and now have been notified through QFocusEvent

    We need to process both the old and now widgets. If we only process now
    and call EnableAccelerators in all other cases, going from DisableAccelerators
    to a widget that needs disabled, like a text input or the Maxscript Listener
    will result in the Accelerators enabled.

    When making changes test switching between the Python Logger and several
    Max interface elements.
        0. The Python Listener
        1. The Maxscript Listener
        2. Rename the selected object by using the Name and Color text box.
        3. The viewport, left, right, and middle click
        4. The Main 3ds max window title

    Ensure the max keyboard shortcuts work properly. I toggled these keys as they are
    easy to visually inspect in the toolbr. a: "Angle Snaps Toggle", s: "Snaps Toggle"

    Keyboard shortcuts should not be disabled when now is 3 or 4. If we call
    DisableAccelerators on x-0 and EnableAccelerators on anything else. 0-1,
    0-2, 0-3 will not end up calling DisableAccelerators on 1, 2, or 3 and
    you will be unable to type into the maxscript text edits.

    Also, make sure to test switching between widgets in the same window. For
    example switching between widgets in a 0-0, or 1-1 manner
    """
    try:
        # If the old window has _shouldDisableAccelerators, we need to re-enable
        # them so that the other window can enable or disable them as it needs
        # Luckily this does not seem to interfear with what ever magic the
        # maxscript listener is doing to enable typing.
        o = old.window()
        if o._shouldDisableAccelerators(now, old):
            MaxPlus.CUI.EnableAccelerators()
    except AttributeError:
        pass

    try:
        w = now.window()
        if w._shouldDisableAccelerators(old, now):
            # This window wants to be able to use keyboard shortcuts
            # so disable max's keyboard accelerators. This is to resolve
            # a strange design decision in max 2018 and newer. By default
            # keyboard shortcuts work on all widgets including text widgets.
            MaxPlus.CUI.DisableAccelerators()
            return
    except AttributeError:
        # now is None, or _shouldDisableAccelerators is not defined
        pass


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
        self.dccVersion = _maxVersion
        if self.dccVersion >= 20:
            self._supportsDocking = True
            # Shutdown blurdev when DCC closes
            if QApplication.instance():
                QApplication.instance().aboutToQuit.connect(self.shutdown)

        # The Qt dlls in the studiomax directory cause problems for other dcc's
        # so, we need to remove the directory from the PATH environment variable.
        # See blurdev.osystem.subprocessEnvironment() for more details.
        maxRoot = mxs.pathConfig.resolvePathSymbols('$max')
        self._removeFromPATHEnv.add(maxRoot)
        self._removeFromPATHEnv.add(
            os.path.join(maxRoot, 'python', 'lib', 'site-packages', 'pywin32_system32')
        )

    def addLibraryPaths(self):
        if sys.platform != 'win32':
            return
        if self.dccVersion == 16 and blurdev.osystem.getPointerSize() == 64:
            path = os.path.split(sys.executable)[0]
            if os.path.exists(os.path.join(path, 'QtOpenGL4.dll')):
                # Special case for if max has our pyqt installed inside it
                QApplication.addLibraryPath(os.path.split(sys.executable)[0])
                return
        elif self.dccVersion > 18:
            # We don't need to worry about adding libraryPaths, its taken care of by
            # the max plugin that imported blurdev
            return
        super(StudiomaxCore, self).addLibraryPaths()

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
            'iconName': '',
        }
        if self.dccVersion >= 19:
            # iconName is only supported in max 2017 or newer.
            options['iconName'] = '\niconName:"%(studioName)s_%(id)s_Macro"' % options

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
        # Versions of max older than 2017 are not Qt based
        if self.dccVersion < 19:
            icon24 = tool.image()
            icon24 = resizeImage(icon24, outSize)

            # ... for 24x24 pixels (image & alpha icons)
            basename = mxs.pathConfig.resolvePathSymbols(
                '$usericons/%s_%s_Macro'
                % (os.environ.get('bdev_studio_name', ''), options['id'])
            )
            icon24.save(basename + '_24i.bmp')
            # NOTE: the alphaChannel function does not exist in Qt5
            icon24.alphaChannel().save(basename + '_24a.bmp')

            # ... and for 16x16 pixels (image & alpha icons)
            outSize = QSize(16, 16)
            # Attempt to load the 16 pixel icon if present
            icon16 = tool.image(replace=('24', ''))
            icon16 = resizeImage(icon16, outSize)
            icon16.save(basename + '_16i.bmp')
            # NOTE: the alphaChannel function does not exist in Qt5
            icon16.alphaChannel().save(basename + '_16a.bmp')
        else:
            # For max 2017+ we can just save out a .png file
            userIcons = mxs.pathConfig.resolvePathSymbols('$ui_ln')
            for theme in ('Light', 'Dark'):
                directory = os.path.join(userIcons, 'Icons', theme)
                if not os.path.exists(directory) and os.path.exists(userIcons):
                    # If userIcons exists, but the theme dir does not, create it.
                    os.makedirs(directory)
                image = tool.image()
                image = resizeImage(image, outSize)
                iconPath = os.path.join(
                    directory,
                    '{}_{}_Macro_24.png'.format(
                        os.environ.get('BDEV_STUDIO_NAME', ''), options['id']
                    ),
                )
                image.save(iconPath)

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
        # Versions of max older than 2017 are not Qt based
        if self.dccVersion < 19:
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

        else:
            app = QApplication.instance()
            app.focusChanged.connect(_focusChanged)
            # backup the existing stylesheet so blurdev doesn't step on it
            self._defaultStyleSheet = app.styleSheet()

        # initialize the logger
        self.logger()

        # init the base class
        ret = super(StudiomaxCore, self).init()
        return ret

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def mainWindowGeometry(self):
        if self.headless:
            raise Exception('You are showing a gui in a headless environment. STOP IT!')
        if self.dccVersion < 16:
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
                iniEnvname = blurdev.ini.GetINISetting(
                    blurdev.ini.configFile, 'GLOBALS', 'environment'
                )
                if (
                    shiftPressed
                    or iniEnvname != envname
                    or os.path.normpath(mxs.blurConfigFile) != env.configIni()
                ):
                    print(
                        'Switching maxscript environments from',
                        iniEnvname,
                        'To',
                        envname,
                    )
                    try:
                        blurdev.ini.SetINISetting(
                            blurdev.ini.configFile, 'GLOBALS', 'environment', envname
                        )
                    except IOError as e:
                        # If the user does not have permission to update this, don't except, just log a warning
                        import warnings

                        warnings.warn(str(e), RuntimeWarning, stacklevel=2)
                    # update blurConfigFile when switching environments to point to the active environment's
                    # config.ini if it exists, otherwise default to the standard c:\blur\config.ini
                    mxs.blurConfigFile = env.configIni()
                    try:
                        import legacy

                        path = os.path.dirname(legacy.__file__)
                        mxs.filein(os.path.join(path, 'lib', 'blurStartup.ms'))
                    except (RuntimeError, ImportError) as error:
                        # Show the error, but don't cause blurdev to fail to fully import.
                        logging.error(error)

        # register standard paths
        return Core.registerPaths(self)

    def rootWindow(self):
        # Max 2017+ is Qt based and makes it simple to find the root max window.
        if self.dccVersion > 18 and self._rootWindow is None:
            # Max returns the main window as a PySide2 widget, get its c++ pointer
            ids = PySide2.shiboken2.getCppPointer(MaxPlus.GetQMaxMainWindow())
            if ids:
                # Convert the c++ pointer to a PyQt5 widget
                self._rootWindow = QtCompat.wrapInstance(long(ids[0]), QMainWindow)
                return self._rootWindow
        return super(StudiomaxCore, self).rootWindow()

    def runScript(
        self, filename='', scope=None, argv=None, tool=None, architecture=None
    ):
        """
        Handle maxscript script running
        """
        if not filename:
            # make sure there is a QApplication running
            if QApplication.instance():
                filename, _ = QtCompat.QFileDialog.getOpenFileName(
                    None,
                    'Select Script File',
                    '',
                    'Python Files (*.py);;Maxscript Files (*.ms);;All Files (*.*)',
                )
                if not filename:
                    return

        # run a maxscript file
        if os.path.splitext(filename)[1] in ('.ms', '.mcr', '.mse'):
            if os.path.exists(filename):
                return mxs.filein(filename)
            return False
        return Core.runScript(
            self, filename, scope, argv, tool=tool, architecture=architecture
        )

    def setSupportLegacy(self, state):
        pass

    def supportLegacy(self):
        return True

    def quitQtOnShutdown(self):
        """ Qt should not be closed when this core has shutdown called
        """
        if self.dccVersion >= 20:
            return False
        else:
            return super(StudiomaxCore, self).quitQtOnShutdown()

    def shutdown(self):
        super(StudiomaxCore, self).shutdown()

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Studiomax applications
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.Studiomax | ToolType.LegacyStudiomax
        return output
