##
# 	\namespace	blurdev.cores.studiomaxcore
#
# 	\remarks	This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Studiomax sessions
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/12/10
#

# to be in a 3dsmax session, we need to be able to import the Py3dsMax package
import Py3dsMax
from core import Core

# -------------------------------------------------------------------------------------------------------------

STUDIOMAX_MACRO_TEMPLATE = """
macroscript Blur_%(id)s_Macro
category: "Blur Tools"
toolTip: "%(tooltip)s"
buttonText: "%(displayName)s"
icon:#( "Blur_%(id)s_Macro", 1 )
(
    local blurdev 	= python.import "blurdev"
    blurdev.runTool "%(tool)s" macro:"%(macro)s"
)
"""

# -------------------------------------------------------------------------------------------------------------


class StudiomaxCore(Core):
    def __init__(self):
        Core.__init__(self)
        self.setObjectName('studiomax')

    def createToolMacro(self, tool, macro=''):
        """
            \remarks	Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
                        Studiomax application for the inputed Core tool
            
            \return		<bool> success
        """
        # create the options for the tool macro to run
        options = {
            'tool': tool.objectName(),
            'displayName': tool.displayName(),
            'macro': macro,
            'tooltip': tool.toolTip(),
            'id': str(tool.displayName()).replace(' ', '_').replace('::', '_'),
        }

        # create the macroscript
        import Py3dsMax

        filename = Py3dsMax.mxs.pathConfig.resolvePathSymbols(
            '$usermacros/Blur_%s_Macro.mcr' % options['id']
        )
        f = open(filename, 'w')
        f.write(STUDIOMAX_MACRO_TEMPLATE % options)

        # convert icon files to max standard ...
        from PyQt4.QtGui import QImage

        root = QImage(tool.icon())
        icon24 = root.scaled(24, 24)

        # ... for 24x24 pixels (image & alpha icons)
        basename = Py3dsMax.mxs.pathConfig.resolvePathSymbols(
            '$usericons/Blur_%s_Macro' % options['id']
        )
        icon24.save(basename + '_24i.bmp')
        icon24.alphaChannel().save(basename + '_24a.bmp')

        # ... and for 16x16 pixels (image & alpha icons)
        icon16 = root.scaled(16, 16)
        icon16.save(basename + '_16i.bmp')
        icon16.alphaChannel().save(basename + '_16a.bmp')

        # run the macroscript & refresh the icons
        Py3dsMax.mxs.filein(filename)
        Py3dsMax.mxs.colorman.setIconFolder('.')
        Py3dsMax.mxs.colorman.setIconFolder('Icons')

        return True

    def disableKeystrokes(self):
        """
            \remarks	[overloaded] disables keystrokes in maxscript
        """
        from Py3dsMax import mxs

        mxs.enableAccelerators = False

        return Core.disableKeystrokes(self)

    def enableKeystrokes(self):
        """
            \remarks	[overloaded] disables keystrokes in maxscript - max will always try to turn them on
        """
        from Py3dsMax import mxs

        mxs.enableAccelerators = False

        return Core.enableKeystrokes(self)

    def init(self):
        # connect the plugin to 3dsmax
        import Py3dsMax

        self.connectPlugin(Py3dsMax.GetPluginInstance(), Py3dsMax.GetWindowHandle())

        # init the base class
        Core.init(self)

    def runScript(self, filename='', scope=None, argv=None, toolType=None):
        """
            \remarks	[overloaded] handle maxscript script running
        """

        if not filename:
            from PyQt4.QtGui import QApplication, QFileDialog

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

        # run a maxscript file
        import os.path

        if os.path.splitext(filename)[1] in ('.ms', '.mcr'):
            if os.path.exists(filename):
                import Py3dsMax

                Py3dsMax.mxs.filein(filename)
                return True
            return False

        return Core.runScript(self, filename, scope, argv, toolType)

    def toolTypes(self):
        """
            \remarks	Overloads the toolTypes method from the Core class to show tool types that are related to
                        Studiomax applications
                        
            \return		<blurdev.tools.ToolType>
        """
        from blurdev.tools import ToolsEnvironment, ToolType

        output = ToolType.Studiomax | ToolType.LegacyStudiomax

        return output
