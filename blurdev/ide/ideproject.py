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
        self._fileTypes = ['*.py', '*.pyw', '*.xml', '*.ui']

    def filePath(self):
        return self._filePath

    def fileInfo(self):
        from PyQt4.QtCore import QFileInfo

        if self.isFileSystem():
            return QFileInfo(self.filePath())
        return QFileInfo()

    def icon(self):
        if not self._icon:
            from PyQt4.QtGui import QIcon

            if self.isFileSystem():
                from PyQt4.QtGui import QFileIconProvider

                provider = QFileIconProvider()
                self._icon = provider.icon(self.fileInfo())
            else:
                import blurdev

                iconfile = blurdev.relativePath(__file__, 'img/folder.png')
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
                if not d in self._exclude:
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
                if not self._fileTypes or ('*' + ftype) in self._fileTypes:
                    child = IdeProjectItem(parent)
                    child.setObjectName(f)
                    fpath = os.path.join(root, f)
                    child.setFilePath(fpath)
                    child.setFileSystem(True)

            first = False

        return True

    def refresh(self):
        if not self.isGroup():
            children = list(self.children())
            for child in children:
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

    def setFileTypes(self, ftypes):
        self._fileTypes = ftypes

    @staticmethod
    def fromXml(xml):
        out = IdeProjectItem(None)
        out.setObjectName(xml.attribute('name'))
        out.setGroup(xml.attribute('group') != 'False')
        out.setFilePath(xml.attribute('filePath'))
        out.refresh()

        exclude = xml.attribute('exclude')
        if exclude:
            out.setExclude(exclude.split(';;'))

        ftypes = xml.attribute('fileTypes')
        if ftypes:
            out.setFileTypes(ftypes.split(';;'))

        return out


class IdeProject(IdeProjectItem):
    def __init__(self, parent=None):
        QObject.__init__(self, parent)

    def findPathGroup(self, path):
        import os.path

        normpath = os.path.normcase(str(path))
        for child in self.findChildren(IdeProjectItem):
            if not child.isGroup():
                normcheck = os.path.normcase(str(child.path()))
                if normcheck == normpath:
                    return child
        return None

    @staticmethod
    def fromXml(filename):
        from blurdev.XML import XMLDocument

        doc = XMLDocument()
        output = None
        if doc.load(filename):
            root = doc.root()
            if root.nodeName == 'bluride':
                output = IdeProject()
                output.setObjectName(root.attribute('project'))

                folders = root.findChild('folders')
                for folder in folders.children():
                    item = IdeProjectItem.fromXml(folder)
                    item.setParent(output)
        return output
