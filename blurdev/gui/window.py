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
        # make sure there is some parenting
        if not parent:

            # grab the root from the core
            import blurdev

            parent = blurdev.core.rootWindow()

            # if there is no root, create
            if not parent and blurdev.core.isMfcApp():
                from PyQt4.QtWinMigrate import QWinWidget

                # have to store the win widget inside this class or it will be deleted improperly
                self._winWidget = QWinWidget(blurdev.core.hwnd())
                self._winWidget.showCentered()
                parent = self._winWidget

        # create a QMainWindow
        if flags:
            QMainWindow.__init__(self, parent, flags)
        else:
            QMainWindow.__init__(self, parent)

        # set the delete attribute to clean up the window once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)
