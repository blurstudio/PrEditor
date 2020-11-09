"""
Functions to read through and initialize the paths for Blur Studios.
Also has functions for accessing & setting INI information.


"""

from __future__ import print_function
from future.utils import iteritems
from past.builtins import basestring
from builtins import str as text
from imp import reload

_configParserKwargs = dict()
try:
    import configparser

    # strict=False: Something in our current workflow is writing duplicate options in
    # ini files. So for now when using the new configparser module we have to set its
    # strict value to False so it doesn't error out when reading those files.
    # interpolation=None: By default configparser expands %(key)s values with
    # environment variables. It raises exceptions if it finds % that don't match that.
    # This causes problems with render elements so we disable it.
    _configParserKwargs = dict(strict=False, interpolation=None)
except Exception:
    import ConfigParser as configparser  # noqa: N813

import sys
import os
from contextlib import contextmanager
import copy


configFile = os.getenv(
    'BDEV_DEFAULT_CONFIG_INI', ''
)  # Default path information for Blur Studio
environments = {}
activeEnvironment = 'production'
blurConfigFile = None
fallbackEncoding = 'utf-16'


def GetINISetting(inFileName, inSection="", inKey="", lowercaseOptions=True):
    """ Gets the value of the inputted key found in the given section of an INI file, if
    it exists and the key is specified.  If the key is not specified, but the
    section exists, then the function will return a list of all the keys in that
    section.

    Args:
        inFileName: The ini file to read from.
        inSection: The section to read from.
        inKey: The key(option) to read from.
        lowercaseOptions (bool, optional): If True, then all keys(options) will be
            treated as lowercase. This is how python's configparser handles ini
            files. You may want to set this to False if editing 3ds max ini files.

    Returns:
        string: A string or list of strings.
    """
    if os.path.isfile(inFileName):
        tParser = ToolParserClass(lowercaseOptions=lowercaseOptions)
        tParser.read(inFileName)
        inSection = text(inSection)
        inKey = text(inKey)
        if inSection:
            if tParser.has_section(inSection):
                if inKey:
                    if tParser.has_option(inSection, inKey):
                        return tParser.get(inSection, inKey)
                else:
                    tItemList = tParser.items(inSection)
                    return [tItem[0] for tItem in tItemList]
        else:
            return tParser.sections()
    return ""


def SetINISetting(
    inFileName,
    inSection,
    inKey,
    inValue,
    useConfigParser=False,
    writeDefault=True,
    lowercaseOptions=True,
):
    """ Sets the ini section setting of the provided file with the give key/value pair.

    By default it uses blurdev.ini.ToolParserClass, but if you set useConfigParser to
    True It will use ConfigParser.ConfigParser instead. You will not be able to write to
    the DEFAULT Section when using ConfigParser.ConfigParser. If writeDefault is False
    it can still use the ToolParserClass, but it will not write the DEFAULT section.

    Updating the DEFAULT section will affect any future ini files you write. To prevent
    this you may want to use the blurdev.ini.temporaryDefaults context.

    Args:
        inFileName (str): Ini filename to write to
        inSection (str): Name of the section the value is stored
        inKey (str): Name of the key(option) to store the value
        inValue: The value to store
        useConfigParser (bool, optional): Use the ToolParserClass or configparser class
        writeDefault (bool, optional): If using ToolParserClass, should it write the
            DEFAULT section
        lowercaseOptions (bool, optional): If True, then all keys(options) will be
                treated as lowercase. This is how python's configparser handles ini
                files. You may want to set this to False if editing 3ds max ini files.

    Returns:
        bool: IF it was able to save the ini setting to file.
    """
    if useConfigParser:
        tParser = configparser.ConfigParser(**_configParserKwargs)
    else:
        tParser = ToolParserClass(
            writeDefault=writeDefault, lowercaseOptions=lowercaseOptions
        )
    inSection = text(inSection)
    inKey = text(inKey)
    inValue = text(inValue)

    if os.path.isfile(inFileName):
        tParser.read(inFileName)
    if not useConfigParser and inSection.lower() == 'default':
        # special case to support updating the Default section
        environments['default'].__dict__['_properties'][inKey] = inValue
    else:
        if inSection.lower() != 'default' and not tParser.has_section(inSection):
            tParser.add_section(inSection)

        tParser.set(inSection, inKey, inValue)
    if useConfigParser:
        f = open(inFileName, 'w')
        tParser.write(f)
        f.close()
        return True
    return tParser.Save(inFileName)


