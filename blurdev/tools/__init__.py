"""
The tools package contains the referencing system for all the Tools
"""
import os

# Compatibility with pre-2.7
try:
    from importlib import import_module
except ImportError:

    def import_module(name):
        return __import__(name)


import blurdev
from blurdev.tools.toolsenvironment import ToolsEnvironment  # noqa: F401
from blurdev.tools.tool import ToolType, Tool  # noqa: F401
from blurdev import debug as _debug

# any refrences to the temporary environment should use this constant
TEMPORARY_TOOLS_ENV = 'TEMPORARY'


def logUsage(info):
    """ Log that a tool was launched.

    Attempts to log tool usage using the modulename defined in the BDEV_USE_LOG_CLASS
    environment variable. The module should accept a dictonary arugment containing the
    info it should log. If it needs to report a failure, it should raise a Exception.
    This function can be disabled by setting the environment variable
    BDEV_DISABLE_TOOL_USAGE_LOG to true.

    Args:
        info(dict): A dictionary of info passed to the called function

    Returns:
        bool: If the usage reporting was successfull.

    Raises:

        Exception: If blurdev.debug.debugLevel is set to High, raises any exceptions
                    generated, otherwise consumes them and sends a error email.
    """
    if os.environ.get('BDEV_DISABLE_TOOL_USAGE_LOG', 'False').lower() == "true":
        # This environment variable can be used to disable tool use logging.
        return False
    try:
        # uses the environment variable "BDEV_USE_LOG_CLASS" to import a module similar
        # to the following
        useLogClass = os.environ.get('BDEV_USE_LOG_CLASS')
        useLog = import_module(useLogClass)
        useLog.logEvent(info)
        return True
    except Exception:
        if _debug.debugLevel() >= _debug.DebugLevel.High:
            raise
        else:
            # If redmine commits fail, allow code to continue.
            from blurdev.utils.errorEmail import emailError

            console = blurdev.core.logger().console()
            error = ''.join(console.lastError())
            emails = blurdev.tools.ToolsEnvironment.activeEnvironment().emailOnError()
            emailError(emails, error)

    return False


def toolPaths():
    """ Entry point returning paths treegrunt needs to find imports and tools.

    Returns:
        sys_paths: A list of paths that need added to sys.path to add imports.
        tool_paths: A list of paths treegrunt should scan for tools. You can pass
            directory paths or a specific __meta__.xml file if your package only has
            one tool.
    """
    return blurdev.activeEnvironment()._environmentToolPaths()
