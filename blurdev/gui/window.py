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

        import PyQt4.uic, os.path

        PyQt4.uic.loadUi(os.path.split(__file__)[0] + '/palette.ui', self)

        # set the delete attribute to clean up the window once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)

    def closeEvent(self, event):
        QMainWindow.closeEvent(self, event)

        # uncache the win widget if necessary
        from PyQt4.QtCore import Qt

        if self.testAttribute(Qt.WA_DeleteOnClose):
            if self.parent() and self.parent().inherits('QWinWidget'):
                from winwidget import WinWidget

                WinWidget.uncache(self.parent())