def DelINISetting(inFileName, inSection, inKey=""):
    """ Delets the given section & key ( if specified ) from the inputed file, if the
    file exists.

        :returns: bool
    """
    if os.path.isfile(inFileName):
        tParser = ToolParserClass()
        tParser.read(inFileName)
        inSection = text(inSection)
        inKey = text(inKey)

        if tParser.has_section(inSection):
            if inKey:
                tParser.remove_option(inSection, inKey)
            else:
                tParser.remove_section(inSection)
            return tParser.Save(inFileName)
    return False


def EndINIFn():
    return None


class switch(object):  # noqa: N801
    """ Provides a switch call that mimics that of C/C++.

        :returns: bool
    """

    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        yield self.match
        raise StopIteration

    def match(self, *args):
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


class SectionClass(object):
    """ Represents an INI file's section, providing quick and easy access to its properties
    """

    def __getattr__(self, attrKey):
        """ Overloaded the get attribute for this class to run the GetProperty function
            for the given attribute
        """
        if not attrKey.startswith('_'):
            return self.GetProperty(attrKey)
        raise AttributeError(attrKey)

    def __setattr__(self, attrKey, attrValue):
        """ Overloaded the set attribute for this class to run the SetProperty function
            for the given attribute
        """
        if not attrKey.startswith('_'):
            self.SetProperty(attrKey, attrValue)
        else:
            raise AttributeError(attrKey)

    def __init__(self, sectionName):
        """ Class initialization.  Set the sectionName for the class instance to the
            given variable *required*
        """
        super(SectionClass, self).__init__()
        self.__dict__['_sectionName'] = sectionName
        self.__dict__['_properties'] = {}

    def GetName(self):
        """ Returns the section name for this instance
        """
        return self._sectionName

    def GetProperty(self, propName):
        """ Gets the property whose dictionary key matches the inputed name from the instance's
            _properties dictionary, or returns a blank string if not found.

        """
        propName = propName.lower()
        if propName in self._properties:
            return self._properties[propName]
        return ''

    def GetPropNames(self):
        """ Returns the _properties dictionary keys
        """
        return self._properties.keys()

    def GetPropValues(self):
        return self._properties.values()

    def Load(self, parser):
        """ Loads the data from the inputed parser if it has a section whose name
        matches this instance's name.
        """
        if parser.has_section(self._sectionName):
            self.__dict__['_properties'] = {}

            for tKey, tValue in parser.items(self._sectionName):
                self._properties[tKey] = tValue

            return True
        return False

    def Save(self, parser):
        """ Saves the data for this instance to the inputed parser
        """
        if not parser.has_section(self._sectionName):
            parser.add_section(self._sectionName)

        for tKey, tValue in iteritems(self._properties):
            # only save the value if its diffrent or not pressent in the default section
            if self.GetProperty(tKey) != tValue:
                parser.set(self._sectionName, tKey, tValue)
        return True

    def SetName(self, sectionName):
        """ Sets the instances name to the inputed string
        """
        self._sectionName = sectionName

    def SetProperty(self, propName, propValue):
        """ Sets the property and value for the INI part based on the inputed values.
        ** The inputed propName is converted to lowercase **
        """
        propName = propName.lower()
        self._properties[propName] = propValue
        return True


