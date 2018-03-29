##
# 	\namespace	blurdev.gui.wizard
#
# 	\remarks	Defines the main Wizard instance for this system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		12/05/08
#

from Qt.QtGui import QPixmap
from Qt.QtWidgets import QWizard
from Qt.QtCore import Qt


class Wizard(QWizard):
    """ Provides a QWizard class that works inside and outside of DCC's.
    """

    def __init__(self, parent=None, flags=0):
        import blurdev

        # if there is no root, create
        if not parent:
            if blurdev.core.isMfcApp():
                from .winwidget import WinWidget

                parent = WinWidget.newInstance(blurdev.core.hwnd())
            else:
                parent = blurdev.core.rootWindow()

        # create a QWizard
        if flags:
            QWizard.__init__(self, parent, flags)
        else:
            QWizard.__init__(self, parent)

        # set the delete attribute to clean up the window once it is closed
        self.setAttribute(Qt.WA_DeleteOnClose)

        # set this property to true to properly handle tracking events to control keyboard overrides
        self.setMouseTracking(True)

        self.initWizardStyle()

    def initWizardStyle(self):
        """ Create the QWizard style, and calls initWizardPages.
        """
        # set the window style
        self.setWizardStyle(QWizard.MacStyle)

        import blurdev

        self.setPixmap(
            QWizard.BackgroundPixmap, QPixmap(blurdev.resourcePath('img/watermark.png'))
        )
        self.initWizardPages()

    def initWizardPages(self):
        """ Allows the user to define the pages that are going to be used for this wizard.
        """
        pass

    def closeEvent(self, event):
        # ensure this object gets deleted
        wwidget = None
        if self.testAttribute(Qt.WA_DeleteOnClose):
            # collect the win widget to uncache it
            if self.parent() and self.parent().inherits('QWinWidget'):
                wwidget = self.parent()

        QWizard.closeEvent(self, event)

        # uncache the win widget if necessary
        if wwidget:
            from .winwidget import WinWidget

            WinWidget.uncache(wwidget)

    def exec_(self):
        # do not use the DeleteOnClose attribute when executing a wizard as often times a user will
        # be accessing information from the wizard instance after it closes.  This function
        # properly transfers ownership of the wizard instance back to Python anyway
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # execute the wizard
        return QWizard.exec_(self)

    @classmethod
    def runWizard(cls, parent=None):
        """ Executes the wizard and returns True if a return value was returned.

        Args:
            parent (QWidget or None, optional): Parent the widiget to this object.

        Returns:
            bool: If a value was returned by the .exec_() call True is returned.
        """
        if cls(parent).exec_():
            return True
        return False
