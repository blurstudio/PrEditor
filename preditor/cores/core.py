from __future__ import print_function
from __future__ import absolute_import
import sys
import os

from Qt.QtCore import QDateTime, QObject, Signal
from Qt.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QSplashScreen,
)
import sentry_bootstrap

from .. import settings
from ..utils.error import sentry_before_send_callback


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to
    be distributed between different pacakges.
    """

    # ----------------------------------------------------------------
    # blurdev signals
    aboutToClearPaths = Signal()  # Emitted before environment is changed or reloaded

    # ----------------------------------------------------------------

    def __init__(self, hwnd=0, objectName=None):
        QObject.__init__(self)
        if objectName is None:
            objectName = 'blurdev'
        QObject.setObjectName(self, objectName)

        # create custom properties
        self._hwnd = hwnd
        self._logger = None
        self._headless = False
        self._rootWindow = None

        # Paths in this variable will be removed in
        # preditor.osystem.subprocessEnvironment
        self._removeFromPATHEnv = set()

    def aboutBlurdev(self):
        """Useful info about blurdev and its dependencies as a string."""
        from Qt import (
            __binding__,
            __binding_version__,
            __version__ as qtpy_version,
            __qt_version__,
        )

        from .. import __version__, __file__ as pfile

        msg = [
            'blurdev: {} ({})'.format(__version__, self.objectName()),
            '    {}'.format(os.path.dirname(pfile)),
        ]

        msg.append('Qt: {}'.format(__qt_version__))
        msg.append('    Qt.py: {}, binding: {}'.format(qtpy_version, __binding__))

        try:
            # QtSiteConfig is optional
            import QtSiteConfig

            msg.append('    QtSiteConfig: {}'.format(QtSiteConfig.__version__))
        except (ImportError, AttributeError):
            pass

        # Legacy Qt 4 support
        if __binding__ not in ('PyQt5', 'PySide2'):
            msg.append(
                '    {qt}: {qtver}'.format(qt=__binding__, qtver=__binding_version__)
            )
        # Add info for all Qt5 bindings that have been imported somewhere
        if 'PyQt5.QtCore' in sys.modules:
            msg.append(
                '    PyQt5: {}'.format(sys.modules['PyQt5.QtCore'].PYQT_VERSION_STR)
            )
        if 'PySide2.QtCore' in sys.modules:
            msg.append(
                '    PySide2: {}'.format(sys.modules['PySide2.QtCore'].qVersion())
            )

        # Include the python version info
        msg.append('Python:')
        msg.append('    {}'.format(sys.version))

        return '\n'.join(msg)

    def defaultStyle(self):
        """The default style name used when setting up the QApplication.

        In Qt4 this is Plastique, in Qt5 this is Fusion.
        """
        from Qt import IsPyQt4, IsPySide

        if IsPyQt4 or IsPySide:
            return 'Plastique'
        return 'Fusion'

    def errorCoreText(self):
        """Returns text that is included in the error email for the active core.
        Override in subclasses to provide extra data. If a empty string is returned
        this line will not be shown in the error email.
        """
        return ''

    def shouldReportException(self, exc_type, exc_value, exc_traceback, actions=None):
        """
        Allow core to control how exceptions are handled. Currently being used
        by `BlurExcepthook`, informing which excepthooks should or should not
        be executed.

        Args:
            exc_type (type): exception type class object
            exc_value (Exception): class instance of exception parameter
            exc_traceback (traceback): encapsulation of call stack for exception
            actions (dict, optional): default values for the returned dict. A copy
                of this dict is returned with standard defaults applied.

        Returns:
            dict: Boolean values representing whether to perform excepthook
                action, keyed to the name of the excepthook
        """
        if actions is None:
            actions = {}
        # Create a shallow copy so we don't modify the passed in dict and don't
        # need to use a default value of None
        actions = actions.copy()

        # provide the expected default values
        actions.setdefault('email', True)
        # If blurdev is running headless, there is no way to show a gui prompt
        actions.setdefault('prompt', not self.headless)
        return actions

    def init(self):
        """Initializes the core system"""
        ret = self.initCore()
        return ret

    def initCore(self):
        """Work method to initialize the core system -- breaking the initialization
        apart allows the gui-dependant initialization to be delayed in applications
        where that is necessary by overloading init().
        """
        # initialize sentry client
        sentry_bootstrap.init_sentry(force=True)
        sentry_bootstrap.add_external_callback(sentry_before_send_callback)

        # initialize the application
        app = QApplication.instance()
        output = None

        if not app:
            # create a new application
            from ..cores.application import CoreApplication, Application

            # Check for headless environment's
            if settings.OS_TYPE == 'Linux':
                if os.environ.get('DISPLAY') is None:
                    output = CoreApplication([])
                    self._headless = True
            if output is None:
                output = Application([])

        self.updateApplicationName(output)

        return output

    @property
    def headless(self):
        """If true, no Qt gui elements should be used because python is running a
        QCoreApplication.
        """
        return self._headless

    def hwnd(self):
        if self.objectName() == 'assfreezer':
            return int(self.rootWindow().winId())
        return self._hwnd

    def logger(self, parent=None):
        """Creates and returns the logger instance"""
        from ..gui.loggerwindow import LoggerWindow

        return LoggerWindow.instance(parent)

    def rootWindow(self):
        """
        Returns the currently active window
        """
        if self._rootWindow is not None:
            return self._rootWindow

        if QApplication.instance():
            self._rootWindow = QApplication.instance().activeWindow()
            # Ignore QSplashScreen's, they should never be considered the root window.
            if isinstance(self._rootWindow, QSplashScreen):
                self._rootWindow = None
            # If the application does not have focus try to find A top level widget
            # that doesn't have a parent and is a QMainWindow or QDialog
            if self._rootWindow is None:
                windows = []
                dialogs = []
                for w in QApplication.instance().topLevelWidgets():
                    if w.parent() is None:
                        if isinstance(w, QMainWindow):
                            windows.append(w)
                        elif isinstance(w, QDialog):
                            dialogs.append(w)
                if windows:
                    self._rootWindow = windows[0]
                elif dialogs:
                    self._rootWindow = dialogs[0]

            # grab the root window
            if self._rootWindow:
                while self._rootWindow.parent():
                    parent = self._rootWindow.parent()
                    if isinstance(parent, QSplashScreen):
                        return self._rootWindow
                    else:
                        self._rootWindow = parent
        return self._rootWindow

    def setHwnd(self, hwnd):
        self._hwnd = hwnd

    def emailAddressMd5Hash(self, text, address=None):
        """Turns the text into a md5 string and inserts it in the address.

        This is useful for controlling how messages are threaded into conversations on
        gmail.

        Args:
            text (str): This text will be converted into a md5 hash.

            address (str or None): The md5 hash will be inserted using str.format on the
            "hash" key. If None, it will use the value stored in the BDEV_ERROR_EMAIL
            environment variable.

        Returns:
            str: The formatted address.

        """
        import hashlib

        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        if address is None:
            address = os.environ.get('BDEV_ERROR_EMAIL')
        return address.format(hash=m.hexdigest())

    def sendEmail(
        self, sender, targets, subject, message, attachments=None, refId=None
    ):
        """Sends an email.
        Args:
            sender (str): The source email address.

            targets (str or list): A single email string, or a list of email address(s)
                to send the email to.

            subject (str): The subject of the email.
            message (str): The body of the message. Treated as html
            attachments (list or None): File paths for files to be attached.

            refId (str or None): If not None "X-Entity-Ref-ID" is added to the header
                with this value. For gmail passing a empty string appears to be the same
                as passing real data.
        """
        try:
            from email import Encoders
            from email.MIMEText import MIMEText
            from email.MIMEMultipart import MIMEMultipart
            from email.MIMEBase import MIMEBase
        except ImportError:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase

        import smtplib

        output = MIMEMultipart()
        output['Subject'] = str(subject)
        output['From'] = str(sender)
        if refId is not None:
            output['X-Entity-Ref-ID'] = refId

        # convert to string
        if isinstance(targets, (tuple, list)):
            output['To'] = ', '.join(targets)
        else:
            output['To'] = str(targets)

        output['Date'] = (
            QDateTime.currentDateTime().toUTC().toString('ddd, d MMM yyyy hh:mm:ss')
        )
        output['Content-type'] = 'Multipart/mixed'
        output.preamble = 'This is a multi-part message in MIME format.'
        output.epilogue = ''

        # Build Body
        msgText = MIMEText(str(message), 'html')
        msgText['Content-type'] = 'text/html'

        output.attach(msgText)

        # Include Attachments
        if attachments:
            for a in attachments:
                fp = open(str(a), 'rb')
                txt = MIMEBase('application', 'octet-stream')
                txt.set_payload(fp.read())
                fp.close()

                Encoders.encode_base64(txt)
                txt.add_header(
                    'Content-Disposition',
                    'attachment; filename="%s"' % os.path.basename(a),
                )
                output.attach(txt)

        try:
            smtp = smtplib.SMTP('mail.blur.com', timeout=1)
            # smtp.starttls()
            # smtp.connect(os.environ.get('BDEV_SEND_EMAIL_SERVER', 'mail.blur.com'))
            smtp.sendmail(str(sender), output['To'].split(','), output.as_string())
            smtp.close()
        except Exception:
            # TODO: Proper logging

            import inspect

            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])

            import traceback

            traceback.print_exc()

            print(
                'Module {0} @ {1} failed to send email\n{2}\n{3}\n{4}\n{5}'.format(
                    module.__name__, module.__file__, sender, targets, subject, message
                )
            )

            raise

    def shutdown(self):
        if QApplication.instance():
            QApplication.instance().closeAllWindows()
            QApplication.instance().quit()

    def showLogger(self):
        """
        Creates the python logger and displays it
        """
        logger = self.logger()
        logger.show()
        logger.activateWindow()
        logger.raise_()
        logger.console().setFocus()

    def updateApplicationName(self, application=None, name=None):
        """Sets the application name based on the environment.

        Args:
            application (
                Qt.QtCore.QCoreApplication or Qt.QtWidgets.QApplication, optional):
                The Qt application that should have its name set to match the
                BDEV_APPLICATION_NAME environment variable. This env variable is
                removed by calling this function so it is not passed to child
                subprocesses. If None is provided, then preditor.application is used.

        Returns:
            bool: If the application name was set. This could be because the
                application was None.
        """
        if application is None:
            from .. import application
        if application is None:
            return False
        # Remove the BDEV_APPLICATION_NAME variable if defined so it is not
        # passed to child processes.
        appName = os.environ.pop('BDEV_APPLICATION_NAME', None)
        if name is not None:
            # If a name was passed in, use it instead of the env variable, but still
            # remove the env variable so it doesn't affect child subprocesses.
            appName = name
        if application and appName:
            # This name can be used in filePaths, so remove the invalid separator
            # used by older tools.
            appName = appName.replace('::', '_')
            # If a application name was passed, update the QApplication's
            # application name.
            application.setApplicationName(appName)
            return True
        return False

    def uuid(self):
        """Application specific unique identifier

        Returns:
            None:
        """
        return None
