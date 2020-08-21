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
        """
            \remarks	checks the widget to see if the data stored is invalid
            \return     <bool>  if the data is successfully saved or ready to otherwise
            close/update
        """
        return True

    def commit(self):
        """
            \remarks	saves the current config values to the system
                        this method will be called by the config dialog's Save/Save &
                        Exit buttons
            \return		<bool> 	should return True if the commit was successful
        """
        return True

    def configData(self, key, default=None):
        """
            \remarks    returns the data set on the main config window for the given key
            \param      key     <str>
            \return     <variant>
        """
        return self.window().configData(key, default)

    def configSet(self):
        return self._section.configSet()

    def initUi(self):
        pass

    def recordUi(self):
        """
            \remarks	records the ui to the current data
        """
        pass

    def refreshUi(self):
        """
            \remarks	refreshes the ui to match the latest data
        """
        pass

    def reset(self):
        """
            \remarks	resets the config values to their default
                        this method will be called by the config dialog's Reset button
            \return		<bool> 	should return True if the reset was successful
        """
        self._section._properties = copy.deepcopy(self._defaults)
        self.refreshUi()

    def section(self):
        return self._section

    def setConfigData(self, key, value):
        """
            \remarks	sets the global data for the given key to the inputed value
            \param		key
            \param		value
        """
        self.window().setConfigData(key, value)
