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


class ConfigDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)

        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self.uiPluginsTREE.header().setVisible(False)

        # create connections
        self.uiExitBTN.clicked.connect(self.reject)
        self.uiSaveExitBTN.clicked.connect(self.accept)
        self.uiResetBTN.clicked.connect(self.reset)
        self.uiSaveBTN.clicked.connect(self.commit)
        self.uiPluginsTREE.itemSelectionChanged.connect(self.refreshWidget)

    def accept(self):
        """ commits the config information and then closes down """
        self.commit()
        Dialog.accept(self)

    def checkForSave(self):
        """ tries to run the active config widget's checkForSave method, if it exists """
        widget = self.uiWidgetAREA.widget()

        if widget:
            try:
                return widget.checkForSave()
            except:
                self.logMissingMethod('checkForSave')

        return True

    def commit(self):
        """ tries to run the active config widget's commit method, if it exists """
        widget = self.uiWidgetAREA.widget()

        if widget:
            try:
                return widget.commit()
            except:
                self.logMissingMethod('commit')

        return True

    def setWidgets(self, classes):
        """ 
            \remarks	sets the plugins to be displayed by this system 
            \param		classes		<dict> { <str> groupName: <dict> { <str> name: <QWidget> class, .. }, .. }
        """
        from PyQt4.QtCore import QSize
        from PyQt4.QtGui import QTreeWidgetItem

        from configitem import ConfigItem

        # clear the tree
        self.uiPluginsTREE.clear()

        # load the tree
        keys = classes.keys()
        keys.sort()

        for key in keys:
            # create the group item
            grpItem = QTreeWidgetItem([key])
            font = grpItem.font(0)
            font.setBold(True)

            grpItem.setFont(0, font)
            grpItem.setSizeHint(0, QSize(200, 20))

            plugs = classes[key]
            subkeys = plugs.keys()
            subkeys.sort()

            for subkey in subkeys:
                grpItem.addChild(ConfigItem(subkey, plugs[subkey]))

            self.uiPluginsTREE.addTopLevelItem(grpItem)
            grpItem.setExpanded(True)

    def logMissingMethod(self, method):
        """ debugs the system and displays the missing method name """
        from blurdev import debug

        item = self.uiPluginsTREE.currentItem()
        if item:
            debug.debugObject(
                self.logMissingMethod,
                '%s not implemented for %s plugin' % (method, item.text(0)),
            )
        else:
            debug.debugObject(
                self.logMissingMethod,
                '%s not implemented for missing plugin' % (method),
            )

    def reject(self):
        """ checks this system to make sure the current widget has been saved before exiting """
        if self.checkForSave():
            Dialog.reject(self)

    def refreshWidget(self):
        """ reloads this dialog with the current plugin instance """
        from configitem import ConfigItem
        from PyQt4.QtGui import QWidget

        self.uiPluginsTREE.blockSignals(True)

        item = self.uiPluginsTREE.currentItem()

        if isinstance(item, ConfigItem):
            widget = self.uiWidgetAREA.widget()

            # clear out an old widget
            if widget and type(widget) != QWidget:
                if not self.checkForSave():
                    self.uiPluginsTREE.clearSelection()
                    self.selectPlugin(widget.objectName())
                    self.uiPluginsTREE.blockSignals(False)
                    return False

                widget.close()
                widget.deleteLater()
                self.uiWidgetAREA.setWidget(None)

            # create the new widgets plugin
            widget = item.widgetClass()(self)
            self.uiWidgetAREA.setWidget(widget)

        self.uiPluginsTREE.blockSignals(False)
        return True

    def reset(self):
        """ resets the data for the current widget """
        widget = self.uiWidgetAREA.widget()

        if widget:
            try:
                return widget.reset()
            except:
                self.logMissingMethod('reset')

        return True

    def selectPlugin(self, name):
        """ selects the widget item whose name matches the inputed name """
        self.uiPluginsTREE.blockSignals(True)

        for i in range(self.uiPluginsTREE.topLevelItemCount()):
            item = self.uiPluginsTREE.topLevelItem(i)
            for c in range(item.childCount()):
                pitem = item.child(c)
                if pitem.text(0) == name:
                    pitem.setSelected(True)
                    self.uiPluginsTREE.blockSignals(False)
                    return True

        self.uiPluginsTREE.blockSignals(False)
        return False

    @staticmethod
    def edit(classes):
        """ 
            \remarks 	creates a modal config dialog using the specified plugins 
            \param		classes		<dict> { <str> name: <QWidget> class, .. }
        """
        dialog = ConfigDialog(None)
        dialog.setWidgets(classes)
        return dialog.exec_()
