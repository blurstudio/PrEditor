from __future__ import absolute_import

import logging
import os

import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QApplication

from .. import resourcePath, settings

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
        self._app_has_exec = False

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
        self.app.setWindowIcon(QIcon(resourcePath('img/python_logger.png')))
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
    def set_app_id(cls, app_id="PrEditor"):
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
        if self.app and not self._app_has_exec:
            self._app_has_exec = True
            self.app.exec_()
