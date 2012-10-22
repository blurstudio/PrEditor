"""
The tools package contains the referencing system for all the Tools
"""

from toolsenvironment import ToolsEnvironment
from tool import ToolType, Tool

# any refrences to the temporary environment should use this constant
TEMPORARY_TOOLS_ENV = 'TEMPORARY'
