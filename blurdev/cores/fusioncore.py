from __future__ import absolute_import
import re
import blurdev
import blurdev.tools.tool
from blurdev.cores.core import Core


class FusionCore(Core):
    """
    This class is a reimplimentation of the blurdev.cores.core.Core class for running
    blurdev within Fusion sessions
    """

    def __init__(self, *args, **kargs):
        kargs['objectName'] = 'fusion'
        Core.__init__(self, *args, **kargs)
        # Disable AppUserModelID. See blurdev.setAppUserModelID for more info.
        self._useAppUserModelID = False
        # NOTE: fusion is globaly available inside fusion.exe, no need to import.
        self.setHwnd(int(fusion.GetMainWindow()))  # noqa: F821

    def uuid(self):
        """Application specific unique identifier

        Returns:
            str: The UUID stored in composition
        """
        # NOTE: composition is globaly available inside fusion.exe, no need to import.
        return re.findall(r'UUID: ([^\]]+)', str(composition))[0]  # noqa: F821

    def macroNames(self):
        """Returns True if the current blurdev core create a tool macro."""
        # Blurdev can not currently make a macro for this DCC.
        return tuple()

    def toolTypes(self):
        """
        Overloads the toolTypes method from the Core class to show tool types that are
        related to Fusion applications
        """
        ToolType = blurdev.tools.tool.ToolType
        output = ToolType.Fusion
        return output