class ToolParserClass(configparser.ConfigParser):
    """ Provides an easy way to create and manage tool related config files.
    """

    def __getattr__(self, attrKey):
        """
            :remarks    Overloaded the __getattr__ function to use the GetSection
                        function for this class type

            :param		attrKey		<string>

            :return		<SectionClass> || AttributeError
        """
        if not attrKey.startswith('_'):
            return self.GetSection(attrKey)
        raise AttributeError(attrKey)

    def __init__(
        self, toolID='', location='', writeDefault=True, lowercaseOptions=True
    ):
        configparser.ConfigParser.__init__(self, **_configParserKwargs)
        self._toolID = toolID
        self._location = location
        self._sectionClasses = []
        self._writeDefault = writeDefault
        self.lowercaseOptions = lowercaseOptions
        if toolID:
            self.Load()

    def GetFileName(self):
        """
        Builds the file name for this class instance using its location and toolID.
        Locations:
                3dsMax:	Uses 'maxPlugPath'  pathID with the GetPath function
                XSI:	Uses 'xsiPlugPath'  pathID with the GetPath function
                Other:	Uses 'userPlugPath' pathID with the GetPath function

        The fileName is built as:
            GetPath( pathID ) + toolID + '.ini'

        If there is no toolID specified for this instance, then this function returns a
        blank string.

        """
        outFileName = ''

        if self._toolID:
            if self._location.lower() == '3dsmax':
                outFileName += GetPath('maxPlugPath')
            elif self._location.lower() == 'xsi':
                outFileName += GetPath('xsiPlugPath')
            else:
                outFileName += GetPath('userPlugPath')

            outFileName += self._toolID + '.ini'

        return outFileName

    def GetSection(self, sectionName):
        """ Returns the section whose name matches the inputed string, adding a new
        SectionClass to this instance's list if none is found.
        """
        for tSection in self._sectionClasses:
            if tSection.GetName().lower() == sectionName.lower():
                return tSection

        outSection = SectionClass(sectionName=sectionName)
        self._sectionClasses.append(outSection)
        return outSection

    def GetSectionNames(self):
        """ Get a list of all the section names for this class instance
        """
        return [tSection.GetName() for tSection in self._sectionClasses]

    def GetSections(self):
        """ Returns the sction class children of this ToolParser instance
        """
        return self._sectionClasses

    def Load(self, fileName=''):
        """ Load up a config file and builds its class information based on its
            sections/keys/values. If the fileName is specified, then the parser uses the
            inputed file name to open, otherwise it will use the GetFileName function to
            build its own name.
        """
        if not fileName:
            fileName = self.GetFileName()

        if fileName and os.path.exists(fileName):
            try:
                self.read(fileName)
            except (
                configparser.MissingSectionHeaderError,
                configparser.ParsingError,
                UnicodeError,
            ):
                if fileName == configFile:
                    # If the file is corrupted load the backup
                    if RestoreConfig(
                        fileName, '"{fileName}" is corrupted. Restoring from backup.'
                    ):
                        try:
                            self.read(fileName)
                        except (
                            configparser.MissingSectionHeaderError,
                            configparser.ParsingError,
                            UnicodeError,
                        ):
                            # The backup is corrupted there is nothing else we can do
                            # automatically.
                            msg = (
                                'The backup config file for "{fileName}" is corrupted. '
                                'Unable to load blurdev config.'
                            )
                            print(msg.format(fileName=fileName))
                            return False
            self._sectionClasses = []
            for tSectionName in self.sections():
                tSection = SectionClass(sectionName=tSectionName)
                tSection.Load(self)
                self._sectionClasses.append(tSection)

            return True
        return False

    def optionxform(self, option):
        """ Set lowercaseOptions to False if you want to preserve option case.
        """
        if self.lowercaseOptions:
            return super(ToolParserClass, self).optionxform(option)
        return option

    def read(self, filenames):
        try:
            read_ok = configparser.ConfigParser.read(self, filenames)
        except configparser.MissingSectionHeaderError:
            # Attempt to read the file using a specific encoding.
            read_ok = []
            if isinstance(filenames, basestring):
                filenames = [filenames]
            for filename in filenames:
                try:
                    import codecs

                    fp = codecs.open(filename, "r", fallbackEncoding)
                except IOError:
                    continue
                self._read(fp, filename)
                fp.close()
                read_ok.append(filename)
        return read_ok

    def Save(self, fileName=''):
        """
            :remarks    Save out a config file based on the class information, saving to
                        the specified fileName. If a blank string is passed in for the
                        fileName, then it sets the fileName value using the GetFileName
                        function.
            :param		fileName		<string>		OPTIONAL

            :return		<bool>
        """
        if not fileName:
            fileName = self.GetFileName()

        if fileName:
            for tSection in self._sectionClasses:
                tSection.Save(self)

            f = open(fileName, 'w')
            self.write(f)
            f.close()
            return True
        return False

    def write(self, fp):
        """
            :remarks	Saves the ini file in alphabetical order
            :param		fp	<file>	A python file object opened in write mode
        """
        sects = ()
        if self._writeDefault:
            sects = ('GLOBALS', 'default')
            for section in sects:
                if section in self._sections:
                    fp.write("[%s]\n" % section)
                    for (key, value) in sorted(self._sections[section].items()):
                        if key != "__name__":
                            fp.write(
                                "%s = %s\n" % (key, text(value).replace('\n', '\n\t'))
                            )
                    fp.write("\n")
                elif section in environments:
                    if section == 'default':
                        fp.write("[DEFAULT]\n")
                    else:
                        fp.write("[%s]\n" % section)
                    for (key, value) in sorted(
                        environments[section].__dict__['_properties'].items()
                    ):
                        if key != "__name__":
                            fp.write(
                                "%s = %s\n" % (key, text(value).replace('\n', '\n\t'))
                            )
                    fp.write("\n")
        for section in sorted(self._sections):
            if section not in sects:
                fp.write("[%s]\n" % section)
                for (key, value) in sorted(self._sections[section].items()):
                    if key != "__name__":
                        fp.write("%s = %s\n" % (key, text(value).replace('\n', '\n\t')))
                fp.write("\n")


