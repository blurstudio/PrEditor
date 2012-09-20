#
# 	__PYDOC__
#
# 	[TITLE]
# 	blurGlobals.py
#
# 	[DESCRIPTION]
# 	Functions to read through and initialize the paths for Blur Studios.
# 	Also has functions for accessing & setting INI information.
#
# 	[CREATION INFO]
# 	Author: Eric Hulser
# 	Email: beta@blur.com
# 	Company: Blur Studios
# 	Date: 06/21/06
#
# 	[HISTORY]
# 	--1.0	- Created
#
# 	[DEPENDENCIES]
#
# 	__END__
#

# -------------------------------------------------------------------------------------------------------------
# 										GLOBAL DEFINITIONS
# -------------------------------------------------------------------------------------------------------------

import ConfigParser, sys, os, os.path, sys, shutil, getpass

configFile = "c:/blur/config.ini"  # Default path information for Blur Studio
environments = {}
activeEnvironment = 'production'
blurConfigFile = None

# -------------------------------------------------------------------------------------------------------------
# 											INI FUNCTIONS
# -------------------------------------------------------------------------------------------------------------


def GetINISetting(inFileName, inSection="", inKey=""):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	Prototype:
    #				FUNCTION blur.globals.GetINISetting( inFileName, inSection, inKey = ''
    #
    #	Remarks:
    #				Gets the value of the inputed key found in the given section of an INI file, if it exists and
    #				the key is specified.  If the key is not specified, but the section exists, then the function
    #				will return a list of all the keys in that section.
    #	Parameters:
    #				inFileName			<string>
    #				inSection			<variant>
    #				inKey				<variant>		Default:''
    #	Returns:
    #				<string> || <list>[ <string>,.. ]
    #	History:
    #				- Created: EKH 06/26/06
    #-------------------------------------------------------------------------------------------------------------
    """
    if os.path.isfile(inFileName):
        tParser = ToolParserClass()
        tParser.read(inFileName)
        inSection = unicode(inSection)
        inKey = unicode(inKey)
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


def SetINISetting(inFileName, inSection, inKey, inValue, useConfigParser=False):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	Prototype:
    #				FUNCTION blur.globals.SetINISetting( inFileName, inSection, inKey, inValue )
    #
    #	Remarks:
    #				Sets the ini section setting of the inputed file with the give key/value pair.
    #				By default it uses blurdev.ini.ToolParserClass, but if you set useConfigParser to True
    #				It will use ConfigParser.ConfigParser instead()
    #	Parameters:
    #				inFileName			<string>
    #				inSection			<variant>
    #				inKey				<variant>
    #				inValue				<variant>
    #				useConfigParser		<bool>		Default False
    #	Returns:
    #				True
    #	History:
    #				- Created: EKH 06/26/06
    #-------------------------------------------------------------------------------------------------------------
    """
    if useConfigParser:
        tParser = ConfigParser.ConfigParser()
    else:
        tParser = ToolParserClass()
    inSection = unicode(inSection)
    inKey = unicode(inKey)
    inValue = unicode(inValue)

    if os.path.isfile(inFileName):
        tParser.read(inFileName)
    if not tParser.has_section(inSection):
        tParser.add_section(inSection)

    tParser.set(inSection, inKey, inValue)
    if useConfigParser:
        f = open(inFileName, 'w')
        tParser.write(f)
        f.close()
        return True
    return tParser.Save(inFileName)


