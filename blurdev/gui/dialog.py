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
from PyQt4.QtCore import Qt


class Dialog(QDialog):
    _instance = None

    @classmethod
    def instance(cls, parent=None):
        """
            :remarks	If you only want to have one instance of a dialog, use this method instead of creating a new dialog.
                        It will only create a new instance of the class if the class variable _instance is none.
            :param		parent	<QWidget>||None		The parent widget
            :return		<Dialog>
        """
        if not cls._instance:
            cls._instance = cls(parent=parent)
            # protect the memory
            cls._instance.setAttribute(Qt.WA_DeleteOnClose, False)
        return cls._instance

    def __init__(self, parent=None, flags=Qt.WindowMinMaxButtonsHint):
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
        self.setAttribute(Qt.WA_DeleteOnClose)

        # set this property to true to properly handle tracking events to control keyboard overrides
        self.setMouseTracking(True)

        # If this value is set to False calling setGeometry on this dialog will not adjust the
        # geometry to ensure the dialog is on a valid screen.
        self.checkScreenGeo = True
        # If this value is set to True the dialog will listen for blurdev.core.aboutToClearPaths and
        # call shutdown on the dialog.
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

        QDialog.closeEvent(self, event)

        # uncache the win widget if necessary
        if wwidget:
            from winwidget import WinWidget

            WinWidget.uncache(wwidget)
        if self.aboutToClearPathsEnabled:
            import blurdev

            try:
                blurdev.core.aboutToClearPaths.disconnect(self.shutdown)
            except TypeError:
                pass

    def exec_(self):
        # do not use the DeleteOnClose attribute when executing a dialog as often times a user will be accessing
        # information from the dialog instance after it closes.  This function properly transfers ownership of the
        # dialog instance back to Python anyway

        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # execute the dialog
        return QDialog.exec_(self)

    def setGeometry(self, *args):
        """
        Sets the dialog's geometry, It will also check if the geometry is visible on any monitors. If it is not it will move the
        dialog so it is visible. This can be disabled by setting self.checkScreenGeo to False
        """
        super(Dialog, self).setGeometry(*args)
        if self.checkScreenGeo:
            import blurdev

            blurdev.ensureWindowIsVisible(self)

    def showEvent(self, event):
        # listen for aboutToClearPaths signal if requested
        if self.aboutToClearPathsEnabled:
            import blurdev

            blurdev.core.aboutToClearPaths.connect(self.shutdown)
        super(Dialog, self).showEvent(event)

    def shutdown(self):
        """
        If this item is the class instance properly close it and remove it from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == Dialog._instance:
            Dialog._instance = None
            self.setAttribute(Qt.WA_DeleteOnClose, True)
        try:
            self.close()
        except RuntimeError:
            pass