def _normEnv(environmentID):
    """ Normalizes inputed environmentID.  Function is setup for backwards
        compatibility, setting code path 'local' and 'network' to work with new
        environments and turns the ID to lowercase
    """
    if environmentID.lower() == 'network':
        return 'Production'
    if environmentID.lower() == 'offline':
        return 'Offline'
    if environmentID.lower() == 'beta':
        return 'Beta'
    return environmentID


def addSysPath(path):
    if path:
        path = os.path.normpath(path.lower())
        if path not in sys.path:
            sys.path.append(path)
            return True
    return False


def AddResourcePath(inRelativePath):
    """ Adds a relative path to the sys.path list, combining the inputed path with the
        current GetCodePath results.
    """
    tPath = os.path.normpath(os.path.join(GetCodePath(), inRelativePath).lower())
    if tPath not in sys.path:
        sys.path.append(tPath)
        return True
    return False


def GetActiveEnvironment():
    """ Returns the active environment SectionClass
    """
    return environments[activeEnvironment]


def GetActiveEnvironmentID():
    """ Returns the id of the active environment
    """
    return GetActiveEnvironment().GetName()


def GetCodePath(inEnvironment=''):
    """ Returns the 'codeRoot' pathID value for the given environment.  If no
        environment is specified, then the current active environment is used.
    """
    return GetPath('codeRoot', inEnvironment=inEnvironment)


def GetEnvironment(environmentID):
    """ Returns the SectionClass instance whose ID matches the inputed envrionment ID
        from the global environments list (if a match is found)
    """
    if not environmentID:
        environmentID = activeEnvironment

    environmentID = _normEnv(environmentID)

    if environmentID in environments:
        return environments[environmentID]
    return None


def GetEnvironmentIDs(verifyPathIDsExist=[]):
    """Returns all available environment IDs from the global environments dictionary
    """
    outEnvironmentIDs = []
    for tEnvironment in environments.values():
        if tEnvironment.GetName() != 'DEFAULT':
            if not verifyPathIDsExist or IsEnvironmentValid(
                environmentID=tEnvironment.GetName(),
                verifyPathIDsExist=verifyPathIDsExist,
            ):
                outEnvironmentIDs.append(tEnvironment.GetName())
    outEnvironmentIDs.sort()
    return outEnvironmentIDs


def GetPath(
    inPathKey, inEnvironment='', inPathSeparator='/', inIncludeLastSeparator=True
):
    """ Gets the path associated with the inputed path key.  If an environment is passed
        in, then that environment section is used to find the path value, otherwise the
        active environment is used.  If the inputed path key does not exist in the given
        environment, then the value for the default environment is returned, and if no
        match exists for the default section, a blank string is outputed.
    """
    if not inEnvironment:
        inEnvironment = activeEnvironment

    inEnvironment = _normEnv(inEnvironment)
    outPath = ''

    if inEnvironment in environments:
        outPath = environments[inEnvironment].GetProperty(inPathKey)

    if not outPath:
        outPath = environments['default'].GetProperty(inPathKey)

    return NormPath(
        RemovePathTemplates(outPath, inEnvironment=inEnvironment),
        inPathSeparator=inPathSeparator,
        inIncludeLastSeparator=inIncludeLastSeparator,
    )


