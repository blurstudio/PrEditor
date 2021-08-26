##
# 	\namespace	[FILENAME]
#
# 	\remarks	[ADD REMARKS]
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		09/27/10
#

from __future__ import absolute_import
from Qt.QtWinMigrate import QWinWidget

# have to wrap in a python class or the memory management will not work properly for
# QWinWidgets


class WinWidget(QWinWidget):
    cache = []

    @staticmethod
    def newInstance(hwnd):
        import blurdev

        out = WinWidget(hwnd)
        # QWinWidget's showCentered doesn't work. In fact it appears to be working as it
        # was programmed, but I wonder if the QDialog auto center no longer works with a
        # width and height of zero.
        geo = blurdev.core.mainWindowGeometry()
        if geo.isValid():
            out.setGeometry(geo)
        else:
            out.showCentered()

        import sip

        sip.transferback(out)

        WinWidget.cache.append(out)

        return out

    @staticmethod
    def uncache(widget):
        if widget in WinWidget.cache:
            WinWidget.cache.remove(widget)
