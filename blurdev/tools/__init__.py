"""
The tools package contains the referencing system for all the Tools
"""
import os
import importlib
import blurdev
from blurdev.tools.toolsenvironment import ToolsEnvironment
from blurdev.tools.tool import ToolType, Tool
from blurdev import debug as _debug

# any refrences to the temporary environment should use this constant
TEMPORARY_TOOLS_ENV = 'TEMPORARY'


def logUsage(info):
    """ A function that attempts to log tool usage using the modulename defined in the bdev_use_log_class
    environment variable. The module should accept a dictonary arugment containing the info it should log.
    If it needs to report a failure, it should raise a Exception.
    :param info: A dictionary of info passed to the called function
    :return bool: If the usage reporting was successfull.
    """
    try:
        # uses the environment variable "bdev_use_log_class" to import a module similar to the following
        useLogClass = os.environ.get('bdev_use_log_class')
        useLog = importlib.import_module(useLogClass)
        useLog.logEvent(info)
        return True
    except Exception, e:
        if _debug.debugLevel() >= _debug.DebugLevel.High:
            raise
        else:
            # If redmine commits fail, allow code to continue.
            console = blurdev.core.logger().console()
            error = ''.join(console.lastError())
            emails = blurdev.tools.ToolsEnvironment.activeEnvironment().emailOnError()
            console.emailError(emails, error)
    return False
