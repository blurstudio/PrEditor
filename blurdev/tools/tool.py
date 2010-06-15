##
# 	\namespace	blurdev.tools.tool
#
# 	\remarks	Creates the ToolsCategory class for grouping tools together
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

from PyQt4.QtCore import QObject

from blurdev.enum import enum

ToolType = enum(
    'External',
    'Studiomax',
    'Softimage',
    'LegacyExternal',
    'LegacyStudiomax',
    'LegacySoftimage',
    AllTools=63,
)


class Tool(QObject):
    def __init__(self):
        QObject.__init__(self)

        self._displayName = ''
        self._toolType = 0

    def exec_(self, macro=''):
        """
            \remarks	runs this tool with the inputed macro command
            \param		macro	<str>
        """
        from PyQt4.QtGui import QMessageBox, QApplication

        if QApplication.instance():
            QMessageBox.critical(None, "Tool Found", "Running %s" % self.objectName())

    def index(self):
        """
            \remarks	returns the index from which this category is instantiated
            \return		<blurdev.tools.ToolIndex>
        """
        from toolsindex import ToolsIndex

        output = self.parent()
        while output and not isinstance(output, ToolsIndex):
            output = output.parent()
        return output

    def setToolType(self, toolType):
        """
            \remarks	sets the current tools type
            \param		toolType	<ToolType>
        """
        self._toolType = toolType

    def toolType(self):
        """
            \remarks	returns the toolType for this category
            \return		<ToolType>
        """
        return self._toolType

    @staticmethod
    def fromIndex(index, xml):
        """
            \remarks	creates a new tool record based on the inputed xml information for the given index
            \param		index	<ToolsIndex>
            \param		xml		<blurdev.XML.XMLElement>
        """
        output = Tool()
        output.setObjectName(xml.attribute('name'))
        output.setToolType(ToolType.fromString(xml.attribute('type', 'AllTools')))

        category = index.findCategory(xml.attribute('category'))
        if category:
            category.addTool(output)
        else:
            output.setParent(index)

        index.cacheTool(output)

        return output
