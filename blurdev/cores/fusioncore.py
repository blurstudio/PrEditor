import re
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core


class FusionCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Fusion sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'fusion'
        Core.__init__(self, *args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # NOTE: fusion is globaly available inside fusion.exe, no need to import.
        self.setHwnd(int(fusion.GetMainWindow()))

    def uuid(self):
        """ Application specific unique identifier
        
        Returns:
            str: The UUID stored in composition
        """
        # NOTE: composition is globaly available inside fusion.exe, no need to import.
        return re.findall(r'UUID: ([^\]]+)', str(composition))[0]

    def createToolMacro(self, tool, macro=''):
        """
        Overloads the createToolMacro virtual method from the Core class, this will create a macro for the
        Fusion application for the inputed Core tool. Not Supported currently.
        """
        return False

    # 	def errorCoreText(self):
    # 		"""
    # 		Returns text that is included in the error email for the active core. Override in subclasses to provide extra data.
    # 		If a empty string is returned this line will not be shown in the error email.
    # 		"""
    # 		return '<i>Open File:</i> %s' % mxs.maxFilePath + mxs.maxFileName

    def macroName(self):
        """
        Returns the name to display for the create macro action in treegrunt
        """
        return 'Create Macro...'

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are related to
        Fusion applications
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.Fusion
        return output
