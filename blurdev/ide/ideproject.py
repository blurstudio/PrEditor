##
# 	\namespace	blurdev.ide.ideproject
#
# 	\remarks	Stores information about a project
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from builtins import str as text
import os
from Qt.QtGui import QPixmap
from Qt.QtWidgets import QItemDelegate, QTreeWidgetItem
from Qt import QtCompat

import blurdev.ide.config.common
import blurdev.ide.config.project


class IdeProjectDelegate(QItemDelegate):
    def __init__(self, tree):
        QItemDelegate.__init__(self, tree)

        self._currOverlay = None

    def drawDecoration(self, painter, option, rect, pixmap):
        QItemDelegate.drawDecoration(self, painter, option, rect, pixmap)

        # draw overlay icon
        if self._currOverlay:
            painter.drawPixmap(rect, QPixmap(self._currOverlay))

    def paint(self, painter, option, index):
        # extract the filesystem information
        item = self.parent().itemFromIndex(index)
        self._currOverlay = item.overlay()

        # paint the standard way
        super(IdeProjectDelegate, self).paint(painter, option, index)


class IdeProjectItem(QTreeWidgetItem):
    def __init__(self):
        QTreeWidgetItem.__init__(self)

        # create custom properties
        self._dataType = 'folder'
        self._filePath = ''
        self._group = True
        self._fileSystem = False
        self._exclude = ['.svn']
        self._fileTypes = [
            '.py',
            '.pyw',
            '.xml',
            '.ui',
            '.nsi',
            '.bat',
            '.schema',
            '.txt',
            '.blurproj',
            '.ini',
            '.js',
            '.html',
            '.css',
            '.yaml',
            '.sh',
            '.pytempl',
        ]
        self._loaded = False
        self._overlay = None

        # set the default icon
        from Qt.QtGui import QIcon
        import blurdev

        self.setIcon(0, QIcon(blurdev.resourcePath('img/folder.png')))
        self.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

    def __cmp__(self, other):
        if not isinstance(other, IdeProjectItem):
            return -1

        # compare two items of the same type
        if self.dataType() == other.dataType():
            return cmp(self.text(0), other.text(0))

        # sort folder items first
        elif self.dataType() == 'folder':
            return -1
        else:
            return 1

    def dataType(self):
        return self._dataType

    def exclude(self):
        return self._exclude

    def filePath(self):
        return self._filePath

    def fileInfo(self):
        from Qt.QtCore import QFileInfo

        if self.isFileSystem():
            return QFileInfo(self.filePath())
        return QFileInfo()

    def fileTypes(self):
        return self._fileTypes

    def isGroup(self):
        return self._group

    def isFile(self):
        from Qt.QtCore import QFileInfo

        return QFileInfo(self.filePath()).isFile()

    def isFileSystem(self):
        return self._fileSystem

    def overlay(self):
        return self._overlay

    def load(self):
        if self._loaded:
            return True
        self._loaded = True

        # don't need to load custom groups
        if self.isGroup():
            return False

        # don't need to load files
        elif self.isFile():
            return False

        # collect overlay finders
        tree = self.treeWidget()
        overlayFinder = None
        if tree:
            from blurdev.ide.ideregistry import RegistryType

            overlayFinder = tree.window().registry().find(RegistryType.Overlay, '*')

        # set the overlay for this item
        if overlayFinder:
            self.setOverlay(overlayFinder(self.filePath()))

        # only show the indicator when there are children
        self.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        exclude = self.exclude()
        fileTypes = self.fileTypes()
        folders = []
        files = []

        import os
        from Qt.QtCore import QDir, QFileInfo

        path = self.filePath()
        # Check for a invalid path and notify the user by updating the text of the folder.
        try:
            dirs = os.listdir(path)
        except WindowsError:
            txt = self.text(0)
            if not txt.endswith('(Invalid Path)'):
                self.setText(0, '%s (Invalid Path)' % txt)
            dirs = []
        # if .* is provided add all files
        allFiles = '.*' in fileTypes
        for d in dirs:
            # ignore directories in the exclude group
            if d in exclude:
                continue
            fpath = os.path.join(path, d)
            finfo = QFileInfo(fpath)
            if finfo.isFile():
                if allFiles:
                    files.append(fpath)
                else:
                    ext = os.path.splitext(fpath)[1]
                    if ext in fileTypes:
                        files.append(fpath)
            else:
                folders.append(fpath)

        # sort the data alphabetically
        folders.sort(key=text.lower)
        files.sort(key=text.lower)

        # load the icon provider
        from Qt.QtWidgets import QFileIconProvider

        iconprovider = QFileIconProvider()

        # add the folders
        for folder in folders:
            self.addChild(
                IdeProjectItem.createFolderItem(
                    folder,
                    iconprovider,
                    fileTypes,
                    exclude,
                    overlayFinder=overlayFinder,
                )
            )

        # add the files
        for file in files:
            self.addChild(
                IdeProjectItem.createFileItem(
                    file, iconprovider, overlayFinder=overlayFinder
                )
            )

        # MCH 10/18/12 HACK: After updating to 4.8.3 the project tree would not update its vertical scroll bar the first time a item was expanded
        # calling updateGeometries seems to fix the problem, but there should be a better way to handle this. I am assuming that its a problem
        # with the sizes of the child items not being updated when the scrollbar is updated.
        tree.updateGeometries()

    def loadXml(self, xml):
        self.setText(0, xml.attribute('name'))
        self.setGroup(xml.attribute('group') != 'False')
        self.setFilePath(xml.attribute('filePath'))
        exclude = xml.attribute('exclude')
        if exclude:
            # support legacy ';;' requirement
            self.setExclude(
                [ftype.lstrip('*') for ftype in exclude.replace(';;', ';').split(';')]
            )

        ftypes = xml.attribute('fileTypes')
        if ftypes:
            # support legacy ';;' requirement
            self.setFileTypes(
                [ftype.lstrip('*') for ftype in ftypes.replace(';;', ';').split(';')]
            )

        # load children
        children = []
        for child in xml.children():
            children.append(IdeProjectItem.fromXml(child, self))

        # sort the children
        children.sort()

        # add the children to the item
        self.addChildren(children)

    def project(self):
        output = self
        while output and not isinstance(output, IdeProject):
            output = output.parent()
        return output

    def recordOpenState(self, item=None, key=''):
        output = []
        if not item:
            for i in range(self.topLevelItemCount()):
                output += self.recordOpenState(self.topLevelItem(i))
        else:
            text = item.text(0)
            if item.isExpanded():
                output.append(key + text)
            key += text + '::'
            for c in range(item.childCount()):
                output += self.recordOpenState(item.child(c), key)
        return output

    def refresh(self):
        # File items have nothing to refresh so refresh their parent
        if self.dataType() == 'file':
            parent = self.parent()
            if parent:
                path = self.filePath()
                parent.refresh()
                # restore selection of the current item
                for index in range(parent.childCount()):
                    child = parent.child(index)
                    if child.filePath() == path:
                        child.treeWidget().setCurrentItem(child)
                        break
                return
        # refreshing only happens on non-groups
        if not self.isGroup():
            # store the children
            openState = self.recordOpenState(self)
            # remove the children's expanded state
            self.takeChildren()
            self._loaded = False

            # load the items
            self.load()
            # restore the children's expanded state
            self.restoreOpenState(openState, self)

    def restoreOpenState(self, openState, item=None, key=''):
        if not item:
            for i in range(self.topLevelItemCount()):
                self.restoreOpenState(openState, self.topLevelItem(i))
        else:
            text = item.text(0)
            itemkey = key + text
            if itemkey in openState:
                item.setExpanded(True)
            key += text + '::'
            for c in range(item.childCount()):
                self.restoreOpenState(openState, item.child(c), key)

    def setGroup(self, state):
        self._group = state

    def setExclude(self, exclude):
        self._exclude = exclude

    def setFilePath(self, filePath):
        self._filePath = os.path.abspath(filePath)

    def setFileSystem(self, state):
        self._fileSystem = state
        if state:
            self._group = False

    def setFileTypes(self, ftypes):
        self._fileTypes = ftypes

    def setOverlay(self, overlay):
        self._overlay = overlay

    def toXml(self, parent):
        if self.isFileSystem():
            return

        xml = parent.addNode(self.dataType())
        xml.setAttribute('name', self.text(0))
        xml.setAttribute('group', self.isGroup())
        xml.setAttribute('filePath', self.filePath())
        xml.setAttribute('exclude', ';'.join(self.exclude()))
        xml.setAttribute('fileTypes', ';'.join(self.fileTypes()))

        for c in range(self.childCount()):
            self.child(c).toXml(xml)

    @staticmethod
    def createFolderItem(
        folder, iconprovider=None, fileTypes=[], exclude=[], overlayFinder=None
    ):
        from Qt.QtCore import QDir, QFileInfo

        if not iconprovider:
            from Qt.QtWidgets import QFileIconProvider

            iconprovider = QFileIconProvider()

        item = IdeProjectItem()
        item.setText(0, QDir(folder).dirName())
        item.setIcon(0, iconprovider.icon(QFileInfo(folder)))
        item.setFilePath(folder)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        item.setFileSystem(True)
        item.setExclude(exclude)
        item.setFileTypes(fileTypes)

        # lookup the overlay icon
        if overlayFinder:
            overlay = overlayFinder(folder)
            if overlay:
                item.setOverlay(overlay)

        return item

    @staticmethod
    def createFileItem(filename, iconprovider=None, overlayFinder=None):
        from Qt.QtCore import QFileInfo
        import os.path

        if not iconprovider:
            from Qt.QtWidgets import QFileIconProvider

            iconprovider = QFileIconProvider()

        # create the item and initialize its properties
        item = IdeProjectItem()
        item._dataType = 'file'
        item.setText(0, os.path.basename(filename))
        item.setFilePath(filename)
        item.setGroup(False)
        item.setFileSystem(True)
        item.setIcon(0, iconprovider.icon(QFileInfo(filename)))
        item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)

        # lookup the overlay icon
        if overlayFinder:
            overlay = overlayFinder(filename)
            if overlay:
                item.setOverlay(overlay)

        return item

    @staticmethod
    def fromXml(xml, parent):
        # create a custom group
        if xml.nodeName == 'folder':
            out = IdeProjectItem()
            out.loadXml(xml)

        # create a file item (ignoring the filesystem option)
        else:
            out = IdeProjectItem.createFileItem(xml.attribute('filePath'))
            out.setFileSystem(False)

        return out


