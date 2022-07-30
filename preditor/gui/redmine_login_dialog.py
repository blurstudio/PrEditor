from __future__ import absolute_import

import os

from Qt.QtWidgets import QDialog
from redminelib import Redmine
from redminelib.exceptions import AuthError

from ..gui import loadUi


class RedmineLoginDialog(QDialog):
    def __init__(self, parent=None, redmineUrl=None):
        super(RedmineLoginDialog, self).__init__(parent)
        loadUi(__file__, self)
        self._redmineUrl = redmineUrl or os.environ.get(
            'BDEV_REDMINE_URL', 'https://redmine.blur.com'
        )
        self.uiDialogButtonBox.rejected.connect(self.reject)
        self._redmine = None
        self._username = ''
        self._password = ''

    def accept(self):
        self._username = self.uiUsernameLineEdit.text()
        self._password = self.uiPasswordLineEdit.text()
        try:
            self._redmine = Redmine(
                self._redmineUrl,
                username=self._username,
                password=self._password,
            )
            # Forces the connection and potential AuthError.
            users = self._redmine.user.all().values_list()
            next(users)
            return super(RedmineLoginDialog, self).accept()
        except AuthError:
            self.uiPromptLabel.setStyleSheet("QLabel {color : red;}")
            self.uiPromptLabel.setText('Invalid Redmine credentials. Try again.')

    def password(self):
        """The password input by the user upon acceptance.

        Returns:
            str: The password.
        """
        return self._password

    def username(self):
        """The username input by the user upon acceptance.

        Returns:
            str: The username.
        """
        return self._username

    def redmine(self):
        """The Redmine connection object upon succesful acceptance.

        Returns:
            redminelib.Redmine: Redmine connection object.
        """
        return self._redmine
