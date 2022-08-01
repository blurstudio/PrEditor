from __future__ import absolute_import, print_function

import os
import sys

from Qt.QtCore import QDateTime, QObject, Signal
from Qt.QtWidgets import QApplication, QDialog, QMainWindow, QSplashScreen


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to
    be distributed between different pacakges.
    """

    # ----------------------------------------------------------------
    # blurdev signals
    aboutToClearPaths = Signal()  # Emitted before environment is changed or reloaded

    # ----------------------------------------------------------------

    def __init__(self, objectName=None):
        QObject.__init__(self)
        if objectName is None:
            objectName = 'blurdev'
        QObject.setObjectName(self, objectName)

        # create custom properties
        self._logger = None
        self._headless = False
        self._rootWindow = None

        # Paths in this variable will be removed in
        # preditor.osystem.subprocessEnvironment
        self._removeFromPATHEnv = set()

    def aboutBlurdev(self):
        """Useful info about blurdev and its dependencies as a string."""
        from Qt import __binding__, __binding_version__, __qt_version__
        from Qt import __version__ as qtpy_version

        from .. import __file__ as pfile
        from .. import __version__

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

    @property
    def headless(self):
        """If true, no Qt gui elements should be used because python is running a
        QCoreApplication.
        """
        return self._headless

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
            from email.MIMEBase import MIMEBase
            from email.MIMEMultipart import MIMEMultipart
            from email.MIMEText import MIMEText
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