def GetPathIDs(inEnvironment=''):
    """ Collects all the available pathIDs for the inputed environment, using the active
        environment if no input is specified.  Combines the given environment and the
        default values (which are available for any environment)
    """
    if not inEnvironment:
        inEnvironment = activeEnvironment

    inEnvironment = _normEnv(inEnvironment)
    outPropNames = environments['default'].GetPropNames()

    if inEnvironment in environments:
        for tPropName in environments[inEnvironment].GetPropNames():
            if tPropName not in outPropNames:
                outPropNames.append(tPropName)

    return outPropNames


def GetPaths(inEnvironment='', inPathSeparator='/'):
    """ Collects all the available paths for the inputed environment, using the active
        environment if no input is specified.  Combines the given environment and the
        default values (which are available for any environment)
    """
    outPaths = []
    for tPathID in GetPathIDs(inEnvironment=inEnvironment):
        outPaths.append(GetPath(tPathID, inEnvironment=inEnvironment))

    return outPaths


def IsEnvironmentValid(environmentID='', verifyPathIDsExist=[]):
    """ Checks to see if the given environment exists by checking the paths associated
        with it, if the pathIDs array is blank, then all the paths are checked,
        otherwise only those specified are checked.
    """
    if not environmentID:
        environmentID = activeEnvironment

    environmentID = _normEnv(environmentID)

    if environmentID in environments:
        for pathID in verifyPathIDsExist:
            path = GetPath(pathID, inEnvironment=environmentID)
            if not (path and os.path.exists(path)):
                return False
        return True
    return False


def IsOffsite():
    """ Checks to see if the current active environment is set to being offsite
    """
    return activeEnvironment == 'Offline'


def IsPath(pathID, inEnvironment=''):
    """ Checks to see if the inputed ID is in the list of available path IDs for the
        specified environment
    """
    for tPathID in GetPathIDs(inEnvironment=''):
        if tPathID.lower() == pathID.lower():
            return True
    return False


def IsScripter():
    """ Checks to see if the code path for the development environment exists on the
        user's machine
    """
    return os.path.exists(GetCodePath(inEnvironment='development'))


def LoadConfigData():
    """ Loads the config data from the blur config.ini file to populate the path
    templates and data
    """
    global environments, activeEnvironment, blurConfigFile
    environments = {}

    if not os.path.exists(configFile):
        # If the config file is missing load if from a backup
        RestoreConfig(configFile, '"{fileName}" is missing. Restoring from backup.')
    if os.path.exists(configFile):
        import blurdev.tools

        blurConfigFile = ToolParserClass()
        blurConfigFile.Load(configFile)

        TEMPORARY_TOOLS_ENV = blurdev.tools.TEMPORARY_TOOLS_ENV
        activeEnvironment = blurdev.activeEnvironment().legacyName()

        for tSection in blurConfigFile.GetSections():
            if tSection.GetName().lower() != 'globals':
                environments[tSection.GetName()] = tSection

        tDefaultSection = SectionClass('DEFAULT')
        for tKey, tValue in iteritems(blurConfigFile.defaults()):
            tDefaultSection.SetProperty(tKey, tValue)
        environments['default'] = tDefaultSection

        # set up the temporary environment if pressent
        env = blurdev.tools.ToolsEnvironment.findEnvironment(TEMPORARY_TOOLS_ENV)
        if not env.isEmpty():
            codeRootPath = os.path.abspath(
                os.path.join(env.path(), 'maxscript', 'treegrunt')
            )
            if os.path.exists(codeRootPath):
                tSection = SectionClass(TEMPORARY_TOOLS_ENV)
                tSection.SetProperty('codeRoot', codeRootPath)
                codeLibPath = os.path.abspath(os.path.join(codeRootPath, 'lib'))
                if os.path.exists(codeLibPath):
                    tSection.SetProperty('startupPath', codeLibPath)
                environments[TEMPORARY_TOOLS_ENV] = tSection
        return True
    return False


def RestoreConfig(fileName, msg=None):
    """ Copies a fresh config.ini from the backup location.

        If msg is provided it will be printed before it copies the file
    """
    path = os.environ.get('BDEV_CONFIG_INI_BACKUP')
    if path and os.path.exists(path):
        if msg:
            print(msg.format(fileName=fileName))
        import shutil

        shutil.copy2(path, fileName)
        return True
    return False


