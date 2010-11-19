##
# 	\namespace	python.blurdev.gui.dialogs.configdialog.configwidget
#
# 	\remarks	Defines the Config widget for the ConfigDialog system

# 				The class is setup as a static data access so that modules can easily import the config widgets and access their information

# 				without needing to instantiate them, as well as providing the ConfigDialog a way to display them for user input
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/19/10
#


from PyQt4.QtGui import QWidget


class ConfigWidget(QWidget):
    @staticmethod
    def checkForSave():

        """

            \remarks	checks the widget to see if the data stored is invalid

            \return		<bool>	if the data is successfully saved or ready to otherwise close/update

        """

        return True

    @staticmethod
    def reset():

        """

            \remarks	resets the config values to their default

                        this method will be called by the config dialog's Reset button

            \return		<bool> 	should return True if the reset was successful

        """

        return True

    @staticmethod
    def commit():

        """

            \remarks	saves the current config values to the system

                        this method will be called by the config dialog's Save/Save & Exit buttons

            \return		<bool> 	should return True if the commit was successful

        """

        return True

    @staticmethod
    def register(configSet):

        """

            \remarks	registers this class to the inputed config set

                        this should call the configSet.registerConfig() method

            \sa			blurdev.gui.dialogs.configdialog.ConfigSet.registerConfig

            \param		configSet		<blurdev.gui.dialogs.configdialog.ConfigSet>

        """

        pass
