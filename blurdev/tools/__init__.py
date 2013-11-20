"""
The tools package contains the referencing system for all the Tools
"""

from blurdev.tools.toolsenvironment import ToolsEnvironment
from blurdev.tools.tool import ToolType, Tool

# any refrences to the temporary environment should use this constant
TEMPORARY_TOOLS_ENV = 'TEMPORARY'
