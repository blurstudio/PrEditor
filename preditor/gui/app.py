from __future__ import absolute_import

import logging
import os

import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QApplication, QDialog, QMainWindow, QSplashScreen

from .. import DEFAULT_CORE_NAME, resourcePath, settings

logger = logging.getLogger(__name__)


class App(object):
    """Used to create and configure the QApplication instance.

    Args:
        name (str, optional): Set the QApplication application name to this value.
        args (list, optional): The arguments used to instantiate the QApplication
            if one isn't already initialized.
        app (QApplication, optional): An instance of a QApplication to use
            instead of creating one.

    Raises:
        RuntimeError: If DISPLAY is not set when running on linux, or the
            current application isn't a instance of QApplication(ie using a
            QCoreApplication).
    """

    def __init__(self, name=None, args=None, app=None):
        # Used to track if this instance had to create the QApplication or if it
        # was already created
        self.app_created = False
        # If we made the QApplication, did we call exec_ already?
        self.app_has_exec = False

        if app is None:
            app = QApplication.instance()

        self.app = app

        if not self.app:
            # Check for headless environment's
            if settings.OS_TYPE == 'Linux' and os.environ.get('DISPLAY') is None:
                raise RuntimeError(
                    'The PrEditor gui can not run in a headless environment.'
                )

            if args is None:
                args = []
            # create a new application
            if self.app is None:
                args.extend(self.dpi_awareness_args())
                self.app = QApplication(args)
                self.app_created = True
                # If we are creating the application, configure it
                self.configure_standalone()

        if not isinstance(self.app, QApplication):
            raise RuntimeError(
                "PrEditor's gui can only be run using a QApplication instance."
            )

        if self.app and name:
            # If a application name was passed, update the QApplication's
            # application name.
            self.app.setApplicationName(name)
            self.set_app_id(name)

    def configure_standalone(self):
        """Update the QApplication for standalone running. Updates the icon and
        sets its style to default_style_name."""
        self.app.setWindowIcon(QIcon(resourcePath('img/preditor.png')))
        self.app.setStyle(self.default_style_name())

    @staticmethod
    def default_style_name():
        """The default style name used when setting up the QApplication.

        In Qt4 this is Plastique, in Qt5 this is Fusion.
        """

        if Qt.IsPyQt4 or Qt.IsPySide:
            return 'Plastique'
        return 'Fusion'

    @classmethod
    def dpi_awareness_args(cls):
        """On windows sets dpiawareness platform flag to 0 to enable
        per-monitor scaling support in Qt.

        Returns:
            args: Extend the arguments used to intialize the QApplication.
        """
        if settings.OS_TYPE == "Windows" and Qt.IsPyQt5:
            # Make Qt automatically scale based on the monitor the window is
            # currently located.
            return ["--platform", "windows:dpiawareness=0"]
        return []

    @classmethod
    def root_window(cls):
        """Returns the currently active window. Attempts to find the top level
        QMainWindow or QDialog for the current Qt application.
        """
        inst = QApplication.instance()
        if inst:
            root_window = inst.activeWindow()
            # Ignore QSplashScreen's, they should never be considered the root window.
            if isinstance(root_window, QSplashScreen):
                root_window = None

            # If the application does not have focus try to find A top level widget
            # that doesn't have a parent and is a QMainWindow or QDialog
            if root_window is None:
                windows = []
                dialogs = []
                for w in inst.topLevelWidgets():
                    if w.parent() is None:
                        if isinstance(w, QMainWindow):
                            windows.append(w)
                        elif isinstance(w, QDialog):
                            dialogs.append(w)
                if windows:
                    root_window = windows[0]
                elif dialogs:
                    root_window = dialogs[0]

            # grab the root window
            if root_window:
                while root_window.parent():
                    parent = root_window.parent()
                    if isinstance(parent, QSplashScreen):
                        return root_window
                    else:
                        root_window = parent
        return root_window

    @classmethod
    def set_app_id(cls, app_id=DEFAULT_CORE_NAME):
        if settings.OS_TYPE == "Windows":
            # Set the app user model id here not in the window class so it doesn't
            # try to set the app id for applications that already set the app id.
            try:
                from casement.app_id import AppId
            except ImportError:
                logger.debug(
                    "Unable to configure taskbar grouping, use `pip install "
                    "casement` to enable this."
                )
            else:
                AppId.set_for_application(app_id)

    def start(self):
        """Exec's the QApplication if it hasn't already been started."""
        if self.app_created and self.app and not self.app_has_exec:
            self.app_has_exec = True
            self.app.exec_()
