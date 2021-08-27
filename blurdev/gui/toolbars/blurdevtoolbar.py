from __future__ import absolute_import
import blurdev
from Qt.QtCore import Qt, QRect, QSize
from Qt.QtWidgets import QToolBar


class BlurdevToolbar(QToolBar):
    """A base class used to add QToolBar's to applications.

    This class is able to record and restore preferences and supports instancing.
    All toolbars used by the blurdev.toolbars entry point should use this as a base
    class, or implement the required methods [recordSettings, restoreSettings,
    instance, instanceShutdown, shutdown]. When subclassing at minimum you should
    customize the ``_name`` class property.
    """

    _instance = None
    _name = 'Blurdev'
    _default_toolbar_area = Qt.RightToolBarArea

    def __init__(self, parent):
        super(BlurdevToolbar, self).__init__(parent)
        self.setWindowTitle(self._name)
        self.setObjectName(self.windowTitle().lower().replace(' ', '_'))

        if blurdev.core.isMfcApp() or not hasattr(self.parent(), 'addToolBar'):
            # if this is not a Qt app, we need to make the toolbar a "dialog"
            self.setWindowFlags(Qt.Tool)

        self._iconsSize = 32
        self.restoreSettings()
        self.setIconSize(QSize(self._iconsSize, self._iconsSize))

    @classmethod
    def name(cls):
        """Returns the nice name of this toolbar."""
        return cls._name

    def preferences(self):
        return blurdev.prefs.find('blurdev/toolbar_{}'.format(self.objectName()))

    def setIconsSize(self, size):
        self._iconsSize = size
        self.setIconSize(QSize(size, size))

    def recordSettings(self, save=True, gui=True):
        """Records settings to be used for another session.

        Args:
            save (bool, optional): Save the settings. This is mostly used by sub-classes
                that need to add extra properties to the preferences.
            gui (bool, optional): Used by some cores to prevent saving some prefs.
                See :py:meth:`blurdev.cores.nukecore.NukeCore.eventFilter`.

        Returns:
            blurdev.prefs.Pref: The preference object. If save is False, you will
                need to call save on it.
        """
        pref = self.preferences()
        pref.recordProperty('icons_size', self._iconsSize)
        if gui:
            pref.recordProperty('isVisible', self.isVisible())
            if blurdev.core.isMfcApp() or not hasattr(self.parent(), 'addToolBar'):
                # If not using a proper Qt application store the position
                pref.recordProperty('geometry', self.geometry())
            else:
                # Otherwise record the toolbar area. If the toolbar is floating
                # the application will need to restore the settings.
                # blurdev.core for most dcc's is set up to handle restoring this
                # info. Nuke and Houdini are the exceptions.
                pref.recordProperty('toolBarArea', int(self.parent().toolBarArea(self)))
        if save:
            pref.save()
        return pref

    def restoreSettings(self):
        """restores settings that were saved by a previous session"""
        pref = self.preferences()
        self._iconsSize = pref.restoreProperty('icons_size', 32)
        if blurdev.core.isMfcApp() or not hasattr(self.parent(), 'addToolBar'):
            geometry = pref.restoreProperty('geometry', QRect())
            if geometry and not geometry.isNull():
                self.setGeometry(geometry)
        else:
            toolBarArea = pref.restoreProperty(
                'toolBarArea', self._default_toolbar_area
            )
            self.parent().addToolBar(toolBarArea, self)
        self.setVisible(pref.restoreProperty('isVisible', False))

    def shutdown(self):
        """If this item is the class instance properly close it and remove it
        from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == self._instance:
            self._instance = None
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            self.close()

    @classmethod
    def instance(cls, parent=None):
        """Create a instance of this class or return the previously created one

        Args:
            parent (QWidget, optional): If this is the first time this function
                is called a new instance is created and this will be its parent

        Returns:
            BlurdevToolbar: The instance of this toolbar.
        """
        if not cls._instance:
            instance = cls(parent=parent)
            instance.setAttribute(Qt.WA_DeleteOnClose, False)
            cls._instance = instance
        return cls._instance

    @classmethod
    def instanceRecordSettings(cls, save=True, gui=True):
        """Only if a instance is created, call recordSettings on it.

        Args:
            save (bool, optional): Only save the prefs if True(the default).
            gui (bool, optional): Used by some cores to prevent saving some prefs.
                See :py:meth:`blurdev.cores.nukecore.NukeCore.eventFilter`.

        Returns:
            pref or None: Returns None if a instance was not created, otherwise
                returns the pref object returned by recordSettings.
        """
        if cls._instance:
            return cls._instance.recordSettings(save=save, gui=gui)

    @classmethod
    def instanceShutdown(cls):
        """Faster way to shutdown the instance of BlurdevToolbar if it was not used.

        Returns:
            bool: Shutdown was required
        """
        instance = cls._instance
        if instance:
            instance.shutdown()
            cls._instance = None
            return True
        return False
