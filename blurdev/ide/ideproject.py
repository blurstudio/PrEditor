##
# 	\namespace	blurdev.ide.ideproject
#
# 	\remarks	Stores information about a project
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtCore import QObject


class IdeProjectItem(QObject):
    def __init__(self, parent):
        QObject.__init__(self, parent)

        self._filePath = ''
        self._group = True
        self._fileSystem = False
        self._icon = None

        self._exclude = ['.svn']
        self._fileTypes = '*.py;;*.pyw;;*.xml;;*.ui;;*.nsi;;*.bat;;*.schema;;*.txt;;*.blurproj'.split(
            ';;'
        )

    def exclude(self):
        return self._exclude

    def filePath(self):

        if not self.isFileSystem() and self._filePath:

            if self.project():

                options = {'PROJECTPATH': self.project().filePath()}

            else:

                options = {}

            from blurdev.ide.idetemplate import IdeTemplate

            return IdeTemplate.formatText(self._filePath, options)

        return self._filePath

    def fileInfo(self):
        from PyQt4.QtCore import QFileInfo

        if self.isFileSystem():
            return QFileInfo(self.filePath())
        return QFileInfo()

    def fileTypes(self):
        return self._fileTypes

    def icon(self):
        if not self._icon:
            from PyQt4.QtGui import QIcon

            if self.isFileSystem():
                from PyQt4.QtGui import QFileIconProvider

                provider = QFileIconProvider()
                self._icon = provider.icon(self.fileInfo())
            else:
                import blurdev

                iconfile = blurdev.resourcePath('img/folder.png')
                self._icon = QIcon(iconfile)

        return self._icon

    def isGroup(self):
        return self._group

    def isFileSystem(self):
        return self._fileSystem

    def load(self):
        if self.isGroup():
            return False

        dirmap = {}

        root = self
        while root and root.isFileSystem():
            root = root.parent()

        exclude = root.exclude()
        fileTypes = root.fileTypes()

        import os

        first = True
        for root, dirs, files in os.walk(str(self.filePath())):
            if first:
                parent = self
            else:
                parent = dirmap.get(root, None)

            if not parent:
                continue

            # load the dirs
            dirs.sort()
            for d in dirs:
                if not d in exclude:
                    child = IdeProjectItem(parent)
                    child.setObjectName(d)
                    fpath = os.path.join(root, d)
                    child.setFilePath(fpath)
                    child.setFileSystem(True)
                    dirmap[fpath] = child

            # load the files
            files.sort()
            for f in files:
                ftype = os.path.splitext(f)[1]
                if not fileTypes or ('*' + ftype) in fileTypes:
                    child = IdeProjectItem(parent)
                    child.setObjectName(f)
                    fpath = os.path.join(root, f)
                    child.setFilePath(fpath)
                    child.setFileSystem(True)

            first = False

        return True

    def project(self):

        output = self

        while output and not isinstance(output, IdeProject):

            output = output.parent()

        return output

    def refresh(self):
        if not self.isGroup():
            children = list(self.children())

            # clear the children
            for child in children:
                if isinstance(child, IdeProjectItem):
                    child.setParent(None)
                    child.deleteLater()

            self.load()

    def setGroup(self, state):
        self._group = state

    def setExclude(self, exclude):
        self._exclude = exclude

    def setFilePath(self, filePath):
        self._filePath = filePath

    def setFileSystem(self, state):
        self._fileSystem = state
        if state:
            self._group = False

    def setFileTypes(self, ftypes):
        self._fileTypes = ftypes

    def toXml(self, parent):
        if self.isFileSystem():
            return

        xml = parent.addNode('folder')
        xml.setAttribute('name', self.objectName())
        xml.setAttribute('group', self.isGroup())
        xml.setAttribute('filePath', self.filePath())
        xml.setAttribute('exclude', ';;'.join(self.exclude()))
        xml.setAttribute('fileTypes', ';;'.join(self.fileTypes()))

        for child in self.children():
            child.toXml(xml)

    @staticmethod
    def fromXml(xml, parent):
        out = IdeProjectItem(parent)
        out.setObjectName(xml.attribute('name'))
        out.setGroup(xml.attribute('group') != 'False')
        out.setFilePath(xml.attribute('filePath'))

        exclude = xml.attribute('exclude')
        if exclude:
            out.setExclude(exclude.split(';;'))

        ftypes = xml.attribute('fileTypes')
        if ftypes:
            out.setFileTypes(ftypes.split(';;'))

        # load children

        for child in xml.children():

            IdeProjectItem.fromXml(child, out)

        # load the filesystem
        out.refresh()
        return out


