from __future__ import absolute_import
from __future__ import print_function
import glob
import json
import os
import sys
import re
import datetime
import logging
import importlib

from Qt.QtCore import QDateTime, QObject
from collections import OrderedDict

import blurdev
import blurdev.tools.toolsindex

try:
    from blur.Projects import customize
except ImportError:
    # If blur.Projects is not importable, rather than except, create a dummy decorator
    # to replace it.
    def customize(func):
        return func


# This logger is used to debug reloading treegrunt environments
logger = logging.getLogger(__name__)

USER_ENVIRONMENT_FILE = 'c:/blur/common/user_environments.json'


class ToolsEnvironment(QObject):
    """Defines the ToolsEnvironment class for the tools package"""

    # static members
    environments = []
    # Should disabled tools be shown
    showDisabledTools = False
    # Enabled the first time an environment is evaluated
    initialized = False
    # In special init cases(switching blurdev.core.objectName() from blurdev to
    # external) we need to make sure deactivateProject is called, but not reset sys.path
    # and sys.modules. The specific conditions are:
    #   1. app_blurdev's environment is set to env1. 2. app_external's environment is
    #      set to env2. env2's path is the same as env1.
    # Because of the way external tools are launched, they import the class from the
    # module, then call blurdev.launch. blurdev.launch calls
    # blurdev.core.setObjectName(), which in this case causes the module to be unloaded
    # and become None (see clearPathSymbols). This causes super calls to fail because
    # you can't pass in None for the type argument.
    # This often results in a traceback ending something like this:
    #    super(RequestPimpDialog, self).__init__(parent)
    # TypeError: must be type, not None
    _resetIfSamePath = True

    def __init__(self, config=None):
        super(ToolsEnvironment, self).__init__()
        if config is None:
            config = {}

        if 'name' in config:
            self.setObjectName(config['name'])
        self._path = config.get('path', '')
        # Defaults to os.getenv('BDEV_DEFAULT_CONFIG_INI')
        self._configIni = None
        self._development = config.get('dev', False)
        self._default = config.get('default', False)
        self._active = False
        self._offline = config.get('offline', False)
        self._custom = False
        self._temporary = False
        self._index = None
        self._emailOnError = config.get('email', [])
        self._legacyName = config.get('legacy', '')
        self._timeout = config.get('timeout', '')
        self._autoupdate = config.get('autoupdate', False)
        self._keychain = config.get('keychain', '')
        self._project = config.get('project', '')
        self._description = config.get('description', '')
        # Set blurdev.activeEnvironment().stopwatchEnabled to True to enable the
        # environment tool stopwatch this will start a stopwatch every time
        # blurdev.core.runScript is called and stop it once that script has
        # finished(this should include showEvent). This will allow you to time how long
        # it takes to launch a tool. You can add laps by calling
        # blurdev.activeEnvironment().stopwatch.newLap('info text')
        self.stopwatchEnabled = False
        self.stopwatch = blurdev.debug.Stopwatch('Default tool')

    def __str__(self):
        return '<ToolsEnvironment ({})>'.format(self.objectName())

    def _environmentToolPaths(self):
        """Returns the blurdev treegrunt environment path info

        See `registerPaths` for more info.

        Returns:
            sys_paths: A list of paths that need added to sys.path to add imports.
            tool_paths: A list of paths treegrunt should scan for tools. You can pass
                directory paths or a specific __meta__.xml file if your package only
                has one tool.
        """

        sys_paths = [
            # Add the virtualenv root(If this is the new environment setup based on pip)
            self.path(),
            # TODO: Remove path support for the svn tools repo once this release of
            # blurdev is installed on everyone's computers.
            # Make environment libs importable.
            os.path.join(self.path(), 'code', 'python', 'lib'),
            # This is the path for packages we deploy directly to the network
            # using Linux virtualenv.
            os.path.join(
                self.path(),
                'code',
                'python',
                'venv',
                'lib',
                'python2.7',
                'site-packages',
            ),
            # This is the path for packages we deploy directly to the network
            # using Windows virtualenv.
            os.path.join(self.path(), 'code', 'python', 'venv', 'Lib', 'site-packages'),
        ]

        return sys_paths, []

    def _get_project(self):
        """Used by blur.Projects.customize to identify the environment project if set"""
        return self.project()

    def clearPathSymbols(self, onlyDeactivate=False):
        """Removes the path symbols from the environment.

        Args:
            onlyDeactivate (bool): If True, call deactivateProject and return without
                modifying sys.path and sys.modules. You should not normally need to set
                this to True.

        Returns:
            bool: Was sys.modules and sys.path cleared.
        """
        if self.isEmpty():
            return False

        # If this environment has a project make sure we unload the project settings
        # if necessary before we clear the path symbols.
        self.deactivateProject()

        if onlyDeactivate:
            return False

        path = self.normalizePath(self.path())
        # do not remove python path variables
        pythonpath = [
            split.lower() for split in os.environ.get('PYTHONPATH', '').split(';')
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
                except Exception:
                    pass

        newpaths = []
        removepaths = set()
        pthFiles = []
        skippedFiles = []
        # remove all paths added by treegrunt or its .egg-link files from sys.path
        for spath in sys.path:
            npath = self.normalizePath(spath)
            if path in npath:
                # If this path is inside the treegrunt folder structure, add any
                # egg-link paths so we can remove them from python
                removepaths.add(spath)
                paths, skipped, pths = blurdev.settings.pthPaths(spath)
                removepaths.update(paths)
                skippedFiles.extend(skipped)
                pthFiles.extend(pths)
                # removepaths.update(self.getEggLinkPaths(spath))
            elif npath != '.' or npath in pythonpath:
                # Preserve any paths not in inside the treegrunt folder structure
                newpaths.append(spath)

        # Remove paths defined in pth files from sys.path
        removepaths_tuple = tuple(removepaths)
        newpaths = [
            np
            for np in newpaths
            if not self.normalizePath(np).startswith(removepaths_tuple)
        ]

        # Debug info about paths being removed from sys.path
        logger.debug('.pth files processed'.center(50, '-'))
        for f in pthFiles:
            if f in skippedFiles:
                logger.debug('Unable to read: {}'.format(f))
            else:
                logger.debug(f)
        logger.info('Paths to be removed'.center(50, '-'))
        for p in removepaths:
            logger.info(p)
        logger.info('-' * 50)

        # remove the required paths from sys.path
        sys.path = newpaths

        # Remove the modules from sys.modules so they are forced to be re-imported
        # Cast to list so we can remove items from sys.modules in python 3
        for key, value in list(sys.modules.items()):
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
                    spath = self.normalizePath(value.__file__)
                    should_remove = [
                        x for x in removepaths if self.normalizePath(x) in spath
                    ]
                except Exception:
                    logger.debug('    no __file__: {}'.format(key))
                else:
                    if should_remove:
                        logger.debug(
                            'module removed: {} "{}"'.format(key, value.__file__)
                        )
                        sys.modules.pop(key)

        try:
            # Clear the cached imports in blur.Projects if supported
            import blur.Projects

            blur.Projects.clearImportCache()
        except (ImportError, AttributeError):
            pass

        return True

    @customize
    def activateProject(self):
        pass

    @customize
    def deactivateProject(self):
        pass

    @customize
    def constructProjectForApplication(self, app):
        return None

    @customize
    def destructProjectForApplication(self, app):
        return None

    def configIni(self):
        if not self._configIni:
            # Attempt to load the environment specific config.ini file.
            filename = os.path.join(self.path(), 'code', 'config.ini')
            if os.path.exists(filename):
                self._configIni = os.path.normpath(filename)
            else:
                # if that doesn't exist, use the default config.ini
                self._configIni = os.path.normpath(
                    os.getenv('BDEV_DEFAULT_CONFIG_INI', '')
                )
        return self._configIni

    def emailOnError(self):
        return self._emailOnError

    def index(self):
        """returns the index of tools for this environment

        Returns:
            blurdev.tools.index.Index:
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
            print('TIMEOUT', self._timeout)
            for arg in self._timeout.split(':'):
                m = re.match(r'(?P<num>\d+)(?P<type>[dmhsw])', arg, re.I)
                print(arg, m)
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
            print('TIMEOUT', self._timeout)
            for arg in self._timeout.split(':'):
                m = re.match(r'(?P<num>\d+)(?P<type>[dmhsw])', arg, re.I)
                print(arg, m)
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
        """Returns the relative path from the inputted path to this environment

        Returns:
            str:
        """
        if not self.isEmpty():
            # posixpath.normpath does not convert windows slashes to prevent problems
            # with escaping. Our tool paths do not have spaces and should not need
            # escaping
            path = str(path).replace('\\', '/')
            return os.path.abspath(os.path.join(str(self.path()), path))
        return ''

    def resetPaths(self):
        blurdev.core.aboutToClearPaths.emit()
        self.clearPathSymbols()
        self.registerPaths()
        blurdev.core.emitEnvironmentActivated()

    def setActive(self, silent=False, force=False):
        """Sets this environment as the active environment.

        It also switches the currently running modules from the system by removing the
        old environment path from sys.path and sys.modules. It then adds the paths for
        this environment to sys.path.

        Args:

            silent (bool): If True, do not emit the blurdev.core.environmentActivated
                signal. Defaults to False.

            force (bool): IF True, force this environment to reload, even if its is
                currently active. Defaults to False.

        Returns:
            bool: The environment was set active.
        """
        if force or not (self.isActive() or self.isEmpty()):
            # clear out the old environment
            old = self.activeEnvironment()
            # Respect _resetIfSamePath when clearing path symbols
            samePath = self.normalizePath(self.path()) == self.normalizePath(old.path())
            onlyDeactivate = not ToolsEnvironment._resetIfSamePath and samePath
            old.clearPathSymbols(onlyDeactivate=onlyDeactivate)
            old._active = False

            # register this environment as active and update the path symbols
            self._active = True
            self.registerPaths()

            # set the legacy environment active
            blurdev.ini.SetActiveEnvironment(self.legacyName())

            # emit the environment activation change signal
            if not silent:
                # core can be defined as None at this point in if this was called during
                # blurdev.core init.
                if blurdev.core:
                    blurdev.core.emitEnvironmentActivated()

            return True
        return False

    def setConfigIni(self, path):
        self._configIni = path

    def setCustom(self, state=True):
        self._custom = state

    def setDefault(self, state=True):
        self._default = state

    def setDescription(self, txt):
        self._description = txt

    def setDevelopment(self, state=True):
        self._development = state

    def setOffline(self, state=False):
        self._offline = state

    def setEmailOnError(self, emails):
        if not emails:
            self._emailOnError = []
        else:
            self._emailOnError = [
                entry for entry in emails if str(entry) != '' and entry is not None
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

    def setTemporary(self, state):
        self._temporary = state

    def stripRelativePath(self, path):
        """removes this environments path from the inputted path

        Returns:
            str:
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
        if not legacy:
            legacy = name

        # Update the config.ini file so next time we start from the correct environment.
        try:
            import legacy

            codeRootPath = os.path.abspath(
                os.path.join(os.path.dirname(legacy.__file__))
            )
            if os.path.exists(codeRootPath):
                blurdev.ini.SetINISetting(
                    blurdev.ini.configFile,
                    legacy,
                    'codeRoot',
                    codeRootPath,
                )
                blurdev.ini.SetINISetting(
                    blurdev.ini.configFile,
                    legacy,
                    'startupPath',
                    os.path.abspath(os.path.join(codeRootPath, 'lib')),
                )
                blurdev.ini.LoadConfigData()
        except ImportError as error:
            logging.warning(error)

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
            if not legacy:
                legacy = name
            # update the config.ini file so next time we start from the correct
            # environment.
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
        """Looks up the active environment for the system

        Return:
            ToolsEnvironment:
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
        """Adds a new environment to the list of environments. It does not save this
        environment to user_environments.

        Args:
            name (str): The name of the new environment
            path (str): The base path to the environment
            default (bool): This environment should be treated as default. There
                should only be one env with this set to true. This is ignored in
                user_environments.xml
            development (bool):
            offline (bool):
            environmentFile (str): The source file. Defaults to
                `blurdev.tools.toolsenvironment.USER_ENVIRONMENT_FILE`
            legacyName (str): The name of the legacy environment defined in
                `c:\\blur\\config.ini`

            Returns:
                ToolsEnvironment:
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
        if legacyName is None:
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
        """looks up the default environment for the system

        Returns:
            ToolsEnvironment:
        """
        for env in ToolsEnvironment.environments:
            if env.isDefault():
                return env
        return ToolsEnvironment()

    def description(self):
        """A description of this treegrunt environment"""
        return self._description

    @staticmethod
    def findEnvironment(name, path=None, default=None):
        """Looks up the environment by the inputted name or base path.

        Args:

            name (str): The name of the environment to find.

            path (str): If provided try to find a environment with this path. This is
            only used if the environment was not found by name. Defaults to None.
            default (bool, ToolsEnvironmet, optional): If the environment is not found
                and True is passed it will return the default environment. If None an
                empty ToolsEnvironment is returned, otherwise the value is returned.

        Returns:
            blurdev.tools.ToolsEnvironment: The environment found. Use env.isEmpty() to
            check if it is a valid environment.
        """
        # Find the environment by name.
        for env in ToolsEnvironment.environments:
            if env.objectName() == name:
                return env
        # If the environment was not found by name, find it by path if one was provided.
        if path:
            for env in ToolsEnvironment.environments:
                if path and os.path.normpath(path) == os.path.normpath(env.path()):
                    return env
        if default is True:
            return ToolsEnvironment.defaultEnvironment()
        elif default:
            return default
        return ToolsEnvironment()

    @staticmethod
    def findDevelopmentEnvironment():
        for env in ToolsEnvironment.environments:
            if env.isDevelopment():
                return env
        return ToolsEnvironment.activeEnvironment()

    @staticmethod
    def fromXml(xml):
        """Generates a new tools environment based on the inputted xml information

        Args:
            xml (blurdev.XML.XMLElement):

        Returns:
            ToolsEnvironment:
        """
        output = ToolsEnvironment()

        name = xml.attribute('name')
        output.setObjectName(name)
        output.setPath(xml.attribute('loc'))
        output.setDefault(xml.attribute('default') == 'True')
        output.setDevelopment(xml.attribute('development') == 'True')
        output.setOffline(xml.attribute('offline') == 'True')
        output.setEmailOnError(xml.attribute('emailOnError').split(';'))
        output.setDescription(xml.attribute('description', ''))
        output.setCustom(xml.attribute('custom') == 'True')
        output.setLegacyName(xml.attribute('legacyName', name))
        output.setTimeout(xml.attribute('timeout', ''))
        output.setAutoUpdate(xml.attribute('autoupdate') == 'True')
        output.setKeychain(xml.attribute('keychain', ''))
        output.setProject(xml.attribute('project', ''))
        return output

    @staticmethod
    def normalizePath(path):
        """Returns a normalized path for this environment to use when registering paths
        to the sys path

        Warning:
            deprecated method - use blurdev.settings.normalizePath

        Args:
            path (str):

        Returns:
            str:
        """
        return blurdev.settings.normalizePath(path)

    @classmethod
    def load_config_file(
        cls, filename, config=None, include_name=None, relative_root=None
    ):
        """Reads the config data from one or more files on disk. This is recursively
        called for any included file paths.

        Args:
            filename (str): The filename to load the data from. Follows include any
                include links in this file. Supports only .json and .xml files.
            include_name (str, optional): Used as the name of this include file if
                provided, otherwise the name specified in the file is used.

        Returns:
            dict: A dictionary of all the environment info including the included files.
                It is structured reflecting the included files so we can use this
                dictionary to edit any one of those files.
        """
        if config is None:
            config = OrderedDict()
        current = OrderedDict()

        # Normalize and fully expand the filename.
        # Expand any environment variables and user directory shortcuts. For example
        # you can use '~\$TEST_ENV_VAR' which could expand to
        # 'C:\Users\username\test'
        filename = os.path.expandvars(os.path.expanduser(filename))
        # If a relative path was passed, turn it into a absolute path
        if relative_root:
            filename = os.path.join(relative_root, filename)
        filename = os.path.normpath(filename)
        dir_name = os.path.dirname(filename)

        # TODO: Remove this transition code in a few months when we are no longer using
        # xml files for local configs.
        # To facilitate the transition from xml to json, we change the filename used to
        # save changes to the treegrunt environment to json. This will result in us
        # reading the xml file and changing it to a json file when saving.
        base, ext = os.path.splitext(filename)
        if ext.lower() == '.xml':
            json_name = '{}.json'.format(base)
            if os.path.exists(json_name) or not os.path.exists(filename):
                filename = json_name

        if filename in config:
            # Don't reprocess the same file if there is are circular includes
            return config

        # Add current now to prevent include cycles. This stores a pointer so the
        # future updates to current in the rest of the function will be included.
        base, _ = os.path.splitext(filename)
        config['{}.json'.format(base)] = current

        if os.path.splitext(filename.lower())[-1] == '.json':
            if os.path.isfile(filename):
                with open(filename) as fh:
                    data = json.load(fh, object_pairs_hook=OrderedDict)
            else:
                # If the file doesn't exist, add an empty node so the UI can show it
                # allowing the user to add environments to it/creating the file.
                data = {}
            name = include_name if include_name else 'Environment'
            current['name'] = data.get('name', name)
            current['read_only'] = data.get('read_only', False)

            for include in data.get('included', []):
                current.setdefault('included', []).append(include)
                name = include.get('name')
                fn = include.get('filename', '')
                cls.load_config_file(
                    fn, config=config, include_name=name, relative_root=dir_name
                )

            if 'environments' in data:
                current.setdefault('environments', []).extend(data['environments'])

        # TODO: Remove this xml processing code once we are no longer using xml
        elif os.path.splitext(filename.lower())[-1] == '.xml':
            # If the json file was not found, look for and parse the xml file instead
            doc = blurdev.XML.XMLDocument()
            if doc.load(filename):
                root = doc.root()
                # TODO: perhaps use include_name as the default name not explicit name
                if include_name is None:
                    current['name'] = root.attribute('name')
                else:
                    current['name'] = include_name

                for child in root.children():
                    # include another config file
                    if child.nodeName == 'include':
                        name = child.attribute('name')
                        fn = child.attribute('loc')
                        child_dict = OrderedDict((('name', name), ('filename', fn)))
                        current.setdefault('included', []).append(child_dict)
                        cls.load_config_file(
                            fn,
                            config=config,
                            include_name=name,
                            relative_root=dir_name,
                        )

                    # load an environment
                    elif child.nodeName == 'environment':
                        env = OrderedDict()
                        env['name'] = child.attribute('name')
                        env['path'] = child.attribute('loc')
                        env['email'] = child.attribute('emailOnError')
                        env['description'] = child.attribute('description')
                        env['legacy'] = child.attribute('legacyName')
                        env['dev'] = (
                            child.attribute('development', 'false').lower() == 'true'
                        )
                        env['default'] = (
                            child.attribute('default', 'false').lower() == 'true'
                        )
                        env['offline'] = (
                            child.attribute('offline', 'false').lower() == 'true'
                        )
                        env['autoupdate'] = (
                            child.attribute('autoupdate', 'false').lower() == 'true'
                        )
                        env['timeout'] = child.attribute('timeout', '')
                        env['keychain'] = child.attribute('keychain', '')
                        env['project'] = child.attribute('project', '')

                        current.setdefault('environments', []).append(env)
        return config

    @classmethod
    def create_env(
        cls,
        name,
        path,
        email='',
        description='',
        dev=False,
        default=False,
        offline=False,
        autoupdate=False,
        timeout='',
        keychain='',
        project='',
        legacy='',
    ):
        """Generate a environment dictionary with the given values that can be stored
        in the "environments" section of the treegrunt config.
        """
        ret = OrderedDict()
        ret['name'] = name
        ret['path'] = path
        ret['email'] = email
        ret['description'] = description
        ret['dev'] = dev
        ret['default'] = default
        ret['offline'] = offline
        ret['autoupdate'] = autoupdate
        ret['timeout'] = timeout
        ret['keychain'] = keychain
        ret['project'] = project
        ret['legacy'] = legacy
        return ret

    @classmethod
    def save_config(cls, config, postfix=''):
        """Save the config and any filenames it includes.

        Args:
            config (dict): The config dictionary to save.
            postfix (str, optional): The config specifies the location it is saved.
                This allows you to save a copy of it next to the original file.
        """
        for filename in config:

            current = config[filename]
            if postfix:
                filename, ext = os.path.splitext(filename)
                # TODO: Remove the hardcoded ext once we have migrated to json configs.
                ext = '.json'
                filename = ''.join((filename, postfix, ext))

            dir_name = os.path.dirname(filename)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)

            with open(filename, 'w') as fp:
                json.dump(current, fp, indent=4)

    @classmethod
    def loadConfig(cls, filename):
        """Loads the environments from the inputted config file

        Args:
            filename (str): The file to load from.

        Returns:
            bool: success
        """
        # Expand any environment variables and user directory shortcuts. For example you
        # can use '~\$TEST_ENV_VAR' which could expand to 'C:\Users\username\test'
        filename = os.path.expandvars(os.path.expanduser(filename))
        if not os.path.exists(filename):
            return False

        config = cls.load_config_file(filename)
        default = None
        # Iterate over the environments and create them
        for environments in config.values():
            for env_config in environments.get('environments', {}):
                env = ToolsEnvironment(config=env_config)
                if env.isDefault():
                    if default is None:
                        default = env
                    else:
                        env.setDefault(False)
                        msg = '{} is marked default but {} is already marked default'
                        logger.warning(msg.format(env.objectName(), default.name()))
                ToolsEnvironment.environments.append(env)

        return True

    @classmethod
    def refreshEnvironmentConfigs(cls):
        """Reset the treegrunt environments to match the configs on disk."""
        active = ToolsEnvironment.activeEnvironment()
        activeName = active.objectName()
        # Ensure the current environment is unloaded.
        blurdev.core.configUpdated()
        active.clearPathSymbols()

        # Reset the treegunt environments to match the configs on disk
        ToolsEnvironment.environments = []
        ToolsEnvironment.loadConfig(blurdev.core.defaultEnvironmentPath())

        # Update any EnvComboBox or any other widgets showing treegrunt environments
        blurdev.core.environmentsUpdated.emit()

        # Reload the active environment to restore the paths we removed earlier and
        # to ensure they are updated with the latest config.
        blurdev.setActiveEnvironment(activeName)

    @staticmethod
    def registerPath(path):
        """Registers the inputted path to the system

        Warning:
            deprecated method - use blurdev.settings.registerPath

        Args:
            path (str):

        Returns:
            bool: success
        """
        blurdev.settings.registerPath(path)

    def readEggLink(self, egg_link_file):
        with open(egg_link_file, 'r') as file:
            return file.readline().strip()

    def getEggLinkList(self, path):
        eggLinkList = []
        if os.path.isdir(path):
            eggLinkList = glob.glob(os.path.join(path, '*.egg-link'))
        return eggLinkList

    def getEggLinkPaths(self, path):
        links = self.getEggLinkList(path)
        paths = []
        for link in links:
            logger.info('egg-link: {}'.format(link))
            logger.info('\t{}'.format(self.readEggLink(link)))
            paths.append(self.readEggLink(link))
        return paths

    def registerPaths(self):
        """Update sys.path with all required tool paths.

        Uses the paths defined by installed blurdev.tools.paths entry points.
        The entry points are cached from the last time `self.index().rebuild()`
        was called to speed up the import of blurdev and switching environments.
        The functions called by the entry point is called by this function.

        If a entry point raises a Exception the exception is printed but
        not raised and no path manipulation will happen for that entry point.
        """

        # Update sys.path with the treegrunt environment paths
        index = self.index()
        all_tool_paths = []
        for tools_package in index.packages():
            for path in tools_package.sys_paths():
                logger.debug('  sys.path.insert: {}'.format(path))
                self.registerPath(path)

            # Get the tool_paths and conform them for use in the index
            for tool_path in tools_package.tool_paths():
                # If legacy wasn't passed we can assume its not a legacy file structure
                if isinstance(tool_path, str):
                    tool_path = [tool_path, False]
                all_tool_paths.append(tool_path)
                logger.debug('  tool root path: {}'.format(tool_path))
            index.setToolRootPaths(all_tool_paths)

        # If this environment has a project make sure we load the project settings
        self.activateProject()
        # Some environment settings need to wait for the initial phase to be processed
        # before proceeding
        ToolsEnvironment.initialized = True

    @classmethod
    def packagePath(cls, package, raiseImportError=False):
        try:
            package = importlib.import_module(package)
            return os.path.dirname(package.__file__)
        except ImportError as error:
            if raiseImportError:
                raise error
            return ''

    @staticmethod
    def registerScriptPath(filename):
        # push the local path to the front of the list
        path = os.path.split(filename)[0]

        # if it is a package, then register the parent path, otherwise register the
        # folder itself
        if os.path.exists(path + '/__init__.py'):
            path = os.path.abspath(path + '/..')

        # if the path does not exist, then register it
        ToolsEnvironment.registerPath(path)
