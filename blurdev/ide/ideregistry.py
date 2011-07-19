##
# 	\namespace	blurdev.ide.ideaddon
#
# 	\remarks	Creates the base class for Addons that allow developers to extend
#               the IDE through plugins
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/06/11
#

import os

from blurdev.enum import enum

RegistryType = enum('Extension', 'Filename', 'Overlay')


class IdeRegistry(object):
    def __init__(self):
        self._commands = {}

        self.registerDefaults()

    def find(self, registryType, expression):
        """
            \remarks	searches the registry for the inputed registry command
                        based on the type and regex
                        
            \param		registryType	<blurdev.ide.ideregistry.RegistryType>
            \param		expression		<str>		text to compare against regex in registry
            
            \return		<tuple> ( <str> || <function> || None command, <str> args, <str> startpath )
        """
        cmds = self._commands.get(registryType)
        if cmds:
            import re

            for regex in cmds.keys():
                if re.match(regex, expression):
                    return cmds[regex]
        return (None, '', '')

    def registerDefaults(self):
        # create default extension registry
        extensions = {
            '^.ui$': (
                os.environ['BDEV_QT_DESIGNER'],
                '',
                os.path.dirname(os.environ['BDEV_QT_DESIGNER']),
            ),
            '^.schema$': (
                os.environ['BDEV_CLASSMAKER'],
                '',
                os.path.dirname(os.environ['BDEV_CLASSMAKER']),
            ),
        }

        # create default filename registry
        filenames = {}

        # create default registry information
        self._commands[RegistryType.Extension] = extensions
        self._commands[RegistryType.Filename] = filenames

    def register(self, registryType, regex, command):
        """
            \remarks	registers the inputed command for the given type
                        to the registry
            
            \param		registryType	<blurdev.ide.ideregistry.IdeRegistry>
            \param		regex			<str> 		regular expression to search for in the registry
            \param		command			<tuple> ( <str> || <function> command, <str> args, <str> startpath )
        """
        self._commands.setdefault(registryType, {})
        self._commands[registryType][regex] = command

    def unregister(self, registryType, regex):
        """
            \remarks	removes the inputed command from the registry based
                        on the type and extension
            
            \param		registryType	<blurdev.ide.registry.IdeRegistry>
            \param		regex			<str>		regular expression to search for in the registry
        """
        if registryType in self._commands and regex in self._commands[registryType]:
            self._commands[registryType].pop(regex)
            return True
        return False
