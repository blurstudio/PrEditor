##
# 	\namespace	blurdev.gui.window
#
# 	\remarks	Defines the main Window instance for this system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		12/05/08
#

from PyQt4.QtGui import QMainWindow


class Window(QMainWindow):
    _instance = None

    @classmethod
    def instance(cls, parent=None):
        """
            :remarks	If you only want to have one instance of a window, use this method instead of creating a new window.
                        It will only create a new instance of the class if the class variable _instance is none.
            :param		parent	<QWidget>||None		The parent widget
            :return		<Window>
        """
        if not cls._instance:
            cls._instance = cls(parent=parent)
        return cls._instance

    def __init__(self, parent=None, flags=0):

        import blurdev

        # if there is no root, create
        if not parent:
            if blurdev.core.isMfcApp():
                from winwidget import WinWidget

                parent = WinWidget.newInstance(blurdev.core.hwnd())
            else:
                parent = blurdev.core.rootWindow()

        # create a QMainWindow
        if flags:
            QMainWindow.__init__(self, parent, flags)
        else:
            QMainWindow.__init__(self, parent)

        # use the default palette
        palette = blurdev.core.defaultPalette()
        if palette:
            self.setPalette(palette)

        # set the delete attribute to clean up the window once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)

    def closeEvent(self, event):
        from PyQt4.QtCore import Qt

        # ensure this object gets deleted
        wwidget = None
        if self.testAttribute(Qt.WA_DeleteOnClose):
            # collect the win widget to uncache it
            if self.parent() and self.parent().inherits('QWinWidget'):
                wwidget = self.parent()

        QMainWindow.closeEvent(self, event)

        # uncache the win widget if necessary
        if wwidget:
            from winwidget import WinWidget

            WinWidget.uncache(wwidget)
