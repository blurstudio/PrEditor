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
        # generate a new win widget to use as the parent item for this window
        inheritPalette = False
        if not parent:
            import blurdev

            parent = blurdev.core.activeWindow()

        # create a QMainWindow
        if flags:
            QMainWindow.__init__(self, parent, flags)
        else:
            QMainWindow.__init__(self, parent)

        # set the delete attribute to clean up the window once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)
