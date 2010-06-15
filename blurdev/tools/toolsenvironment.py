##
# 	\namespace	blurdev.tools.ToolsEnvironment
#
# 	\remarks	Defines the ToolsEnvironment class for the tools package
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

from PyQt4.QtCore import QObject, pyqtSignal


class ToolsEnvironment(QObject):
    # static members
    environments = []

    def __init__(self):
        QObject.__init__(self)

        self._path = ''
        self._development = False
        self._default = False
        self._active = False
        self._offline = False
        self._index = None

    def clearPathSymbols(self):
        """
            \remarks	removes the path symbols from the environment
        """
        if self.isEmpty():
            return False

        path = self.normalizePath(self.path())

        import sys

        oldpaths = sys.path
        newpaths = [spath for spath in sys.path if not path in spath.lower()]
        sys.path = newpaths

        print '%s were removed from sys.path' % list(
            set(oldpaths).difference(set(newpaths))
        )

        newmodules = {}

        import blurdev

        symbols = blurdev.core.protectedModules()
        for key, value in sys.modules.items():
            if not key in symbols:
                found = False
                try:
                    found = path in value.__file__.lower()
                except:
                    pass

                if found:
                    print 'removing %s from sys.modules' % key
                    sys.modules.pop(key)

        return True

    def index(self):
        """
            \remarks	returns the index of tools for this environment
            \return		<blurdev.tools.index.Index>
        """
        if not self._index:
            from toolsindex import ToolsIndex

            self._index = ToolsIndex(self)
        return self._index

    def isActive(self):
        return self._active

    def isEmpty(self):
        return self._path == ''

    def isDevelopment(self):
        return self._development

    def isDefault(self):
        return self._default

    def isOffline(self):
        return self._offline

    def normalizePath(self, path):
        """
            \remarks	returns a normalized path for this environment to use when registering paths to the sys path
            \param		path		<str> || <QString>
            \return		<str>
        """
        import os.path

        return os.path.abspath(str(path)).lower()

    def path(self):
        return self._path

    def registerPath(self, path):
        """
            \remarks	registers the inputed path to the system
            \param		path		<str>
            \return		<bool> success
        """
        import os.path

        if path:
            import sys

            sys.path.insert(0, self.normalizePath(path))
            return True
        return False

    def relativePath(self, path):
        """
            \remarks	returns the relative path from the inputed path to this environment
            \return		<str>
        """
        if not self.isEmpty():
            import os.path

            return os.path.abspath(os.path.join(str(self.path()), str(path)))
        return ''

    def setActive(self):
        """
            \remarks	sets this environment as the active environment and switches the currently running modules from the
                        system
        """
        if not (self.isActive() or self.isEmpty()):
            # clear out the old environment
            old = self.activeEnvironment()
            old.clearPathSymbols()
            old._active = False

            # register this environment as active and update the path symbols
            self._active = True
            self.registerPath(self.path())

            # emit the environment activateion change signal
            import blurdev

            blurdev.core.environmentActivated.emit(old, self)

    def setDefault(self, state=True):
        self._default = state

    def setDevelopment(self, state=True):
        self._development = state

    def setOffline(self, state=False):
        self._offline = state

    def setPath(self, path):
        self._path = path

    def stripRelativePath(self, path):
        """
            \remarks	removes this environments path from the inputed path
            \return		<str>
        """
        return (
            self.normalizePath(path)
            .replace(self.normalizePath(self.path()), '')
            .lstrip('\\/')
        )

    @staticmethod
    def activeEnvironment():
        """
            \remarks	looks up the active environment for the system
            \return		<ToolsEnvironment>
        """
        for env in ToolsEnvironment.environments:
            if env.isActive():
                return env
        return ToolsEnvironment()

    @staticmethod
    def defaultEnvironment():
        """
            \remarks	looks up the default environment for the system
            \return		<ToolsEnvironment>
        """
        for env in ToolsEnvironment.environments:
            if env.isDefault():
                return env
        return ToolsEnvironment()

    @staticmethod
    def findEnvironment(name):
        """
            \remarks	looks up the environment by the inputed name
            \return		<ToolsEnvironment>
        """
        for env in ToolsEnvironment.environments:
            if env.objectName() == name:
                return env
        return ToolsEnvironment()

    @staticmethod
    def fromXml(xml):
        """
            \remarks	generates a new tools environment based on the inputed xml information
            \param		xml		<blurdev.XML.XMLElement>
            \return		<ToolsEnvironment>
        """
        output = ToolsEnvironment()

        output.setObjectName(xml.attribute('name'))
        output.setPath(xml.attribute('loc'))
        output.setDefault(xml.attribute('default') == 'True')
        output.setDevelopment(xml.attribute('development') == 'True')
        output.setOffline(xml.attribute('offline') == 'True')

        return output

    @staticmethod
    def loadConfig(filename):
        """
            \remarks	loads the environments from the inputed config file
            \param		filename		<str>
        """

        ToolsEnvironment.environments = []

        from blurdev.XML import XMLDocument

        doc = XMLDocument()
        if doc.load(filename):
            root = doc.root()
            for child in root.children():
                ToolsEnvironment.environments.append(ToolsEnvironment.fromXml(child))

            # initialize the default environment
            ToolsEnvironment.defaultEnvironment().setActive()
