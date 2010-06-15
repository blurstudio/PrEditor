##
# 	\namespace	blurdev
#
# 	\remarks	The blurdev package is the core library methods for tools development at Blur Studio
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

core = None


def init():
    global core
    if not core:
        # create the core instance
        from blurdev.cores import Core

        core = Core()
        core.init()


def runTool(tool, macro=""):
    from PyQt4.QtGui import QApplication
    from tools import ToolsEnvironment

    # load the tool
    tool = ToolsEnvironment.activeEnvironment().index().findTool(tool)
    if tool:
        tool.exec_(macro)

    # let the user know the tool could not be found
    elif QApplication.instance():
        from PyQt4.QtGui import QMessageBox

        QMessageBox.critical(
            None,
            'Tool Not Found',
            '%s is not a tool in %s environment.'
            % (tool, ToolsEnvironment.activeEnvironment().objectName()),
        )
