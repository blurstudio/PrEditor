from __future__ import absolute_import
import os
import ntpath

from Qt.QtCore import QObject

import blurdev
from ..enum import enum
import blurdev.tools.toolsindex
import six


ToolType = enum(
    'External',  # 1
    'Trax',  # 2
    'Studiomax',  # 4
    'Softimage',  # 8
    'Fusion',  # 16
    'MotionBuilder',  # 32
    'LegacyExternal',  # 64
    'LegacyStudiomax',  # 128
    'LegacySoftimage',  # 255
    'Maya',  # 512
    'Nuke',  # 1024
    'Shotgun',  # 2048
    'RV',  # 4096
    'Mari',  # 8192
    'Houdini',  # 16384
    'Katana',  # 32768
    AllTools=65535,  # 2**16 - 1
)


class Tool(QObject):
    """Creates the ToolsCategory class for grouping tools together"""

    def __init__(self):
        QObject.__init__(self)
        self._displayName = ''
        self._path = ''
        self._sourcefile = ''
        self._toolTip = ''
        self._wikiPage = ''
        self._url = ''
        self._macros = []
        self._version = ''
        self._icon = ''
        self._toolType = 0
        self._architecture = None
        self._favorite = False
        self._redistributable = True
        self._disabled = False
        self._usagestatsEnabled = True
        self._cli_module = ''

    def architecture(self):
        """This tool needs to run in this architecture (32bit or 64bit) when running externally

        If this tool is run by external treegrunt, launch the tool with this version of
        python if possible. If None the system default will be used.
        """
        return self._architecture

    def setArchitecture(self, architecture):
        if isinstance(architecture, six.string_types):
            architecture = int(architecture)
        self._architecture = architecture

    def cli_module(self):
        """Optional module import name defining a custom cli for the tool.

        This module needs to implement a cli function using the click python module.
        If not defined, then a default cli will be used to launch the tool.

        Returns:
            str: The module name as it would be passed to the import command.
        """
        return self._cli_module

    def disabled(self):
        return self._disabled

    def displayName(self):
        if self._displayName:
            return self._displayName
        else:
            output = str(self.objectName()).split('::')[-1]
            return output.replace('_', ' ').strip()

    def exec_(self, macro=''):
        """Runs this tool with the inputted macro command

        Args:
            macro (str):
        """
        # The external Treegrunt tool sometimes gets deleted before we can collect
        # usage stats. Capture the name before we launch(exec_) the tool.
        name = self.objectName()
        # run standalone
        if self.toolType() & ToolType.LegacyExternal:
            blurdev.core.runStandalone(
                self.sourcefile(), architecture=self.architecture(), tool=self
            )
        else:
            blurdev.core.runScript(
                self.sourcefile(), tool=self, architecture=self.architecture()
            )

        # Log what tool was used and when.
        if self._usagestatsEnabled:
            info = {'name': name}
            info['miscInfo'] = macro
            blurdev.tools.logUsage(info)

    def icon(self):
        path = self.relativePath(self._icon)
        if not (path and os.path.isfile(path)):
            # Return default icon if none was set or exists
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'resource',
                'img',
                'tool.png',
            )
        return path

    def image(self, replace=None):
        """Returns a QImage of the icon including any alpha channel"""
        from Qt.QtGui import QImage

        iconName = self.icon()
        if isinstance(replace, (tuple, list)):
            iconName = iconName.replace(replace[0], replace[1])
        return QImage(iconName)

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

    def isVisible(self):
        """Returns False if the tool should be hidden based on filters.

        Returns:

            bool: If the tool is disabled and ToolsEnvironment.showDisabledTools is
                False returns False. If the none of the tools toolTypes are in
                `blurdev.core.selectedToolTypes()` False is returned.
        """
        if not blurdev.tools.ToolsEnvironment.showDisabledTools and self.disabled():
            return False
        return self.toolType() & blurdev.core.selectedToolTypes()

    def index(self):
        """returns the index from which this category is instantiated

        Returns:
            blurdev.tools.ToolIndex:
        """
        output = self.parent()
        while output and not isinstance(output, blurdev.tools.toolsindex.ToolsIndex):
            output = output.parent()
        return output

    def path(self):
        # The index stores the absolute path for the operating system it was built
        # on. Translate to the current operating system path if required.
        return blurdev.settings.toSystemPath(self._path)

    def projectFile(self):
        return self.relativePath('%s.blurproj' % self.displayName())

    def redistributable(self):
        """If False, this tool should be excluded from offsite distro."""
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
        # Update the set that is used to save user favorites if this is a valid tool.
        if not self.isNull():
            if state:
                self.index().favoriteToolIds().add(self.objectName())
            else:
                self.index().favoriteToolIds().discard(self.objectName())

    def setIcon(self, icon):
        self._icon = icon

    def set_cli_module(self, name):
        self._cli_module = name

    def setPath(self, path):
        self._path = str(path).replace(
            str(self.objectName()).lower(), self.objectName()
        )  # ensure that the tool id is properly formatted since it is case sensitive

    def setSourcefile(self, sourcefile):
        self._sourcefile = str(sourcefile).replace(
            str(self.objectName()).lower(), self.objectName()
        )  # ensure that the tool id is properly formatted since it is case sensitive

    def setToolTip(self, tip):
        self._toolTip = tip

    def setToolType(self, toolType):
        """sets the current tools type
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
        # The index stores the absolute path for the operating system it was built
        # on. Translate to the current operating system path if required.
        return blurdev.settings.toSystemPath(self._sourcefile)

    def toolTip(self, info=False):
        if info:
            if self._toolTip:
                tip = self._toolTip.replace('\n', '<br>')
                return '<b>{name}</b><br><br>{toolTip}'.format(
                    name=self.displayName(), toolTip=tip
                )
            else:
                return '<b>{name}</b>'.format(name=self.displayName())
        else:
            return self._toolTip

    def toolType(self):
        """returns the toolType for this category"""
        return self._toolType

    def usagestatsEnabled(self):
        return self._usagestatsEnabled

    def url(self):
        return self._url

    def setUrl(self, url):
        self._url = url

    def version(self):
        return self._version

    def wikiPage(self):
        return self._wikiPage

    @classmethod
    def fromIndex(cls, index, data, relative_root=None):
        """Creates a new tool record based on the provided information for the given
        index.

        Args:
            index (ToolsIndex):
            data (dict):
            relative_root (str, optional): Relative path joined to the path stored in
                data. This should only be used if data was built with a relative path.
                For example `blurdev.tools.setup_tools.buildCmdFactory` is used by pip
                packages to build a relative index.

        Returns:
            Tool: The created tool record.
        """
        output = cls()

        # NOTE: Not using os.path is intentional. Those functions are slower
        # than simple string formatting/replacing and the index is structured
        # enough that it shouldn't cause problems. The focus is on speed.

        # The code name of the tool
        output.setObjectName(data['name'])
        # The folder containing the tool
        path = data['path']
        if relative_root:
            path = os.path.join(relative_root, path)
        # TODO: This isabs  if statement can be removed once the studio has migrated
        # to the new absolute path treegrunt index system. ntpath is used because
        # it understands unc paths and understands linux `/mnt/path` paths.
        if not ntpath.isabs(path):
            path = '{}/{}'.format(index.environment().path(), path)
        src = data['src']
        # If this is a legacy tool, we need to build the path differently.
        if data.get('legacy', False):
            srcBase = src.replace('\\', '/').rsplit('/', 1)[-1].rsplit('.', 1)[0]
            path = '{}/{}_resource'.format(path, srcBase)
        output.setPath(path)
        # The file that starts the tool. To handle legacy and modern tool structures.
        # (legacy needs ../ to get out of the _resource folder)
        output.setSourcefile('{}/{}'.format(path, src))

        output.setDisplayName(data.get('displayName', ''))
        output.setToolType(ToolType.fromString(data.get('types', 'AllTools')))
        output.setToolTip(data.get('tooltip', ''))
        output.setVersion(data.get('version', 1.0))
        output.setIcon(data.get('icon', ''))
        output.setWikiPage(data.get('wiki', ''))
        output.setUrl(data.get('url', ''))
        output.setDisabled(data.get('disabled', False))
        output.setUsagestatsEnabled(data.get('usagestats', True))
        output.setArchitecture(data.get('architecture'))
        output.setRedistributable(data.get('redistributable', True))
        output.set_cli_module(data.get('cliModule', ''))

        # Add the tool to the category or index
        category = index.findCategory(data.get('category'))
        if category:
            category.addTool(output)
        else:
            output.setParent(index)

        # cache the tool in the index
        index.cacheTool(output)

        return output
