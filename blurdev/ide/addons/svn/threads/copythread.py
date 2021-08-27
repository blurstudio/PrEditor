##
# 	\namespace	blurdev.ide.addons.svn.threads
#
# 	\remarks	Contains various threads to be run during the SVN process
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/25/11
#

from __future__ import absolute_import
import pysvn

from blurdev.ide.addons.svn.threads import ActionThread


class CopyThread(ActionThread):
    def __init__(self):
        super(CopyThread, self).__init__()

        self.setTitle('Copy')

        self._source = ''
        self._target = ''
        self._revision = pysvn.Revision(pysvn.opt_revision_kind.head)
        self._comments = ''

    def comments(self):
        return self._comments

    def connectClient(self, client):
        super(CopyThread, self).connectClient(client)

        client.callback_get_log_message = self.message

    def message(self):
        return True, self._comments

    def revision(self):
        return self._revision

    def runClient(self, client):
        """Check-in the information to the client

        Args:
            client (pysvn.Client):
        """
        client.copy(self._source, self._target, self._revision)
        self.notify({'action': 'Completed', 'path': 'Copy has completed successfully.'})

    def setComments(self, comments):
        self._comments = comments

    def setRevision(self, revision):
        self._revision = revision

    def setSource(self, source):
        self._source = source

    def setTarget(self, target):
        self._target = target

    def source(self):
        return self._source

    def target(self):
        return self._target
