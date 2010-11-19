##
# 	\namespace	blurdev.gui.dialogs.configdialog.configset
#
# 	\remarks	Defines the ConfigSet class that will manage config widgets
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/20/10
#

from PyQt4.QtCore import QObject


class ConfigSetItem(QObject):
    def __init__(self, configSet):

        QObject.__init__(self, configSet)

        self._configClass = None

        self._groupName = 'Default'

        self._icon = ''

    def configClass(self):

        return self._configClass

    def setConfigClass(self, configClass):

        self._configClass = configClass

    def setGroupName(self, grpName):

        self._groupName = grpName

    def setIcon(self, icon):

        self._icon = icon


# ---------------------------------------------------------------


class ConfigSet(QObject):
    def __init__(self, parent=None):

        QObject.__init__(self, parent)

    def configGroups(self):

        output = []

        for child in self.findChildren(ConfigSetItem):

            grpName = str(child.groupName())

            if not grpName in output:

                output.append(grpName)

        output.sort()

        return output

    def configsForGroup(self, groupName):

        output = [
            child
            for child in self.findChildren(ConfigSetItem)
            if (child.groupName() == groupName)
        ]

        output.sort(lambda x, y: cmp(x.objectName(), y.objectName()))

        return output

    def findConfig(self, configName):

        for child in self.findChildren(ConfigSetItem):

            if child.objectName() == configName:

                return child.configWidget()

        return None

    def registerConfig(self, configName, configClass, group='Default', icon=''):

        item = ConfigSetItem(self)

        item.setObjectName(configName)

        item.setGroupName(group)

        item.setConfigClass(configClass)

        item.setIcon(icon)

        return item
