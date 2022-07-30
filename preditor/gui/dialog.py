from __future__ import absolute_import

from Qt.QtCore import Qt
from Qt.QtWidgets import QDialog

from .. import core, relativePath


class Dialog(QDialog):
    _instance = None

    @classmethod
    def instance(cls, parent=None):
        """If you only want to have one instance of a dialog, use this method instead
        of creating a new dialog. It will only create a new instance of the class if
        the class variable _instance is none.

        Args:
            parent (QWidget, optional):The parent widget

        Returns:
            Dialog:
        """
        if not cls._instance:
            cls._instance = cls(parent=parent)
            # protect the memory
            cls._instance.setAttribute(Qt.WA_DeleteOnClose, False)
            # but make sure that if we reload the environment, everything gets deleted
            # properly
            core.aboutToClearPaths.connect(cls._instance.shutdown)
        return cls._instance

    def __init__(
        self, parent=None, flags=Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
    ):
        # if there is no root, create
        if not parent:
            parent = core.rootWindow()

        # create a QDialog
        if flags:
            QDialog.__init__(self, parent, flags)
        else:
            QDialog.__init__(self, parent)

        # INFO
        #
        # As far as we can tell, the purpose for this class is keeping live
        # references to the subclasses so they don't get garbage collected, all while
        # getting around having to actively maintain a list of running dialogs.
        #
        # Generally, setting WA_DeleteOnClose to False, and keeping the _instance
        # variable around will do the trick for pseudo-singleton dialogs. (created with
        # instance=True)
        #
        # However, for non-instanced dialogs where multiples are allowed, deleteOnClose
        # is set to True and no _instance variable is set.  Because there are no live
        # references to the dialog, it is closed and garbage collected almost
        # immediately in certain programs (xsi, maya).
        #
        # The current workaround is to manually set WA_DeleteOnClose to False, however
        # this causes any subclasses to stick around in memory even when the
        # window/dialog is closed. So you also have to manually set WA_DeleteOnClose to
        # True in the sub-classed .closeEvent() method before you call super()
        #
        # It is completely possible to write some code that would automatically handle
        # this, and it is CERTAINLY something we can/will be doing in the future, but
        # for now we're not quite sure how that would affect the production tools.
        # Technically this is a problem, but there are currently no consequences from an
        # artist standpoint because we have more than enough memory to hold all those
        # dead dialogs

        # set the delete attribute to clean up the window once it is closed
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        # set this property to true to properly handle tracking events to control
        # keyboard overrides
        self.setMouseTracking(True)

        # If this value is set to False calling setGeometry on this dialog will not
        # adjust the geometry to ensure the dialog is on a valid screen.
        self.checkScreenGeo = True
        # If this value is set to True the dialog will listen for
        # core.aboutToClearPaths and call shutdown on the dialog.
        self.aboutToClearPathsEnabled = True
        # attempt to set the dialog icon
        import os
        import sys

        from Qt.QtGui import QIcon

        try:
            path = relativePath(
                os.path.abspath(sys.modules[self.__class__.__module__].__file__),
                'img/icon.png',
            )
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
        except (AttributeError, KeyError):
            pass

    def _shouldDisableAccelerators(self, old, now):
        """Used to enable typing in DCC's that require it(Max 2018).

        Args:
            old (QWidget or None): The QWidget that lost focus.
            new (QWidget or None): The QWidget that gained focus.

        Returns:
            bool: If accelerators should be disabled.
        """
        # By default we always want to disable accelerators.
        return True

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
            from .winwidget import WinWidget

            WinWidget.uncache(wwidget)

        # only disconnect here if deleting on close
        if self.aboutToClearPathsEnabled and self.testAttribute(Qt.WA_DeleteOnClose):
            try:
                core.aboutToClearPaths.disconnect(self.shutdown)
            except TypeError:
                pass

    def exec_(self):
        # do not use the DeleteOnClose attribute when executing a dialog as often times
        # a user will be accessing information from the dialog instance after it closes.
        # This function properly transfers ownership of the dialog instance back to
        # Python anyway

        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # execute the dialog
        return QDialog.exec_(self)

    def setGeometry(self, *args):
        """
        Sets the dialog's geometry, It will also check if the geometry is visible on any
        monitors. If it is not it will move the dialog so it is visible. This can be
        disabled by setting self.checkScreenGeo to False
        """
        super(Dialog, self).setGeometry(*args)
        if self.checkScreenGeo:
            from cute.functions import ensureWindowIsVisible

            ensureWindowIsVisible(self)

    def showEvent(self, event):
        # listen for aboutToClearPaths signal if requested
        # but only connect here if deleting on close
        if self.aboutToClearPathsEnabled and self.testAttribute(Qt.WA_DeleteOnClose):
            core.aboutToClearPaths.connect(self.shutdown)
        super(Dialog, self).showEvent(event)

    def shutdown(self):
        # use a @classmethod to make inheritance magically work
        self._shutdown(self)

    @classmethod
    def _shutdown(cls, this):
        """
        If this item is the class instance properly close it and remove it from memory
        so it can be recreated.
        """
        # allow the global instance to be cleared
        if this == cls._instance:
            cls._instance = None
            if this.aboutToClearPathsEnabled:
                core.aboutToClearPaths.disconnect(this.shutdown)
            this.setAttribute(Qt.WA_DeleteOnClose, True)
        try:
            this.close()
        except RuntimeError:
            pass

    @classmethod
    def instanceShutdown(cls):
        """Call shutdown on this class instance only if the class was instantiated.

        Returns:
            bool: if cls.instance().shutdown() needed to be called.
        """
        instance = cls._instance
        if instance:
            instance.shutdown()
            return True
        return False