def RemovePathTemplates(inPath, inEnvironment='', inCustomKeys={}):
    """ Removes templates from the inputed path - this way paths can be built using
        symbolic links
    """
    tSplit = inPath.replace('[', ']').split(']')
    outName = ''
    for tPart in tSplit:
        if tPart.lower() == 'username':
            import getpass

            tPart = getpass.getuser()
        elif IsPath(tPart):
            tPart = GetPath(
                tPart, inEnvironment=inEnvironment, inIncludeLastSeparator=False
            )
        elif tPart in inCustomKeys:
            tPart = inCustomKeys[tPart]
        outName += tPart
    return outName


def SetActiveEnvironment(inEnvironment):
    """ Sets the current active environment to the inputed value
    """
    global activeEnvironment

    inEnvironment = _normEnv(inEnvironment)

    if inEnvironment != activeEnvironment and inEnvironment in environments:
        activeEnvironment = inEnvironment
        return True
    return False


def ReloadAllModules():
    """ Reloads all modules in memory
    """
    for module in sys.modules.itervalues():
        if (module is not None) and module.__name__.find("blur") != -1:
            try:
                if module.__name__ not in ["blurdev.ini"]:
                    reload(module)
                # xsi.LogMessage( "Reloaded:  " + module.__name__ )
            except Exception:
                pass
                # xsi.LogMessage( "No Module Named:  " + module.__name__ )
    return True


def SetCodePath(inEnvironment, reloadModules=False):
    """ Sets the current active environment to the inputed value, replacing the code
        path within the sys path info for importing libraries from the right environment
    """
    oldCodePath = GetCodePath()
    outCodePath = oldCodePath
    success = SetActiveEnvironment(inEnvironment)

    if success:
        newCodePath = outCodePath = GetCodePath()

        normNewPath = os.path.normpath(newCodePath.lower())
        normOldPath = os.path.normpath(oldCodePath.lower())

        for i in range(len(sys.path)):
            if sys.path[i]:
                sys.path[i] = sys.path[i].replace(normOldPath, normNewPath)

        if not normNewPath + '\\lib' in sys.path:
            addSysPath(normNewPath + '\\lib')

        if reloadModules:
            ReloadAllModules()

    return outCodePath


def NormPath(inPath, inPathSeparator="/", inIncludeLastSeparator=True):
    """ Normalizes the inputed path
    """
    if inPath == "":
        return ""

    tUNCPath = ""
    if inPath[0] == "\\" and inPath[1] == "\\":
        tUNCPath = "\\\\"

    inPath = inPath.strip('\\/')

    tPathList = inPath.replace("\\", "/").split("/")
    outNormPath = tPathList[0]
    for i in range(1, len(tPathList)):
        outNormPath += inPathSeparator + tPathList[i]

    if os.path.splitext(tPathList[len(tPathList) - 1])[1] or (
        not inIncludeLastSeparator
    ):
        return tUNCPath + outNormPath

    return tUNCPath + outNormPath + inPathSeparator


def EndGlobalsFN():
    return None


def IsInt(inString):
    """ Checks if the inputed string is a valid int type
    """
    try:
        int(inString)
        return True
    except Exception:
        return False


def IsFloat(inString):
    """ Checks if the inputed string is a valid float type
    """
    try:
        float(inString)
        return True
    except Exception:
        return False


@contextmanager
def temporaryDefaults():
    """ Context that restores the current DEFAULT settings in memory, after editing.

    When modifying the DEFAULT section with blurdev.ini.SetINISetting, it updates the
    DEFAULT values stored in memory, so any future saves with blurdev.ini, will have
    those changes. If you want to update DEFAULT for a single file, but not update
    the global defaults, you can use this context. Any changes made to DEFAULT while
    this context is active will be reverted afterwards, and you can make changes to
    multiple DEFAULT keys.
    """
    env = environments['default']
    sectionName = env._sectionName
    properties = copy.copy(env._properties)
    try:
        yield
    finally:
        environments['default'].__dict__['_sectionName'] = sectionName
        environments['default'].__dict__['_properties'] = properties
