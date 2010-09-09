##
# 	\namespace	trax.gui.dialogs.configdialog.configitem
#
# 	\remarks	Defines the QTreeWidgetItem that contains a pointer to the config plugin
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/20/10
#

from PyQt4.QtGui import QTreeWidgetItem


class ConfigItem(QTreeWidgetItem):
    def __init__(self, name, cls):
        QTreeWidgetItem.__init__(self, [name])

        from PyQt4.QtCore import QSize
        from PyQt4.QtGui import QIcon

        self.setSizeHint(0, QSize(200, 20))

        self._widgetClass = cls

    def widgetClass(self):
        return self._widgetClass
