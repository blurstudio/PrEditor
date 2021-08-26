import os
import Qt
import getpass
import tempfile
import blurdev.keychain

from redminelib import Redmine
from Qt.QtWidgets import QApplication
from Qt.QtGui import QPixmap
from blurdev.action import Action, Apps, executehook, argproperty
import six


class CreateRedmineIssue(Action):

    """Creates an issue in Redmine site.

    Attributes:

        apiKey (basestring): The API key for the connection. Used "password" is None and
            "redmine" is a URL.

        attachments (list): A list of filenames that should be attached to the issue.
        description (basestring): The issue description.

        password (basestring): The password used to connect. Used when "redmine"
            argument is a URL.

        priority (int): The priority ID for the issue.
            project (basestring): The project ID for the issue.

        redmine (basestring, redminelib.Redmine): Redmine URL or Redmine configured
        object.

        screenshot (bool): Whether a screenshot should be attached to the issue.
            subject (basestring): The subject of the issue.

        username (basestring): User to impersonate. Used when "redmine" argument is a
        URL.

        watchers (basestring): A list of usernames that should watch the issue.
    """

    apiKey = argproperty(
        atype=six.string_types, default=blurdev.keychain.getKey('redmine_api_key')
    )
    attachments = argproperty(atype=list, defaultInstance=True)
    description = argproperty(atype=six.string_types, default='')
    password = argproperty(atype=six.string_types, allowNone=True, default=None)
    priority = argproperty(atype=int, default=14)
    project = argproperty(atype=six.string_types, default='pipeline')
    redmine = argproperty(
        atype=(six.string_types, Redmine),
        default=os.environ.get('BDEV_REDMINE_URL', 'https://redmine.blur.com',),
    )
    screenshot = argproperty(atype=bool, default=False)
    subject = argproperty(atype=six.string_types)
    username = argproperty(atype=six.string_types, default=getpass.getuser())
    watchers = argproperty(atype=list, default=None, allowNone=True)

    @executehook(app=Apps.All)
    def execute(self):
        """Will create an issue in Redmine.

        Raises:
            ImpersonateError: Could not impersonate a user if password not passed.
            AuthError: Could not loging with provided user and password.
        """

        # We support taking a configured Redmine object.
        if isinstance(self.redmine, Redmine):
            redmine = self.redmine
        else:
            # If the password is past we try to login using username password.
            if self.password:
                kwargs = dict(username=str(self.username), password=str(self.password),)
            else:
                # Otherwise we try to impersonate the user.
                kwargs = dict(key=self.apiKey, impersonate=self.username,)
            redmine = (
                self.redmine
                if isinstance(self.redmine, Redmine)
                else Redmine(self.redmine, **kwargs)
            )

        kwargs = {
            'description': self.description,
            'priority_id': self.priority,
            'project_id': self.project,
            'subject': self.subject,
        }

        if self.watchers:
            kwargs.update({'watcher_user_ids': self.watchers})

        if self.screenshot:
            windowId = QApplication.desktop().winId()
            if Qt.IsPyQt5 or Qt.IsPySide2:
                if Qt.IsPyQt5:
                    from PyQt5.QtGui import QScreen
                else:
                    from PySide2.QtGui import QScreen
                screen = QApplication.instance().primaryScreen()
                pixmap = QScreen.grabWindow(screen, windowId)
            else:
                pixmap = QPixmap.grabWindow(windowId)
            tempfilename = os.path.join(tempfile.mkdtemp(), 'screenshot.png')
            pixmap.save(tempfilename, 'png')
            self.attachments.append(tempfilename)

        if self.attachments:
            uploads = []
            for attachment in self.attachments:
                uploads.append(
                    {'path': attachment, 'filename': os.path.basename(attachment)}
                )
            kwargs['uploads'] = uploads

        return redmine.issue.create(**kwargs)
