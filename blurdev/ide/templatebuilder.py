##
# 	\namespace	blurdev.ide.templatebuilder
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from blurdev.gui import Dialog


class TemplateBuilder(Dialog):
    def __init__(self):
        Dialog.__init__(self)

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # load the plugins
        from blurdev.ide import plugins

        plugins.load()

        from pluginitem import PluginItem

        for plugin in plugins.plugins():
            self.uiPluginTREE.addTopLevelItem(PluginItem(plugin))

        # create connections
        from PyQt4.QtCore import QDir

        self.uiCreateBTN.clicked.connect(self.commit)
        self.uiExitBTN.clicked.connect(self.close)
        self.uiPluginTREE.itemSelectionChanged.connect(self.refresh)
        self.uiWorkingPathTXT.textChanged.connect(QDir.setCurrent)
        self.uiWorkingPathBTN.clicked.connect(self.pickPath)

        # set the current working path
        from blurdev.tools import ToolsEnvironment

        self.uiWorkingPathTXT.setText(ToolsEnvironment.activeEnvironment().path())

    def commit(self):
        if self.uiPluginAREA.widget():
            self.uiPluginAREA.widget().commit()

    def refresh(self):
        item = self.uiPluginTREE.currentItem()
        if item:
            # remove the current widget
            widget = self.uiPluginAREA.takeWidget()
            if widget:
                widget.deleteLater()

            # insert this plugins widget
            self.uiPluginAREA.setWidget(item.plugin().widgetFor(self))

    def pickPath(self):
        from PyQt4.QtGui import QFileDialog

        path = QFileDialog.getExistingDirectory()
        if path:
            self.uiWorkingPathTXT.setText(path)

    def setWorkingPath(self, path):
        self.uiWorkingPathTXT.setText(path)

    def workingPath(self):
        return self.uiWorkingPathTXT.text()

    @staticmethod
    def createTemplate():
        TemplateBuilder().show()