class IdeProject(IdeProjectItem):
    __version__ = 1.0

    Favorites = []

    _currentProject = None

    def __init__(self):
        IdeProjectItem.__init__(self)

        # initialize the project item
        from Qt.QtGui import QIcon

        import blurdev

        self.setIcon(0, QIcon(blurdev.resourcePath('img/project.png')))
        self._filename = ''

        # intiailize the override settings
        from blurdev.gui.dialogs.configdialog import ConfigSet

        self._configSet = ConfigSet()
        self._configSet.loadPlugins(blurdev.ide.config.common)
        self._configSet.loadPlugins(blurdev.ide.config.project)

        # record project specific environment variables and sys.paths
        self._envvars = {}
        self._syspaths = []
        self._origEnv = None
        self._origSys = None
        self._argumentList = {}
        self._commandList = {}

    def activateSystem(self):
        # update the os.environ variable with this projects environment variables
        import os
        import sys

        # record the original information
        self._origEnv = os.environ.copy()
        self._origSys = list(sys.path)

        os.environ.update(self._envvars)

        # update the sys.paths variable with this environments paths
        sys.path = self._syspaths + sys.path

    def argumentList(self):
        return self._argumentList

    def commandList(self):
        return self._commandList

    def deactivateSystem(self):
        # unregister all the project specific override information
        import os
        import sys

        # restore the system variables
        if self._origEnv != None:
            os.environ = self._origEnv
        if self._origSys != None:
            sys.path = self._origSys

    def configSet(self):
        return self._configSet

    def exists(self):
        return os.path.exists(self.filename())

    def filename(self):
        return self._filename

    def registerVariable(self, key, value):
        self._envvars[str(key)] = str(value)

    def registerPath(self, path):
        path = str(path).strip()
        if path and not path in self._syspaths:
            self._syspaths.append(path)

    def save(self):
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        if not filename:
            filename, _ = QtCompat.QFileDialog.getSaveFileName(self, 'Save File as...')

        if filename:
            filename = str(filename)

            from blurdev.XML import XMLDocument

            doc = XMLDocument()

            root = doc.addNode('blurproj')
            root.setAttribute('version', self.__version__)

            # record the config set
            self.configSet().recordToXml(root)

            # define the env variables
            envvarsxml = root.addNode('envvars')
            for key, value in self._envvars.items():
                envvar = envvarsxml.addNode('variable')
                envvar.setAttribute('key', key)
                envvar.setAttribute('value', value)

            # define the sys paths
            syspathsxml = root.addNode('syspaths')
            for path in self._syspaths:
                syspath = syspathsxml.addNode('path')
                syspath.setAttribute('path', path)

            command = root.addNode('commands')
            command.recordProperty('argumentList', self._argumentList)
            command.recordProperty('commandList', self._commandList)
            self.toXml(root)

            doc.save(filename)
            return True
        return False

    def setArgumentList(self, argumentList):
        self._argumentList = argumentList

    def setCommandList(self, commandList):
        self._commandList = commandList

    def setConfigSet(self, configSet):
        self._configSet = configSet

    def setFilename(self, filename):
        self._filename = filename

    @staticmethod
    def currentProject():
        return IdeProject._currentProject

    @staticmethod
    def setCurrentProject(project):
        # clear the old project information
        if IdeProject._currentProject:
            IdeProject._currentProject.deactivateSystem()

        IdeProject._currentProject = project
        if project:
            project.activateSystem()

    @staticmethod
    def fromTool(tool):
        # see if the tool has a project file
        import os.path

        projectfile = tool.projectFile()
        if os.path.exists(projectfile):
            return IdeProject.fromXml(projectfile)

        # otherwise, generate a project on the fly
        proj = IdeProject()
        proj.setText(0, tool.objectName())

        import blurdev

        # determine the language for the source file
        sourcefile = tool.sourcefile()
        ext = os.path.splitext(sourcefile)[1]

        # external files are python (usually)
        if ext == '.lnk':
            ext = '.py'

        from blurdev.ide import lang

        language = lang.byExtension(ext)

        fileTypes = ['.xml', '.ui', '.txt', '.ini']
        if language:
            fileTypes += language.fileTypes()

        # support legacy libraries & structures
        if tool.isLegacy():
            # create the library path
            libs = IdeProjectItem()
            libs.setText(0, 'Libraries')
            libs.setFilePath(
                blurdev.activeEnvironment().relativePath('maxscript/treegrunt/lib')
            )
            libs.setFileTypes(fileTypes)
            libs.setGroup(False)
            proj.addChild(libs)

            # create the resource folder
            resc = IdeProjectItem()
            resc.setText(0, 'Resources')
            resc.setFilePath(tool.path())
            resc.setFileTypes(fileTypes)
            resc.setGroup(False)
            proj.addChild(resc)

            # create the main file
            proj.addChild(IdeProjectItem.createFileItem(sourcefile))

        else:
            if lang:
                # create the library path
                libs = IdeProjectItem()
                libs.setText(0, 'Libraries')
                libs.setFilePath(
                    blurdev.activeEnvironment().relativePath('code/%s/lib' % lang)
                )
                libs.setGroup(False)
                libs.setFileTypes(fileTypes)
                proj.addChild(libs)

            # create the main package
            packg = IdeProjectItem()
            packg.setText(0, tool.displayName())
            packg.setFileTypes(fileTypes)
            packg.setFilePath(tool.path())
            packg.setGroup(False)
            proj.addChild(packg)

        return proj

    @staticmethod
    def fromXml(filename):
        from blurdev.XML import XMLDocument
        import os.path

        doc = XMLDocument()
        output = None
        filename = str(filename)

        if doc.load(filename):
            root = doc.root()

            # load a blur project
            if root.nodeName == 'blurproj':
                output = IdeProject()
                output.setFilename(filename)
                output.setText(0, os.path.basename(filename).split('.')[0])

                # load old style
                folders = root.findChild('folders')
                if folders:
                    for folder in folders.children():
                        output.addChild(IdeProjectItem.fromXml(folder, output))

                # restore the settings
                output.configSet().restoreFromXml(root)

                # load environment variables per project
                environvars = root.findChild('envvars')
                if environvars:
                    for child in environvars.children():
                        output.registerVariable(
                            child.attribute('key'), child.attribute('value')
                        )

                # load sys path variables per project
                syspaths = root.findChild('syspaths')
                if syspaths:
                    for child in syspaths.children():
                        output.registerPath(child.attribute('path'))

                # load the command list
                commands = root.findChild('commands')
                if commands:
                    args = commands.restoreProperty('argumentList', {})
                    if args:
                        output.setArgumentList(args)
                    cmds = commands.restoreProperty('commandList', {})
                    if cmds:
                        output.setCommandList(cmds)
                # load new style
                folder = root.findChild('folder')
                if folder:
                    output.loadXml(folder)

        return output