def DelINISetting(inFileName, inSection, inKey=""):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	Prototype:
    #				FUNCTION blur.globals.DelINISetting( inFileName, inSection, inKey )
    #
    #	Remarks:
    #				Delets the given section & key ( if specified ) from the inputed file, if the file exists.
    #	Parameters:
    #				inFileName			<string>
    #				inSection			<variant>
    #				inKey				<variant>
    #	Returns:
    #				<boolean>
    #	History:
    #				- Created: EKH 06/26/06
    #-------------------------------------------------------------------------------------------------------------
    """
    if os.path.isfile(inFileName):
        tParser = ToolParserClass()
        tParser.read(inFileName)
        inSection = unicode(inSection)
        inKey = unicode(inKey)

        if tParser.has_section(inSection):
            if inKey:
                tParser.remove_option(inSection, inKey)
            else:
                tParser.remove_section(inSection)
            return tParser.Save(inFileName)
    return False


def EndINIFn():
    return None


class switch(object):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\brief: Provides a switch call that mimics that of C/C++.
    #-------------------------------------------------------------------------------------------------------------
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


# -------------------------------------------------------------------------------------------------------------
# 										TOOL SETTING CLASS
# -------------------------------------------------------------------------------------------------------------


class SectionClass:
    """
    #-------------------------------------------------------------------------------------------------------------
    #	Prototype:
    #				CLASS SectionClass
    #
    #	Remarks:
    #				Represents an INI file's section, providing quick and easy access to its properties
    #	Methods:
    #				GetProperty( <string> propName )
    #				GetName()
    #				Load( <ConfigParser> parser )
    #				Save( <ConfigParser> parser )
    #				SetID( <string> sectionName )
    #				SetProperty( <string> propName, <variant> propValue )
    #	Members:
    #				<void>
    #	History:
    #				- Created: EKH 11/14/06
    #-------------------------------------------------------------------------------------------------------------
    """

    def __getattr__(self, attrKey):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Overloaded the get attribute for this class to run the GetProperty function for the given
        #				attribute
        #
        #	\param		attrKey		<string>
        #
        #	\return
        #				<variant> || AttributeError
        #-------------------------------------------------------------------------------------------------------------
        """
        if not attrKey.startswith('_'):
            return self.GetProperty(attrKey)
        raise AttributeError, attrKey

    def __setattr__(self, attrKey, attrValue):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Overloaded the set attribute for this class to run the SetProperty function for the given
        #				attribute
        #
        #	\param		attrKey		<string>
        #	\param		attrValue	<variant>
        #
        #	\return
        #				True || AttributeError
        #-------------------------------------------------------------------------------------------------------------
        """
        if not attrKey.startswith('_'):
            self.SetProperty(attrKey, attrValue)
        else:
            raise AttributeError, attrKey

    def __init__(self, sectionName):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Class initialization.  Set the sectionName for the class instance to the given variable *required*
        #
        #	\param		sectionName		<string>		**Required
        #
        #-------------------------------------------------------------------------------------------------------------
        """
        self.__dict__['_sectionName'] = sectionName
        self.__dict__['_properties'] = {}

    def GetName(self):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Returns the section name for this instance
        #
        #	\return
        #				<string>
        #-------------------------------------------------------------------------------------------------------------
        """
        return self._sectionName

    def GetProperty(self, propName):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Gets the property whose dictionary key matches the inputed name from the instance's
        #				_properties dictionary, or returns a blank string if not found.
        #
        #	\param		propName		<string>
        #
        #	\return
        #				<string>
        #-------------------------------------------------------------------------------------------------------------
        """
        propName = propName.lower()
        if propName in self._properties:
            return self._properties[propName]
        return ''

    def GetPropNames(self):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Returns the _properties dictionary keys
        #
        #	\return
        #				<list> [ <string>, .. ]
        #-------------------------------------------------------------------------------------------------------------
        """
        return self._properties.keys()

    def GetPropValues(self):
        return self._properties.values()

    def Load(self, parser):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Loads the data from the inputed parser if it has a section whose name matches this instance's
        #				name.
        #
        #	\param		parser		<ConfigParser> || <ToolParserClass>
        #
        #	\return
        #				<boolean>
        #-------------------------------------------------------------------------------------------------------------
        """
        if parser.has_section(self._sectionName):
            self.__dict__['_properties'] = {}

            for tKey, tValue in parser.items(self._sectionName):
                self._properties[tKey] = tValue

            return True
        return False

    def Save(self, parser):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Saves the data for this instance to the inputed parser
        #
        #	\param		parser		<ConfigParser> || <ToolParserClass>
        #
        #	\return
        #				True
        #-------------------------------------------------------------------------------------------------------------
        """
        if not parser.has_section(self._sectionName):
            parser.add_section(self._sectionName)

        for tKey, tValue in self._properties.iteritems():
            # only save the value if its diffrent or not pressent in the default section
            if self.GetProperty(tKey) != unicode(tValue):
                parser.set(self._sectionName, tKey, unicode(tValue))
        return True

    def SetName(self, sectionName):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Sets the instances name to the inputed string
        #
        #	\param		sectionName		<string>
        #
        #-------------------------------------------------------------------------------------------------------------
        """
        self._sectionName = sectionName

    def SetProperty(self, propName, propValue):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Sets the property and value for the INI part based on the inputed values.  ** The inputed
        #				propName is converted to lowercase **
        #
        #	\param		propName		<string>
        #	\param		propValue		<variant>
        #
        #	\return
        #				True
        #-------------------------------------------------------------------------------------------------------------
        """
        propName = unicode(propName).lower()
        self._properties[propName] = propValue
        return True


class ToolParserClass(ConfigParser.ConfigParser):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	Prototype:
    #				CLASS ToolParserClass : EXTENDS ConfigParser
    #
    #	Remarks:
    #				Provides an easy way to create and manage tool related config files.
    #	Methods:
    #				GetFileName()
    #				GetSection( <string> sectionName )
    #				Load( <string> fileName = '' )
    #				Save( <string> fileName = '' )
    #	Members:
    #				<void>
    #	History:
    #				- Created: EKH 11/14/06
    #-------------------------------------------------------------------------------------------------------------
    """

    def __getattr__(self, attrKey):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Overloaded the __getattr__ function to use the GetSection function for this class type
        #
        #	\param		attrKey		<string>
        #
        #	\return
        #				<SectionClass> || AttributeError
        #-------------------------------------------------------------------------------------------------------------
        """
        if not attrKey.startswith('_'):
            return self.GetSection(attrKey)
        raise AttributeError, attrKey

    def __init__(self, toolID='', location=''):
        ConfigParser.ConfigParser.__init__(self)
        self._toolID = toolID
        self._location = location
        self._sectionClasses = []

        if toolID:
            self.Load()

    def GetFileName(self):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Builds the file name for this class instance using its location and toolID.
        #				Locations:
        #						3dsMax:	Uses 'maxPlugPath'  pathID with the GetPath function
        #						XSI:	Uses 'xsiPlugPath'  pathID with the GetPath function
        #						Other:	Uses 'userPlugPath' pathID with the GetPath function
        #
        #				The fileName is built as:
        #					GetPath( pathID ) + toolID + '.ini'
        #
        #				If there is no toolID specified for this instance, then this function returns a blank string.
        #
        #	\return
        #				<string>
        #-------------------------------------------------------------------------------------------------------------
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
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Returns the section whose name matches the inputed string, adding a new SectionClass to this
        #				instance's list if none is found.
        #
        #	\param		sectionName		<string>
        #
        #	\return
        #				<SectionClass>
        #-------------------------------------------------------------------------------------------------------------
        """
        for tSection in self._sectionClasses:
            if tSection.GetName().lower() == sectionName.lower():
                return tSection

        outSection = SectionClass(sectionName=sectionName)
        self._sectionClasses.append(outSection)
        return outSection

    def GetSectionNames(self):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Get a list of all the section names for this class instance
        #
        #	\return
        #				<list>[ <string>, .. ]
        #-------------------------------------------------------------------------------------------------------------
        """
        return [tSection.GetName() for tSection in self._sectionClasses]

    def GetSections(self):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Returns the sction class children of this ToolParser instance
        #
        #	\return
        #				<list>[ <SectionClass>, .. ]
        #-------------------------------------------------------------------------------------------------------------
        """
        return self._sectionClasses

    def Load(self, fileName=''):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Load up a config file and builds its class information based on its sections/keys/values.
        #				If the fileName is specified, then the parser uses the inputed file name to open, otherwise
        #				it will use the GetFileName function to build its own name.
        #
        #	\param		fileName		<string>		OPTIONAL
        #
        #	\return
        #				<boolean>
        #-------------------------------------------------------------------------------------------------------------
        """
        if not fileName:
            fileName = self.GetFileName()

        if fileName and os.path.exists(fileName):
            self.read(fileName)

            self._sectionClasses = []
            for tSectionName in self.sections():
                tSection = SectionClass(sectionName=tSectionName)
                tSection.Load(self)
                self._sectionClasses.append(tSection)

            return True
        return False

    def Save(self, fileName=''):
        """
        #-------------------------------------------------------------------------------------------------------------
        #	\remarks
        #				Save out a config file based on the class information, saving to the specified fileName.
        #				If a blank string is passed in for the fileName, then it sets the fileName value using the
        #				GetFileName function.
        #
        #	\param		fileName		<string>		OPTIONAL
        #
        #	\return
        #				<boolean>
        #-------------------------------------------------------------------------------------------------------------
        """
        if not fileName:
            fileName = self.GetFileName()

        if fileName:
            for tSection in self._sectionClasses:
                tSection.Save(self)

            self.write(open(fileName, 'w'))
            return True
        return False

    def write(self, fp):
        """
            :remarks	Saves the ini file in alphabetical order
            :param		fp	<file>	A python file object opened in write mode
        """
        sects = ('GLOBALS', 'default')
        for section in sects:
            if section in self._sections:
                fp.write("[%s]\n" % section)
                for (key, value) in sorted(self._sections[section].items()):
                    if key != "__name__":
                        fp.write(
                            "%s = %s\n" % (key, unicode(value).replace('\n', '\n\t'))
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
                            "%s = %s\n" % (key, unicode(value).replace('\n', '\n\t'))
                        )
                fp.write("\n")
        for section in sorted(self._sections):
            if not section in sects:
                fp.write("[%s]\n" % section)
                for (key, value) in sorted(self._sections[section].items()):
                    if key != "__name__":
                        fp.write(
                            "%s = %s\n" % (key, unicode(value).replace('\n', '\n\t'))
                        )
                fp.write("\n")


# -------------------------------------------------------------------------------------------------------------
# 									BLUR GLOBALS PATH DEFINITIONS
# -------------------------------------------------------------------------------------------------------------


def _normEnv(environmentID):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Normalizes inputed environmentID.  Function is setup for backwards compatibility, setting
    #				code path 'local' and 'network' to work with new environments and turns the ID to lowercase
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
    """
    # 	if ( environmentID.lower() == 'local' ):
    # 		return 'Development'
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
        if not path in sys.path:
            sys.path.append(path)
            return True
    return False


