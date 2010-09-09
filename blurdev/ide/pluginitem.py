##
# 	\namespace	blurdev.ide.pluginitem
#
# 	\remarks	The PluginItem class keeps information about a plugin instance as a QTreeWidgetItem
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtGui import QTreeWidgetItem


class PluginItem(QTreeWidgetItem):
    def __init__(self, plugin):
        QTreeWidgetItem.__init__(self)

        self.setIcon(0, plugin.icon())
        self.setText(0, plugin.objectName())

        from PyQt4.QtCore import QSize

        self.setSizeHint(0, QSize(250, 22))

        self._plugin = plugin

    def plugin(self):
        return self._plugin
