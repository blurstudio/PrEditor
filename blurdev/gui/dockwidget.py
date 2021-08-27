##
# 	\namespace	blurdev.gui.window
#
# 	\remarks	Defines the main DockWidget instance for this system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		12/05/08
#

from __future__ import absolute_import
from Qt.QtWidgets import QDockWidget
from Qt.QtCore import Qt


class DockWidget(QDockWidget):
    _instance = None

    @classmethod
    def instance(cls, parent=None):
        """If you only want to have one instance of a DockWidget, use this
                    method instead of creating a new DockWidget. It will only create
                    a new instance of the class if the class variable _instance is
                    none.

        Args:
            parent (QWidget, optional): The parent widget

        Returns:
            DockWidget:
        """
        if not cls._instance:
            import blurdev

            cls._instance = cls(parent=parent)
            # protect the memory
            cls._instance.setAttribute(Qt.WA_DeleteOnClose, False)
            # but make sure that if we reload the environment, everything gets deleted
            # properly
            blurdev.core.aboutToClearPaths.connect(cls._instance.shutdown)
        return cls._instance

    def __init__(self, parent=None, flags=0):
        import blurdev

        # if there is no root, create
        if not parent:
            parent = blurdev.core.rootWindow()

        # create a QDockWidget
        if flags:
            super(DockWidget, self).__init__(parent, flags)
        else:
            super(DockWidget, self).__init__(parent)

        # INFO
        #
        # As far as we can tell, the purpose for this class is keeping live references
        # to the subclasses so they don't get garbage collected, all while getting
        # around having to actively maintain a list of running dialogs.
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
        # this causes any subclasses to stick around in memory even when the DockWidget
        # is closed. So you also have to manually set WA_DeleteOnClose to True in the
        # sub-classed .closeEvent() method before you call super()
        #
        # It is completely possible to write some code that would automatically handle
        # this, and it is CERTAINLY something we can/will be doing in the future, but
        # for now we're not quite sure how that would affect the production tools.
        # Technically this is a problem, but there are currently no consequences from an
        # artist standpoint because we have more than enough memory to hold all those
        # dead dialogs

        # set the delete attribute to clean up the DockWidget once it is closed
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        # If this value is set to True the DockWidget will listen for
        # blurdev.core.aboutToClearPaths and call shutdown on the DockWidget.
        self.aboutToClearPathsEnabled = True

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
        super(DockWidget, self).closeEvent(event)

        # only disconnect here if deleting on close
        if self.aboutToClearPathsEnabled and self.testAttribute(Qt.WA_DeleteOnClose):
            import blurdev

            try:
                blurdev.core.aboutToClearPaths.disconnect(self.shutdown)
            except TypeError:
                pass

    def showEvent(self, event):
        # listen for aboutToClearPaths signal if requested
        # but only connect here if deleting on close
        if self.aboutToClearPathsEnabled and self.testAttribute(Qt.WA_DeleteOnClose):
            import blurdev

            blurdev.core.aboutToClearPaths.connect(self.shutdown)
        super(DockWidget, self).showEvent(event)

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
            import blurdev

            cls._instance = None
            blurdev.core.aboutToClearPaths.disconnect(this.shutdown)
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
