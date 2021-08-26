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

from __future__ import absolute_import
import os
import re

from blurdev.enum import enum

RegistryType = enum(
    'Extension', 'Filename', 'Overlay', 'GlobalOverride', 'ProjectOverride'
)


class IdeRegistry(object):
    def __init__(self):
        self._commands = dict([(rtype, {}) for rtype in RegistryType.values()])

        self.registerDefaults()

    def commands(self):
        return self._commands

    def findCommand(self, filename):
        """
            \remarks	looks up the command based on the inputed filename
            \param		filename	<str>
            \return		<str> || <method> || None
        """
        filename = str(filename)
        ext = os.path.splitext(filename)[-1]

        # look through the different options
        for rtype in (
            RegistryType.ProjectOverride,
            RegistryType.GlobalOverride,
            RegistryType.Filename,
            RegistryType.Extension,
        ):
            for expr in self._commands[rtype]:
                if re.match('^%s$' % expr, filename) or re.match('^%s$' % expr, ext):
                    return self._commands[rtype][expr]
        return None

    def find(self, registryType, expression):
        """
            \remarks	searches the registry for the inputed registry command
                        based on the type and regex

            \param		registryType	<blurdev.ide.ideregistry.RegistryType>
            \param		expression		<str>		text to compare against regex in registry

            \return     <tuple> ( <str> || <function> || None command, <str> args, <str>
                        startpath )
        """
        cmds = self._commands.get(registryType)
        if cmds:
            for regex in cmds.keys():
                if re.match('^%s$' % regex, expression):
                    return cmds[regex]
        return None

    def flush(self, registryType):
        """
            \remarks	clears the registry type based on the inputed class
        """
        self._commands[registryType] = {}

    def registerDefaults(self):
        # create default extension registry
        extensions = {
            '.ui': '$BDEV_APP_QDESIGNER "%(filepath)s"',
            '.schema': '$BDEV_APP_CLASSMAKER -s "%(filepath)s"',
            '.png': '$BDEV_APP_IMAGEEDITOR "%(filepath)s"',
            '.sh': '$BDEV_CMD_SHELL_EXECFILE',
            '.bat': '$BDEV_CMD_SHELL_EXECFILE',
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
            \param      command         <tuple> ( <str> || <function> command, <str>
                                        args, <str> startpath )
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
