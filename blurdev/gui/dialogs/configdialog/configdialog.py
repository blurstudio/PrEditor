##
# 	\namespace	blurdev.gui.dialogs.configdialog.configdialog
#
# 	\remarks	Defines the ConfigDialog class that is used to display config plugins for the blurdev system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/20/10
#

from blurdev.gui import Dialog
from Qt.QtWidgets import QTreeWidgetItem


class ConfigSectionItem(QTreeWidgetItem):
    def __init__(self, section):
        QTreeWidgetItem.__init__(self, [section.name()])

        from Qt.QtCore import QSize
        from Qt.QtGui import QIcon

        # store the config set item
        self._section = section

        # set the icon
        self.setIcon(0, QIcon(section.icon()))
        self.setSizeHint(0, QSize(200, 20))

    def section(self):
        return self._section


# --------------------------------------------------------------------------------


class ConfigDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # clear the widget
        widget = self.uiWidgetAREA.takeWidget()
        widget.close()
        widget.setParent(None)
        widget.deleteLater()

        # initialize the header
        self.uiPluginsTREE.header().setVisible(False)

        # create custom properties
        self._configSet = None
        self._sectionCache = {}

        # create connections
        self.uiExitBTN.clicked.connect(self.reject)
        self.uiSaveExitBTN.clicked.connect(self.accept)
        self.uiResetBTN.clicked.connect(self.reset)
        self.uiSaveBTN.clicked.connect(self.commit)
        self.uiPluginsTREE.itemSelectionChanged.connect(self.refreshWidget)

    def accept(self):
        """ commits the config information and then closes down """
        if self.commit():
            Dialog.accept(self)

    def checkForSave(self):
        """ tries to run the active config widget's checkForSave method, if it exists """
        widget = self.uiWidgetAREA.widget()

        if widget:
            return widget.checkForSave()
        return True

    def commit(self):
        """ tries to run the active config widget's commit method, if it exists """

        success = True

        # save all the widgets in the configset
        for widget in self._sectionCache.values():
            # record the interface
            widget.recordUi()

            # save the widget
            if not widget.commit():
                success = False

        if success:
            self._configSet.save()

        return success

    def configData(self, key, default=None):
        """
            \remarks	returns the custom value for the inputed key based on the
                        current config set
            \param		key			<str>
            \param		default		<variant>
            
            \return		<variant>
        """
        return self._configSet.customData(key, default)

    def setConfigSet(self, configSet):
        """ 
            \remarks	sets the config set that should be edited
            \param		configSet	<blurdev.gui.dialogs.configdialog.ConfigSet>
        """

        self._configSet = configSet

        import blurdev

        from Qt.QtCore import QSize
        from Qt.QtGui import QIcon
        from Qt.QtWidgets import QTreeWidgetItem

        self.uiPluginsTREE.blockSignals(True)
        self.uiPluginsTREE.setUpdatesEnabled(False)

        # clear the tree
        self.uiPluginsTREE.clear()

        for group in configSet.sectionGroups():
            # create the group item
            grpItem = QTreeWidgetItem([group])
            grpItem.setIcon(0, QIcon(blurdev.resourcePath('img/folder.png')))
            grpItem.setSizeHint(0, QSize(200, 20))

            # update the font
            font = grpItem.font(0)
            font.setBold(True)
            grpItem.setFont(0, font)

            # create the config set items
            for section in configSet.sectionsInGroup(group):
                grpItem.addChild(ConfigSectionItem(section))

            # add the group item to the tree
            self.uiPluginsTREE.addTopLevelItem(grpItem)
            grpItem.setExpanded(True)

        self.uiPluginsTREE.blockSignals(False)
        self.uiPluginsTREE.setUpdatesEnabled(True)

    def reject(self):
        """ checks this system to make sure the current widget has been saved before exiting """
        if self.checkForSave():
            Dialog.reject(self)

    def refreshWidget(self):
        """ reloads this dialog with the current plugin instance """
        self.uiPluginsTREE.blockSignals(True)

        item = self.uiPluginsTREE.currentItem()

        if isinstance(item, ConfigSectionItem):
            # remove the current widget
            widget = self.uiWidgetAREA.takeWidget()

            # close the old widget
            if widget:
                widget.close()

                # make sure the parenting remains intact
                widget.setParent(self)
            # create a new widget to cache
            key = item.section().uniqueName()
            if not key in self._sectionCache:
                self._sectionCache[key] = item.section().widget(self)

            # create the new widgets plugin
            self.uiWidgetAREA.setWidget(self._sectionCache[key])

        self.uiPluginsTREE.blockSignals(False)
        return True

    def reset(self):
        """ resets the data for the current widget """
        widget = self.uiWidgetAREA.widget()

        if widget:
            widget.reset()
            widget.refreshUi()

        return True

    def selectItem(self, name):
        """ selects the widget item whose name matches the inputed name """
        # go through the group level
        for i in range(self.uiPluginsTREE.topLevelItemCount()):
            item = self.uiPluginsTREE.topLevelItem(i)

            # go through the config level
            for c in range(item.childCount()):
                pitem = item.child(c)

                # select the item if the name matches
                if pitem.text(0) == name:
                    pitem.setSelected(True)
                    return True

        return False

    def setConfigData(self, key, value):
        """
            \remarks	sets the custom data on the config set to the inputed value
            
            \param		key		<str>
            \param		value	<variant>
        """
        return self._configSet.setCustomData(key, value)

    def setCurrentSection(self, section):
        """
            \remarks	sets the current section based on the inputed section id
            
            \param		section 	<str>
        """
        found = False
        for i in range(self.uiPluginsTREE.topLevelItemCount()):
            item = self.uiPluginsTREE.topLevelItem(i)
            for c in range(item.childCount()):
                child = item.child(c)
                if child.section().uniqueName() == section:
                    self.uiPluginsTREE.setCurrentItem(child)
                    found = True
                    break
            if found:
                break

    @staticmethod
    def edit(configSet, parent=None, defaultSection=''):
        """ 
            \remarks 	creates a modal config dialog using the specified plugins 
            \param		configSet	<blurdev.gui.dialogs.configdialog.ConfigSet>
        """
        dialog = ConfigDialog(parent)
        dialog.setConfigSet(configSet)
        dialog.setCurrentSection(defaultSection)
        return dialog.exec_()
