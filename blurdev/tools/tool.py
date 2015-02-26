from __future__ import absolute_import

import os

from PyQt4.QtCore import QObject, Qt
from PyQt4.QtGui import QApplication

import blurdev
from ..enum import enum
import blurdev.tools.toolheader
import blurdev.tools.toolsindex


# 					1			2			4			8		  16			32				64					128				256			  512
ToolType = enum(
    'External',
    'Trax',
    'Studiomax',
    'Softimage',
    'Fusion',
    'MotionBuilder',
    'LegacyExternal',
    'LegacyStudiomax',
    'LegacySoftimage',
    'Maya',
    AllTools=1023,
)


class Tool(QObject):
    """ Creates the ToolsCategory class for grouping tools together
    """

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
        self._architecture = None
        self._favorite = False
        self._favoriteGroup = None
        self._redistributable = True
        self._header = None
        self._disabled = False
        self._usagestatsEnabled = True

    def architecture(self):
        """ This tool needs to run in this architecture (32bit or 64bit) when running externally
        
        If this tool is run by external treegrunt, launch the tool with this version of python if
        possible. If None the system default will be used.
        """
        return self._architecture

    def setArchitecture(self, architecture):
        if isinstance(architecture, basestring):
            architecture = int(architecture)
        self._architecture = architecture

    def disabled(self):
        return self._disabled

    def displayName(self):
        if self._displayName:
            return self._displayName
        else:
            output = str(self.objectName()).split('::')[-1]
            return output.replace('_', ' ').strip()

    def exec_(self, macro=''):
        """ Runs this tool with the inputed macro command
            
            :param str macro: macro
        """
        # run standalone
        if self.toolType() & ToolType.LegacyExternal:
            blurdev.core.runStandalone(
                self.sourcefile(), architecture=self.architecture()
            )
        else:
            blurdev.core.runScript(
                self.sourcefile(),
                toolName=self.displayName(),
                architecture=self.architecture(),
            )

        # Log what tool was used and when.
        if self._usagestatsEnabled:
            info = {'name': self.objectName()}
            info['miscInfo'] = macro
            blurdev.tools.logUsage(info)

    def favoriteGroup(self):
        return self._favoriteGroup

    def header(self):
        if not self._header:
            self._header = blurdev.tools.toolheader.ToolHeader(self)
        return self._header

    def icon(self):
        path = self.relativePath(self._icon)
        if not (path and os.path.isfile(path)):
            # Return default icon if none was set or exists
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'resource',
                'img',
                'blank.png',
            )
        return path

    def image(self, replace=None):
        """ Returns a QImage of the icon including any alpha channel """
        from PyQt4.QtGui import QImage

        iconName = self.icon()
        if isinstance(replace, (tuple, list)):
            iconName = iconName.replace(replace[0], replace[1])
        ret = QImage(iconName)
        isBmp = os.path.splitext(iconName)[-1] == '.bmp'
        if isBmp:
            alpha = QImage(iconName.replace('.bmp', '_a.bmp'))
            if not alpha.isNull():
                ret.setAlphaChannel(alpha)
        return ret

    def isFavorite(self):
        return self._favorite

    def isNull(self):
        return self.objectName() == ''

    def isLegacy(self):
        return self.toolType() in (
            ToolType.LegacyExternal,
            ToolType.LegacyStudiomax,
            ToolType.LegacySoftimage,
        )

    def index(self):
        """ returns the index from which this category is instantiated
            \return		<blurdev.tools.ToolIndex>
        """
        output = self.parent()
        while output and not isinstance(output, blurdev.tools.toolsindex.ToolsIndex):
            output = output.parent()
        return output

    def path(self):
        return self._path

    def projectFile(self):
        return self.relativePath('%s.blurproj' % self.displayName())

    def redistributable(self):
        """ If False, this tool should be excluded from offsite distro. """
        return self._redistributable

    def setRedistributable(self, state):
        self._redistributable = state

    def relativePath(self, relpath):
        output = os.path.join(self.path(), relpath)
        return output

    def setDisabled(self, state):
        self._disabled = state

    def setDisplayName(self, name):
        self._displayName = name

    def setFavorite(self, state=True):
        self._favorite = state

    def setFavoriteGroup(self, favoriteGroup):
        self._favoriteGroup = favoriteGroup
        if favoriteGroup:
            self.setFavorite()

    def setIcon(self, icon):
        self._icon = icon

    def setPath(self, path):
        self._path = str(path).replace(
            str(self.objectName()).lower(), self.objectName()
        )  # ensure that the tool id is properly formated since it is case sensitive

    def setSourcefile(self, sourcefile):
        self._sourcefile = str(sourcefile).replace(
            str(self.objectName()).lower(), self.objectName()
        )  # ensure that the tool id is properly formated since it is case sensitive

    def setToolTip(self, tip):
        self._toolTip = tip

    def setToolType(self, toolType):
        """ sets the current tools type
            :param toolType: ToolType
            
        """
        self._toolType = toolType

    def setUsagestatsEnabled(self, state):
        self._usagestatsEnabled = state

    def setVersion(self, version):
        self._version = version

    def setWikiPage(self, wiki):
        self._wikiPage = wiki

    def sourcefile(self):
        return self._sourcefile

    def toolTip(self):
        return self._toolTip

    def toolType(self):
        """ returns the toolType for this category
        """
        return self._toolType

    def usagestatsEnabled(self):
        return self._usagestatsEnabled

    def version(self):
        return self._version

    def wikiPage(self):
        return self._wikiPage

    @staticmethod
    def fromIndex(index, xml):
        """ creates a new tool record based on the inputed xml information for the given index
            :param index: <ToolsIndex>
            :param xml: <blurdev.XML.XMLElement>
        """
        output = Tool()
        output.setObjectName(xml.attribute('name'))

        # load modern tools
        loc = xml.attribute('loc')
        if loc:
            output.setPath(os.path.split(index.environment().relativePath(loc))[0])
        else:
            # load legacy tools
            output.setToolType(ToolType.fromString(xml.attribute('type', 'AllTools')))
            filename = xml.attribute('src')
            output.setPath(
                os.path.split(filename)[0]
                + '/%s_resource' % os.path.basename(filename).split('.')[0]
            )
            output.setSourcefile(filename)
            output.setIcon(xml.attribute('icon'))

        # load the meta data
        data = xml.findChild('data')
        if data:
            output.setVersion(data.attribute('version'))
            output.setIcon(data.findProperty('icon'))
            output.setSourcefile(output.relativePath(data.findProperty('src')))
            output.setWikiPage(data.findProperty('wiki'))
            output.setToolType(ToolType.fromString(data.attribute('type', 'AllTools')))
            output.setDisplayName(data.findProperty('displayName', output.objectName()))
            output.setDisabled(data.findProperty('disabled', 'false').lower() == 'true')
            output.setUsagestatsEnabled(
                data.findProperty('usagestats', 'true').lower() == 'true'
            )
            output.setToolTip(data.findProperty('toolTip', ''))
            output.setArchitecture(data.findProperty('architecture', None))
            output.setRedistributable(
                data.findProperty('redistributable', 'true').capitalize() == 'True'
            )

        # add the tool to the category or index
        category = index.findCategory(xml.attribute('category'))
        if category:
            category.addTool(output)
        else:
            output.setParent(index)

        # cache the tool in the index
        index.cacheTool(output)

        return output
