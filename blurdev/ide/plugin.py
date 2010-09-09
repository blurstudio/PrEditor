##
# 	\namespace	blurdev.ide.plugin
#
# 	\remarks	The Plugin class defines the common base class that all plugins will inherit from
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtCore import QObject


class Plugin(QObject):
    def __init__(self):
        QObject.__init__(self)

        self._widgetClass = None
        self._iconFile = ''

    def icon(self):
        from PyQt4.QtGui import QIcon

        return QIcon(self.iconFile())

    def iconFile(self):
        return self._iconFile

    def setIconFile(self, iconFile):
        self._iconFile = iconFile

    def widgetFor(self, parent):
        if self._widgetClass:
            return self._widgetClass(parent)
        return None

    def setWidgetClass(self, widgetClass):
        self._widgetClass = widgetClass