class IdeProject(IdeProjectItem):
    __version__ = 1.0

    DefaultPath = 'c:/blur/dev'
    Favorites = []

    def __init__(self, parent=None):
        QObject.__init__(self, parent)

        self._filename = ''

    def filename(self):
        return self._filename

    def filePath(self):

        import os.path

        return os.path.split(str(self.filename()))[0]

    def isNull(self):
        return self._filename == ''

    def save(self):
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        if not filename:
            from PyQt4.QtGui import QFileDialog

            filename = QFileDialog.getSaveFileName(self.window(), 'Save File as...')

        if filename:
            filename = str(filename)

            from blurdev.XML import XMLDocument

            doc = XMLDocument()

            root = doc.addNode('blurproj')
            root.setAttribute('version', self.__version__)

            folders = root.addNode('folders')
            for child in self.children():
                child.toXml(folders)

            doc.save(filename)
            return True
        return False

    def findPathGroup(self, path):
        import os.path

        normpath = os.path.normcase(str(path))
        for child in self.findChildren(IdeProjectItem):
            if not child.isGroup():
                normcheck = os.path.normcase(str(child.path()))
                if normcheck == normpath:
                    return child
        return None

    def setFilename(self, filename):
        self._filename = filename

    @staticmethod
    def fromTool(tool):
        # see if the tool has a project file
        import os.path

        projectfile = tool.projectFile()
        if os.path.exists(projectfile):
            return IdeProject.fromXml(projectfile)

        # otherwise, generate a project on the fly
        proj = IdeProject()
        proj.setObjectName(tool.objectName())

        import blurdev

        # determine the language for the source file
        sourcefile = tool.sourcefile()
        ext = os.path.splitext(sourcefile)[1]

        # external files are python (usually)
        if ext == '.lnk':
            ext = '.py'

        import lexers

        lang = lexers.languageForExt(ext)
        lexerMap = lexers.lexerMap(lang)

        fileTypes = ['*.xml', '*.ui', '*.txt', '*.ini']
        if lexerMap:
            fileTypes += ['*' + ftype for ftype in lexerMap.fileTypes]

        # support legacy libraries & structures
        if tool.isLegacy():
            # create the library path
            libs = IdeProjectItem(proj)
            libs.setObjectName('Libraries')
            libs.setFilePath(
                blurdev.activeEnvironment().relativePath('maxscript/treegrunt/lib')
            )
            libs.setFileTypes(fileTypes)
            libs.setGroup(False)
            libs.refresh()

            # create the resource folder
            resc = IdeProjectItem(proj)
            resc.setObjectName('Resources')
            resc.setFilePath(tool.path())
            resc.setFileTypes(fileTypes)
            resc.setGroup(False)
            resc.refresh()

            # create the main file
            src = IdeProjectItem(proj)
            src.setObjectName(os.path.basename(sourcefile))
            src.setFilePath(sourcefile)
            src.setFileSystem(True)

        else:
            if lang:
                # create the library path
                libs = IdeProjectItem(proj)
                libs.setObjectName('Libraries')
                libs.setFilePath(
                    blurdev.activeEnvironment().relativePath('code/%s/lib' % lang)
                )
                libs.setGroup(False)
                libs.setFileTypes(fileTypes)
                libs.refresh()

            # create the main package
            packg = IdeProjectItem(proj)
            packg.setObjectName(tool.displayName())
            packg.setFileTypes(fileTypes)
            packg.setFilePath(tool.path())
            packg.setGroup(False)
            packg.refresh()

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
            if root.nodeName == 'blurproj':
                output = IdeProject()
                output.setFilename(filename)
                output.setObjectName(os.path.basename(filename).split('.')[0])

                folders = root.findChild('folders')
                for folder in folders.children():
                    IdeProjectItem.fromXml(folder, output)
        return output
