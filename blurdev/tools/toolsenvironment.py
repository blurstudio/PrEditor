# #
# 	\namespace	blurdev.tools.ToolsEnvironment
#
# 	\remarks	Defines the ToolsEnvironment class for the tools package
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#
from __future__ import absolute_import

import os
import sys
import re
import datetime

from PyQt4.QtCore import QObject, pyqtSignal, QDateTime

import blurdev
import blurdev.tools.toolsindex
import blur.Projects


USER_ENVIRONMENT_FILE = 'c:/blur/common/user_environments.xml'


class ToolsEnvironment(QObject):
    """ Defines the ToolsEnvironment class for the tools package
    """

    # static members
    environments = []
    # Should disabled tools be shown
    showDisabledTools = False
    # Enabled the first time an environment is evaluated
    initialized = False

    def __init__(self):
        QObject.__init__(self)

        self._path = ''
        self._development = False
        self._default = False
        self._active = False
        self._offline = False
        self._custom = False
        self._temporary = False
        self._index = None
        self._sourcefile = ''
        self._emailOnError = []
        self._legacyName = ''
        self._timeout = ''
        self._autoupdate = False
        self._keychain = ''
        self._project = ''
        # Set blurdev.activeEnvironment().stopwatchEnabled to True to enable the environment
        # tool stopwatch this will start a stopwatch every time blurdev.core.runScript is
        # called and stop it once that script has finished(this should include showEvent).
        # This will allow you to time how long it takes to launch a tool.
        # You can add laps by calling blurdev.activeEnvironment().stopwatch.newLap('info text')
        self.stopwatchEnabled = False
        self.stopwatch = blurdev.debug.Stopwatch('Default tool')

    def __str__(self):
        return '<ToolsEnvironment ({})>'.format(self.objectName())

    def _get_project(self):
        """ Used by blur.Projects.customize to identify the environment project if set
        """
        return self.project()

    def clearPathSymbols(self):
        """
        Removes the path symbols from the environment
        """
        if self.isEmpty():
            return False

        # If this environment has a project make sure we unload the project settings
        # if neccissary before we clear the path symbols.
        self.deactivateProject()

        path = self.normalizePath(self.path())

        # do not remove python path variables
        pythonpath = [
            split.lower() for split in os.environ.get('pythonpath', '').split(';')
        ]
        # do not remove paths for protected modules.
        symbols = blurdev.core.protectedModules()
        for name in symbols:
            mod = sys.modules.get(name)
            if mod:
                try:
                    pythonpath.append(
                        self.normalizePath(os.path.split(mod.__file__)[0])
                    )
                except:
                    pass

        oldpaths = sys.path
        newpaths = [
            spath
            for spath in sys.path
            if (path not in spath.lower() and spath != '.')
            or spath.lower() in pythonpath
        ]
        sys.path = newpaths

        newmodules = {}

        for key, value in sys.modules.items():
            protected = False
            if key in symbols:
                protected = True

            # Used by multiprocessing library, don't remove this.
            if key == '__parents_main__':
                protected = True

            # Protect submodules of protected packages
            ckey = key
            while not protected and '.' in ckey:
                ckey = ckey.rsplit('.', 1)[0]
                if ckey in symbols:
                    protected = True

            if protected:
                continue

            else:
                # Only clear out modules that are loaded from the environment system.
                # This excludes locally installed packages, packages that are
                # loaded from outside the environment system via pythonpath or
                # sys.path manipulation, and any other module that exists
                # outside the environment paths.
                try:
                    is_environment_package = path in value.__file__.lower()
                except Exception:
                    pass
                else:
                    if is_environment_package:
                        sys.modules.pop(key)

        return True

    @blur.Projects.customize
    def activateProject(self):
        pass

    @blur.Projects.customize
    def deactivateProject(self):
        pass

    @blur.Projects.customize
    def constructProjectForApplication(self, app):
        return None

    @blur.Projects.customize
    def destructProjectForApplication(self, app):
        return None

    def emailOnError(self):
        return self._emailOnError

    def index(self):
        """
            \remarks	returns the index of tools for this environment
            \return		<blurdev.tools.index.Index>
        """
        if not self._index:
            self._index = blurdev.tools.toolsindex.ToolsIndex(self)
        return self._index

    def isActive(self):
        return self._active

    def isEmpty(self):
        return self._path == ''

    def isCustom(self):
        return self._custom

    def isDevelopment(self):
        return self._development

    def isDefault(self):
        return self._default

    def isOffline(self):
        return self._offline

    def isTemporary(self):
        return self._temporary

    def keychain(self):
        return self._keychain

    def legacyName(self):
        return self._legacyName

    def path(self):
        return self._path

    def project(self):
        return self._project

    def autoUpdate(self):
        return self._autoupdate

    def timeout(self):
        return self._timeout

    def timeoutTimedelta(self):
        if not self._timeout:
            return None
        try:
            type_map = {
                'd': 'days',
                'm': 'minutes',
                'h': 'hours',
                's': 'seconds',
                'w': 'weeks',
            }
            d = {}
            print 'TIMEOUT', self._timeout
            for arg in self._timeout.split(':'):
                m = re.match(r'(?P<num>\d+)(?P<type>[dmhsw])', arg, re.I)
                print arg, m
                if not m:
                    continue
                gd = m.groupdict()
                d[type_map[gd['type'].lower()]] = int(gd['num'])
            return datetime.timedelta(**d)

        except Exception:
            return None

    def timeoutThreshold(self):
        if not self._timeout:
            return None
        now = QDateTime.currentDateTime()
        try:
            print 'TIMEOUT', self._timeout
            for arg in self._timeout.split(':'):
                m = re.match(r'(?P<num>\d+)(?P<type>[dmhsw])', arg, re.I)
                print arg, m
                if not m:
                    continue
                gd = m.groupdict()
                num = int(gd['num'])
                type_ = gd['type'].lower()
                if type_ == 'w':
                    now = now.addDays(-num * 7)
                elif type_ == 'd':
                    now = now.addDays(-num)
                elif type_ == 'h':
                    now = now.addSecs(-num * 3600)
                elif type_ == 'm':
                    now = now.addSecs(-num * 60)
                elif type_ == 's':
                    now = now.addSecs(-num)

            return now

        except Exception:
            raise
            return None

    def recordXml(self, xml):
        envxml = xml.addNode('environment')
        envxml.setAttribute('name', self.objectName())
        envxml.setAttribute('loc', self.path())
        envxml.setAttribute('default', self._default)
        envxml.setAttribute('development', self._development)
        envxml.setAttribute('offline', self._offline)
        envxml.setAttribute('autoupdate', self._autoupdate)
        envxml.setAttribute('timeout', self._timeout)
        envxml.setAttribute('keychain', self._keychain)
        envxml.setAttribute('project', self._project)

        if self._legacyName != self.objectName():
            envxml.setAttribute('legacyName', self._legacyName)

        if self._custom:
            envxml.setAttribute('custom', True)

        if self._emailOnError:
            envxml.setAttribute(':'.join(self._emailOnError))

    def relativePath(self, path):
        """
            \remarks	returns the relative path from the inputed path to this environment
            \return		<str>
        """
        if not self.isEmpty():
            # posixpath.normpath does not convert windows slashes to prevent problems with escaping.
            # Our tool paths do not have spaces and should not need escaping
            path = str(path).replace('\\', '/')
            return os.path.abspath(os.path.join(str(self.path()), path))
        return ''

    def resetPaths(self):
        blurdev.core.aboutToClearPaths.emit()
        self.clearPathSymbols()
        self.registerPaths()
        blurdev.core.emitEnvironmentActivated()

    def setActive(self, silent=False, force=False):
        """ Sets this environment as the active environment.
    
        It also switches the currently running modules from the system by removing the old 
        environment path from sys.path and sys.modules. It then adds the paths for this
        environment to sys.path.
        
        Args:
            silent (bool): If True, do not emit the blurdev.core.environmentActivated signal.
                Defaults to False.
            force (bool): IF True, force this environment to reload, even if its is currently
                active. Defaults to False.
        
        Returns:
            bool: The environment was set active.
        """
        if force or not (self.isActive() or self.isEmpty()):
            # clear out the old environment
            old = self.activeEnvironment()
            old.clearPathSymbols()
            old._active = False

            # register this environment as active and update the path symbols
            self._active = True
            self.registerPaths()

            # set the legacy environment active
            blurdev.ini.SetActiveEnvironment(unicode(self.objectName()))

            # emit the environment activateion change signal
            if not silent:
                # core can be defined as None at this point in if this was called during blurdev.core init.
                if blurdev.core:
                    blurdev.core.emitEnvironmentActivated()

            return True
        return False

    def setCustom(self, state=True):
        self._custom = state

    def setDefault(self, state=True):
        self._default = state

    def setDevelopment(self, state=True):
        self._development = state

    def setOffline(self, state=False):
        self._offline = state

    def setEmailOnError(self, emails):
        if not emails:
            self._emailOnError = []
        else:
            self._emailOnError = [
                entry for entry in emails if str(entry) != '' and entry != None
            ]

    def setKeychain(self, keychain):
        self._keychain = keychain

    def setLegacyName(self, name):
        self._legacyName = name

    def setPath(self, path):
        self._path = path

    def setProject(self, project):
        self._project = project

    def setTimeout(self, timeout):
        self._timeout = timeout

    def setAutoUpdate(self, autoupdate):
        self._autoupdate = autoupdate

    def setSourceFile(self, filename):
        self._sourcefile = filename

    def setTemporary(self, state):
        self._temporary = state

    def sourceFile(self):
        return self._sourcefile

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
    def syncINIEnvironment(env):
        """
        Syncs a single environment definition with the legacy config.ini file.
        
        """
        name = env.objectName()
        legacy = env.legacyName()
        envPath = env.path()
        email = env.emailOnError()
        if not legacy:
            legacy = name
        # update the config.ini file so next time we start from the correct environment.
        codeRootPath = os.path.abspath(os.path.join(envPath, 'maxscript', 'treegrunt'))
        if os.path.exists(codeRootPath):
            blurdev.ini.SetINISetting(
                blurdev.ini.configFile, legacy, 'codeRoot', codeRootPath
            )
            blurdev.ini.SetINISetting(
                blurdev.ini.configFile,
                legacy,
                'startupPath',
                os.path.abspath(os.path.join(envPath, 'maxscript', 'treegrunt', 'lib')),
            )
            blurdev.ini.LoadConfigData()

    @staticmethod
    def syncINI():
        """
        Syncs all environments from the environment definition xml files to the
        legacy config.ini file.
                
        """
        for env in ToolsEnvironment.environments:
            name = env.objectName()
            legacy = env.legacyName()
            envPath = env.path()
            email = env.emailOnError()
            if not legacy:
                legacy = name
            # update the config.ini file so next time we start from the correct environment.
            codeRootPath = os.path.abspath(
                os.path.join(envPath, 'maxscript', 'treegrunt')
            )
            if os.path.exists(codeRootPath):
                blurdev.ini.SetINISetting(
                    blurdev.ini.configFile, legacy, 'codeRoot', codeRootPath
                )
                blurdev.ini.SetINISetting(
                    blurdev.ini.configFile,
                    legacy,
                    'startupPath',
                    os.path.abspath(
                        os.path.join(envPath, 'maxscript', 'treegrunt', 'lib')
                    ),
                )
                blurdev.ini.LoadConfigData()

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
    def createNewEnvironment(
        name,
        path,
        default=False,
        development=False,
        offline=True,
        environmentFile='',
        legacyName=None,
    ):
        """
            :remarks	Adds a new environment to the list of environments. It does not save this environment to user_environments.
            :param		name			<str>	The name of the new environment
            :param		path			<str>	The base path to the environment
            :param		default			<bool>	This environment should be treated as default. There should only be one env with this set 
                                                to true. This is ignored in user_environments.xml
            :param		development		<bool>	
            :param		offline			<bool>	
            :param		environmentFile	<str>	The source file. Defaults to blurdev.tools.toolsenvironment.USER_ENVIRONMENT_FILE
            :param		legacyName		<str>	The name of the legacy environment defined in c:\blur\config.ini
            
            :return		<ToolsEnvironment>
        """
        output = ToolsEnvironment()

        if not environmentFile:
            environmentFile = USER_ENVIRONMENT_FILE

        output.setObjectName(name)
        output.setPath(path)
        output.setDefault(default)
        output.setDevelopment(development)
        output.setOffline(offline)
        output.setSourceFile(environmentFile)
        output.setCustom(True)
        if legacyName == None:
            legacyName = name
        output.setLegacyName(legacyName)

        ToolsEnvironment.environments.append(output)
        # update blurdev.ini
        # TODO: this will register the TEMPORARY_TOOLS_ENV env with legacy tools, but
        # not other new environments
        blurdev.ini.LoadConfigData()
        return output

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
    def findEnvironment(name, path=None):
        """ Looks up the environment by the inputed name or base path.
        
        Args:
            name (str): The name of the environment to find.
            path (str): If provided try to find a environment with this path. This is only used
                if the environment was not found by name. Defaults to None.
        
        Returns:
            blurdev.tools.ToolsEnvironment: The environment found. Use env.isEmpty() to check if it
                is a valid environment.
        """
        # Find the environmet by name.
        for env in ToolsEnvironment.environments:
            if unicode(env.objectName()) == unicode(name):
                return env
        # If the environment was not found by name, find it by path if one was provided.
        if path:
            for env in ToolsEnvironment.environments:
                if path and os.path.normpath(path) == os.path.normpath(env.path()):
                    return env
        return ToolsEnvironment()

    @staticmethod
    def findDevelopmentEnvironment():
        for env in ToolsEnvironment.environments:
            if env.isDevelopment():
                return env
        return ToolsEnvironment.activeEnvironment()

    @staticmethod
    def fromXml(xml):
        """
            \remarks	generates a new tools environment based on the inputed xml information
            \param		xml		<blurdev.XML.XMLElement>
            \return		<ToolsEnvironment>
        """
        output = ToolsEnvironment()

        name = xml.attribute('name')
        output.setObjectName(name)
        output.setPath(xml.attribute('loc'))
        output.setDefault(xml.attribute('default') == 'True')
        output.setDevelopment(xml.attribute('development') == 'True')
        output.setOffline(xml.attribute('offline') == 'True')
        output.setEmailOnError(xml.attribute('emailOnError').split(';'))
        output.setCustom(xml.attribute('custom') == 'True')
        output.setLegacyName(xml.attribute('legacyName', name))
        output.setTimeout(xml.attribute('timeout', ''))
        output.setAutoUpdate(xml.attribute('autoupdate') == 'True')
        output.setKeychain(xml.attribute('keychain', ''))
        output.setProject(xml.attribute('project', ''))
        return output

    @staticmethod
    def normalizePath(path):
        """
            \remarks	returns a normalized path for this environment to use when registering paths to the sys path
            \warning	deprecated method - use blurdev.settings.normalizePath
            \param		path		<str> || <QString>
            \return		<str>
        """
        return blurdev.settings.normalizePath(path)

    @staticmethod
    def loadConfig(filename, included=False):
        """
            \remarks	loads the environments from the inputed config file
            \param		filename		<str>
            \param		included		<bool> 	marks whether or not this is an included file
            \return		<bool> success
        """
        doc = blurdev.XML.XMLDocument()
        # Expand any environment variables and user directory shortcuts.
        # For example you can use '~\$TEST_ENV_VAR' which could expand to 'C:\Users\username\test'
        filename = os.path.expandvars(os.path.expanduser(filename))
        if doc.load(filename):
            root = doc.root()

            for child in root.children():
                # include another config file
                if child.nodeName == 'include':
                    ToolsEnvironment.loadConfig(child.attribute('loc'), True)

                # load an environment
                elif child.nodeName == 'environment':
                    env = ToolsEnvironment.fromXml(child)
                    env.setSourceFile(filename)
                    ToolsEnvironment.environments.append(env)

            # initialize the default environment
            if not included:
                pref = blurdev.prefs.find(
                    'blurdev/core', coreName=blurdev.core.objectName()
                )

                envName = pref.restoreProperty('environment')
                if envName:
                    env = ToolsEnvironment.findEnvironment(envName)
                    if not env.isEmpty():
                        # restore the environment from settings instead of the default if possible.
                        env.setActive(silent=True)
                        return True

                # If the environment variable BLURDEV_PATH is defined create a custom environment instead of using the loaded environment
                environPath = os.environ.get('BLURDEV_PATH')
                found = False
                if environPath:
                    env = ToolsEnvironment.findEnvironment(
                        blurdev.tools.TEMPORARY_TOOLS_ENV
                    )
                    if env.isEmpty():
                        found = True
                if not found:
                    ToolsEnvironment.defaultEnvironment().setActive(silent=True)
            return True

        return False

    @staticmethod
    def recordConfig(filename=''):
        if not filename:
            filename = USER_ENVIRONMENT_FILE

        if not filename:
            return False

        doc = blurdev.XML.XMLDocument()
        root = doc.addNode('tools_environments')
        root.setAttribute('version', 1.0)

        filename = os.path.normcase(filename)
        for env in ToolsEnvironment.environments:
            if os.path.normcase(env.sourceFile()) == filename:
                env.recordXml(root)

        return doc.save(filename)

    @staticmethod
    def registerPath(path):
        """
            \remarks	registers the inputed path to the system
            \warning	deprecated method - use blurdev.settings.registerPath
            \param		path		<str>
            \return		<bool> success
        """
        blurdev.settings.registerPath(path)

    def registerPaths(self):
        self.registerPath(self.path())
        # make tools importable
        self.registerPath(
            os.path.join(blurdev.activeEnvironment().path(), 'code', 'python', 'tools')
        )
        self.registerPath(
            os.path.join(
                blurdev.activeEnvironment().path(), 'maxscript', 'treegrunt', 'lib'
            )
        )
        # make environment libs importable
        self.registerPath(
            os.path.join(blurdev.activeEnvironment().path(), 'code', 'python', 'lib')
        )
        # If this environment has a project make sure we load the project settings
        self.activateProject()
        # Some environment settings need to wait for the initial phase to be processed before proceeding
        ToolsEnvironment.initialized = True

    @staticmethod
    def registerScriptPath(filename):
        # push the local path to the front of the list
        path = os.path.split(filename)[0]

        # if it is a package, then register the parent path, otherwise register the folder itself
        if os.path.exists(path + '/__init__.py'):
            path = os.path.abspath(path + '/..')

        # if the path does not exist, then register it
        ToolsEnvironment.registerPath(path)
