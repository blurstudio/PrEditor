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

# 					1			2			4			8					16					32				64
ToolType = enum(
    'External',
    'Trax',
    'Studiomax',
    'Softimage',
    'LegacyExternal',
    'LegacyStudiomax',
    'LegacySoftimage',
    AllTools=127,
)


class Tool(QObject):
    def __init__(self):
        QObject.__init__(self)

        self._displayName = ''
        self._path = ''
        self._sourcefile = ''
        self._toolTip = ''
        self._wikiPage = ''
        self._macros = []
        self._version = ''
        self._icon = ''
        self._toolType = 0
        self._favorite = False
        self._favoriteGroup = None
        self._header = None

    def displayName(self):
        output = str(self.objectName()).split('::')[-1]
        return output.replace('_', ' ').strip()

    def exec_(self, macro=''):
        """
            \remarks	runs this tool with the inputed macro command
            \param		macro	<str>
        """
        # external tools should be launched externally
        import blurdev

        if (
            self.toolType() & ToolType.LegacyExternal
            or blurdev.core.objectName() == 'external'
        ):
            import os

            os.startfile(self.sourcefile())

        else:
            import blurdev

            blurdev.init()
            blurdev.core.runScript(self.sourcefile())

    def favoriteGroup(self):
        return self._favoriteGroup

    def header(self):
        if not self._header:
            from toolheader import ToolHeader

            self._header = ToolHeader(self)
        return self._header

    def icon(self):
        return self.relativePath(self._icon)

    def isFavorite(self):
        return self._favorite

    def isNull(self):
        return self.objectName() == ''

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

    def path(self):
        return self._path

    def relativePath(self, relpath):
        import os.path

        output = os.path.join(self.path(), relpath)
        if output and os.path.exists(output):
            return output
        return ''

    def setFavorite(self, state=True):
        self._favorite = state

    def setFavoriteGroup(self, favoriteGroup):
        self._favoriteGroup = favoriteGroup
        if favoriteGroup:
            self.setFavorite()

    def setIcon(self, icon):
        self._icon = icon

    def setPath(self, path):
        import os.path

        if os.path.exists(path):
            self._path = path
        else:
            self._path = ''

    def setSourcefile(self, sourcefile):
        self._sourcefile = sourcefile

    def setToolType(self, toolType):
        """
            \remarks	sets the current tools type
            \param		toolType	<ToolType>
        """
        self._toolType = toolType

    def setVersion(self, version):
        self._version = version

    def setWikiPage(self, wiki):
        self._wikiPage = wiki

    def sourcefile(self):
        return self._sourcefile

    def toolTip(self):
        return self._toolTip

    def toolType(self):
        """
            \remarks	returns the toolType for this category
            \return		<ToolType>
        """
        return self._toolType

    def version(self):
        return self._version

    def wikiPage(self):
        return self._wikiPage

    @staticmethod
    def fromIndex(index, xml):
        """
            \remarks	creates a new tool record based on the inputed xml information for the given index
            \param		index	<ToolsIndex>
            \param		xml		<blurdev.XML.XMLElement>
        """
        output = Tool()
        output.setObjectName(xml.attribute('name'))

        # load modern tools
        loc = xml.attribute('loc')
        import os.path

        if loc:
            output.setPath(os.path.split(index.environment().relativePath(loc))[0])

            # load the meta data
            data = xml.findChild('data')
            if data:
                output.setVersion(data.attribute('version'))
                output.setIcon(data.findProperty('icon'))
                output.setSourcefile(output.relativePath(data.findProperty('src')))
                output.setWikiPage(data.findProperty('wiki'))
                output.setToolType(
                    ToolType.fromString(data.attribute('type', 'AllTools'))
                )
        else:
            output.setToolType(ToolType.fromString(xml.attribute('type', 'AllTools')))
            filename = xml.attribute('src')
            output.setPath(
                os.path.split(filename)[0]
                + '/%s_resource' % os.path.basename(filename).split('.')[0]
            )
            output.setSourcefile(filename)
            output.setIcon(xml.attribute('icon'))

        # add the tool to the category or index
        category = index.findCategory(xml.attribute('category'))
        if category:
            category.addTool(output)
        else:
            output.setParent(index)

        # cache the tool in the index
        index.cacheTool(output)

        return output
