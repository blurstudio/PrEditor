##
# 	\namespace	python.blurdev.gui.dialogs.configdialog.configwidget
#
# 	\remarks	Defines the Config widget for the ConfigDialog system
#               The class is setup as a static data access so that modules can easily
#               import the config widgets and access their information without needing
#               to instantiate them, as well as providing the ConfigDialog a way to
#               display them for user input
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/19/10
#

from __future__ import absolute_import
import copy

from Qt.QtWidgets import QWidget


class ConfigSectionWidget(QWidget):
    def __init__(self, section, parent=None):
        super(ConfigSectionWidget, self).__init__(parent)
        self.setObjectName(section.name())

        # record the section
        self._section = section

        # record the initial settings
        self._defaults = copy.deepcopy(self._section._properties)

        # init the ui
        self.initUi()

        # refresh the ui
        self.refreshUi()

    def checkForSave(self):
        """Checks the widget to see if the data stored is invalid

        Returns:
            bool: if the data is successfully saved or ready to otherwise close/update
        """
        return True

    def commit(self):
        """Saves the current config values to the system this method will be called by
        the config dialog's Save/Save & Exit buttons

        Returns:
            bool: should return True if the commit was successful
        """
        return True

    def configData(self, key, default=None):
        """Returns the data set on the main config window for the given key

        Args:
            key (str):

        Returns:
            variant:
        """
        return self.window().configData(key, default)

    def configSet(self):
        return self._section.configSet()

    def initUi(self):
        pass

    def recordUi(self):
        """Records the ui to the current data"""
        pass

    def refreshUi(self):
        """Refreshes the ui to match the latest data"""
        pass

    def reset(self):
        """Resets the config values to their default this method will be called by the
        config dialog's Reset button

        Returns:
            bool: should return True if the reset was successful
        """
        self._section._properties = copy.deepcopy(self._defaults)
        self.refreshUi()

    def section(self):
        return self._section

    def setConfigData(self, key, value):
        """Sets the global data for the given key to the inputed value

        Args:
            key:
            value:
        """
        self.window().setConfigData(key, value)
