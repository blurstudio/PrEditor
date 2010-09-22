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

        # create a QDialog
        if flags:
            QDialog.__init__(self, parent, flags)
        else:
            QDialog.__init__(self, parent)

        # set the delete attribute to remove the dialog properly once it is closed
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose)

        # set this property to true to properly handle tracking events to control keyboard overrides
        self.setMouseTracking(True)

    def exec_(self):
        # do not use the DeleteOnClose attribute when executing a dialog as often times a user will be accessing
        # information from the dialog instance after it closes.  This function properly transfers ownership of the
        # dialog instance back to Python anyway
        from PyQt4.QtCore import Qt

        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # execute the dialog
        return QDialog.exec_(self)
