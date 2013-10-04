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
from PyQt4.QtCore import Qt


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
            # protect the memory
            cls._instance.setAttribute(Qt.WA_DeleteOnClose, False)
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
        self.setAttribute(Qt.WA_DeleteOnClose)
        # If this value is set to False calling setGeometry on this window will not adjust the
        # geometry to ensure the window is on a valid screen.
        self.checkScreenGeo = True
        # If this value is set to True the window will listen for blurdev.core.aboutToClearPaths and
        # call shutdown on the window.
        self.aboutToClearPathsEnabled = True
        # attempt to set the dialog icon
        import os
        import sys
        from PyQt4.QtGui import QIcon

        try:
            path = blurdev.relativePath(
                os.path.abspath(sys.modules[self.__class__.__module__].__file__),
                'img/icon.png',
            )
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
        except AttributeError:
            pass

    def closeEvent(self, event):
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
        if self.aboutToClearPathsEnabled:
            import blurdev

            blurdev.core.aboutToClearPaths.disconnect(self.shutdown)

    def setGeometry(self, *args):
        """
        Sets the window's geometry, It will also check if the geometry is visible on any monitors. If it is not it will move the
        window so it is visible. This can be disabled by setting self.checkScreenGeo to False
        """
        super(Window, self).setGeometry(*args)
        if self.checkScreenGeo:
            import blurdev

            blurdev.ensureWindowIsVisible(self)

    def showEvent(self, event):
        # listen for aboutToClearPaths signal if requested
        if self.aboutToClearPathsEnabled:
            import blurdev

            blurdev.core.aboutToClearPaths.connect(self.shutdown)
        super(Window, self).showEvent(event)

    def shutdown(self):
        """
        If this item is the class instance properly close it and remove it from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == Window._instance:
            Window._instance = None
            self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.close()