def AddResourcePath(inRelativePath):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Adds a relative path to the sys.path list, combining the inputed path with the current
    #				GetCodePath results.
    #	\example
    #				AddResourcePath( 'Main/Production_Tools/Treegrunt_resource/' ) adds 'h:/treegrunt/Main/Production_Tools/Treegrunt_resource'
    #				if 'h:/treegrunt/' is the current codeRoot value.
    #
    #	\param		inRelativePath		<string>
    #
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    tPath = os.path.normpath(os.path.join(GetCodePath(), inRelativePath).lower())
    if not tPath in sys.path:
        sys.path.append(tPath)
        return True
    return False


def GetActiveEnvironment():
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Returns the active environment SectionClass
    #	\return
    #				<SectionClass>
    #-------------------------------------------------------------------------------------------------------------
    """
    return environments[activeEnvironment]


def GetActiveEnvironmentID():
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Returns the id of the active environment
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
    """
    return GetActiveEnvironment().GetName()


def GetCodePath(inEnvironment=''):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Returns the 'codeRoot' pathID value for the given environment.  If no environment is specified,
    #				then the current active environment is used.
    #
    #	\param		inEnvironment 		<string>
    #
    #	\sa GetPath
    #
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
    """
    return GetPath('codeRoot', inEnvironment=inEnvironment)


def GetEnvironment(environmentID):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Returns the SectionClass instance whose ID matches the inputed envrionment ID from the global
    #				environments list (if a match is found)
    #
    #	\param		environmentID		<string>
    #
    #	\return
    #				<SectionClass>
    #-------------------------------------------------------------------------------------------------------------
    """
    if not environmentID:
        environmentID = activeEnvironment

    environmentID = _normEnv(environmentID)

    if environmentID in environments:
        return environments[environmentID]
    return None


