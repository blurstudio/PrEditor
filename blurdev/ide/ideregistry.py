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
        """Looks up the command based on the inputted filename

        Args:
            filename (str):

        Returns:
            str:
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
        """searches the registry for the inputted registry command based on the type
        and regex

        Args:
            registryType (blurdev.ide.ideregistry.RegistryType):
            expression (str): text to compare against regex in registry

        Returns:
             tuple:
        """
        cmds = self._commands.get(registryType)
        if cmds:
            for regex in cmds.keys():
                if re.match('^%s$' % regex, expression):
                    return cmds[regex]
        return None

    def flush(self, registryType):
        """Clears the registry type based on the inputted class"""
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
        """Registers the inputted command for the given type to the registry

        Args:
            registryType (blurdev.ide.ideregistry.IdeRegistry):
            regex (str): regular expression to search for in the registry
            command (tuple):
        """
        self._commands.setdefault(registryType, {})
        self._commands[registryType][regex] = command

    def unregister(self, registryType, regex):
        """Removes the inputted command from the registry based on the type
        and extension

        Args:
            registryType (blurdev.ide.registry.IdeRegistry):
            regex (str): regular expression to search for in the registry
        """
        if registryType in self._commands and regex in self._commands[registryType]:
            self._commands[registryType].pop(regex)
            return True
        return False
