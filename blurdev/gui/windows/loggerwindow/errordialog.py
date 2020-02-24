import os
import blurdev
import traceback
import getpass

from blurdev.gui import Dialog
from Qt.QtCore import Qt
from Qt.QtGui import QPixmap
from Qt.QtWidgets import QDialog
from redminelib.exceptions import ImpersonateError
from blurdev.gui.windows.loggerwindow.redmine_login_dialog import RedmineLoginDialog
from blurdev.gui.icon_factory import IconFactory
import traceback


class ErrorDialog(Dialog):

    _iconFactory = IconFactory().customize(
        icon_class='StyledIcon', finders=['library-icons.google']
    )


class ErrorDialog(Dialog):
    def __init__(self, parent):
        super(ErrorDialog, self).__init__(parent)

        blurdev.gui.loadUi(__file__, self)

        self.parent_ = parent
        self.requestPimpPID = None
        self.setWindowTitle('Error Occurred')
        self.errorLabel.setTextFormat(Qt.RichText)
        self.iconLabel.setPixmap(
            QPixmap(
                os.path.join(
                    os.path.dirname(blurdev.__file__),
                    'resource',
                    'img',
                    'warning-big.png',
                )
            ).scaledToHeight(64, Qt.SmoothTransformation)
        )

        self.loggerButton.clicked.connect(self.showLogger)
        self.requestButton.clicked.connect(self.submitRequest)
        self.ignoreButton.clicked.connect(self.close)

    def setText(self, exc_info):
        from console import ConsoleEdit

        self.traceback_msg = "".join(traceback.format_exception(*exc_info))
        msg = 'The following error has occurred:<br><br><font color=%(color)s>%(text)s</font>'
        self.errorLabel.setText(
            msg
            % {
                'text': self.traceback_msg.split('\n')[-2],
                'color': ConsoleEdit._errorMessageColor.name(),
            }
        )

    def showLogger(self):
        inst = blurdev.gui.windows.loggerwindow.LoggerWindow.instance()
        inst.show()
        self.close()

    def submitRequest(self):
        from blurdev.utils.errorEmail import buildErrorMessage

        subject, description = buildErrorMessage(self.traceback_msg, fmt='textile')
        subject = self.traceback_msg.split('\n')[-2]
        from blurdev.actions.create_redmine_issue import CreateRedmineIssue

        kwargs = {
            'subject': subject,
            'description': description,
            'screenshot': True,
            'username': getpass.getuser(),
        }

        # Tryin a first connection impersonating the current user.
        try:
            CreateRedmineIssue(**kwargs)()

        # If that failed, we will use a dialog to prompt for credentials.
        except ImpersonateError:
            dialog = RedmineLoginDialog(parent=self)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                kwargs.update(
                    {
                        'username': dialog.username(),
                        'password': dialog.password(),
                        'redmine': dialog.redmine(),
                    }
                )

                # The dialog can only return a successful connection.
                CreateRedmineIssue(**kwargs)()
            elif result == QDialog.Rejected:
                return
        self.close()