def GetEnvironmentIDs(verifyPathIDsExist=[]):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Returns all available environment IDs from the global environments dictionary
    #
    #	\return
    #				<list>[ <string>, .. ]
    #-------------------------------------------------------------------------------------------------------------
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
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Gets the path associated with the inputed path key.  If an environment is passed in, then
    #				that environment section is used to find the path value, otherwise the active environment is
    #				used.  If the inputed path key does not exist in the given environment, then the value for the
    #				default environment is returned, and if no match exists for the default section, a blank string
    #				is outputed.
    #
    #	\param		inPathKey			<string>
    #	\param		inEnvironment		<string>
    #	\param		inPathSeparator		<string>
    #
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
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
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Collects all the available pathIDs for the inputed environment, using the active environment
    #				if no input is specified.  Combines the given environment and the default values (which are
    #				available for any environment)
    #
    #	\param		inEnvironment			<string>
    #
    #	\return
    #				<list>[ <string>, .. ]
    #-------------------------------------------------------------------------------------------------------------
    """
    if not inEnvironment:
        inEnvironment = activeEnvironment

    inEnvironment = _normEnv(inEnvironment)
    outPropNames = environments['default'].GetPropNames()

    if inEnvironment in environments:
        for tPropName in environments[inEnvironment].GetPropNames():
            if not tPropName in outPropNames:
                outPropNames.append(tPropName)

    return outPropNames


def GetPaths(inEnvironment='', inPathSeparator='/'):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Collects all the available paths for the inputed environment, using the active environment
    #				if no input is specified.  Combines the given environment and the default values (which are
    #				available for any environment)
    #
    #	\param		inEnvironment		<string>
    #	\param		inPathSeparator		<string>
    #
    #	\sa GetPathIDs
    #
    #	\return
    #				<list>[ <string>, .. ]
    #-------------------------------------------------------------------------------------------------------------
    """
    outPaths = []
    for tPathID in GetPathIDs(inEnvironment=inEnvironment):
        outPaths.append(GetPath(tPathID, inEnvironment=inEnvironment))

    return outPaths


