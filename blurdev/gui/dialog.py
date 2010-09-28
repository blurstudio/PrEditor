##
# 	\namespace	blurdev.gui.dialog
#
# 	\remarks	Defines the main Dialog instance for this system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		12/05/08
#

from PyQt4.QtGui import QDialog


class Dialog(QDialog):
    def __init__(self, parent=None, flags=0):
        import blurdev

        # if there is no root, create
        if not parent:
            if blurdev.core.isMfcApp():
                from winwidget import WinWidget

                parent = WinWidget.newInstance(blurdev.core.hwnd())
            else:
                parent = blurdev.core.rootWindow()

        # create a QDialog
        if flags:
            QDialog.__init__(self, parent, flags)
        else:
            QDialog.__init__(self, parent)

        # set the delete attribute to clean up the window once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)

        # set this property to true to properly handle tracking events to control keyboard overrides
        self.setMouseTracking(True)

    def closeEvent(self, event):
        QDialog.closeEvent(self, event)

        # uncache the win widget if necessary
        from PyQt4.QtCore import Qt

        if self.testAttribute(Qt.WA_DeleteOnClose):
            if self.parent().inherits('QWinWidget'):
                from winwidget import WinWidget

                WinWidget.uncache(self.parent())

    def exec_(self):
        # do not use the DeleteOnClose attribute when executing a dialog as often times a user will be accessing
        # information from the dialog instance after it closes.  This function properly transfers ownership of the
        # dialog instance back to Python anyway
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # execute the dialog
        return QDialog.exec_(self)