def IsEnvironmentValid(environmentID='', verifyPathIDsExist=[]):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Checks to see if the given environment exists by checking the paths associated with it,
    #				if the pathIDs array is blank, then all the paths are checked, otherwise only those specified
    #				are checked.
    #
    #	\param		environmentID		<string>
    #	\param		pathIDs				<list>[ <string>, .. ]
    #
    #	\return
    #				<bool>
    #-------------------------------------------------------------------------------------------------------------
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
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Checks to see if the current active environment is set to being offsite
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    return activeEnvironment == 'Offline'


def IsPath(pathID, inEnvironment=''):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Checks to see if the inputed ID is in the list of available path IDs for the specified
    #				environment
    #
    #	\param		pathID			<string>
    #	\param		inEnvironment	<string>
    #
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    for tPathID in GetPathIDs(inEnvironment=''):
        if tPathID.lower() == pathID.lower():
            return True
    return False


def IsScripter():
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Checks to see if the code path for the development environment exists on the user's machine
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    return os.path.exists(GetCodePath(inEnvironment='development'))


def LoadConfigData():
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Loads the config data from the blur config.ini file to populate the path templates and data
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    global environments, activeEnvironment

    environments = {}

    if os.path.exists(configFile):
        global blurConfigFile
        blurConfigFile = ToolParserClass()
        blurConfigFile.Load(configFile)
        import blurdev

        activeEnvironment = unicode(blurdev.activeEnvironment().objectName())

        for tSection in blurConfigFile.GetSections():
            if tSection.GetName().lower() != 'globals':
                environments[tSection.GetName()] = tSection

        tDefaultSection = SectionClass('DEFAULT')
        for tKey, tValue in blurConfigFile.defaults().iteritems():
            tDefaultSection.SetProperty(tKey, tValue)
        environments['default'] = tDefaultSection
        return True
    return False


def RemovePathTemplates(inPath, inEnvironment='', inCustomKeys={}):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Removes templates from the inputed path - this way paths can be built using symbolic links
    #
    #	\param		inPath			<string>
    #	\param		inCustomKeys	<dictionary>{ <key>: <string> }
    #
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
    """
    tSplit = inPath.replace('[', ']').split(']')
    outName = ''
    for tPart in tSplit:
        if tPart.lower() == 'username':
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
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Sets the current active environment to the inputed value
    #
    #	\param		inEnvironment		<string>
    #
    #	\return
    #				<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    global activeEnvironment

    inEnvironment = _normEnv(inEnvironment)

    if inEnvironment != activeEnvironment and inEnvironment in environments:
        activeEnvironment = inEnvironment
        return True
    return False


def ReloadAllModules():
    """Reloads all modules in memory"""

    for module in sys.modules.itervalues():
        if (module != None) and module.__name__.find("blur") != -1:
            try:
                if not module.__name__ in ["blurdev.ini"]:
                    reload(module)
                # xsi.LogMessage( "Reloaded:  " + module.__name__ )
            except:
                pass
                # xsi.LogMessage( "No Module Named:  " + module.__name__ )

    return True


def SetCodePath(inEnvironment, reloadModules=False):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Sets the current active environment to the inputed value, replacing the code path within
    #				the sys path info for importing libraries from the right environment
    #
    #	\param		inEnvironment			<string>
    #
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
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
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks
    #				Normalizes the inputed path
    #
    #	\param		inPath					<string>
    #	\param		inPathSeparator			<string>
    #	\param		inIncludeLastSeparator	<boolean>
    #
    #	\return
    #				<string>
    #-------------------------------------------------------------------------------------------------------------
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


# -------------------------------------------------------------------------------------------------------------
# 										BOOLEAN FUNCTIONS
# -------------------------------------------------------------------------------------------------------------


def IsInt(inString):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks 	Checks if the inputed string is a valid int type
    #	\param		<string>
    #	\return 	<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    try:
        int(inString)
        return True
    except:
        return False


def IsFloat(inString):
    """
    #-------------------------------------------------------------------------------------------------------------
    #	\remarks 	Checks if the inputed string is a valid float type
    #	\param		<string>
    #	\return 	<boolean>
    #-------------------------------------------------------------------------------------------------------------
    """
    try:
        float(inString)
        return True
    except:
        return False


# -------------------------------------------------------------------------------------------------------------
# 										PATH FUNCTIONS
# -------------------------------------------------------------------------------------------------------------
def ______end______():
    pass


# -------------------------------------------------------------------------------------------------------------
# 											INITIALIZATION
# -------------------------------------------------------------------------------------------------------------

LoadConfigData()
