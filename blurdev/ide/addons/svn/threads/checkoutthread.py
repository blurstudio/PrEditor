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


class CheckoutThread(ActionThread):
    def __init__(self):
        super(CheckoutThread, self).__init__()

        self.setTitle('Update')

        self._url = ''
        self._filepath = ''
        self._recurse = True
        self._revision = pysvn.Revision(pysvn.opt_revision_kind.head)
        self._peg_revision = pysvn.Revision(pysvn.opt_revision_kind.unspecified)
        self._ignore_externals = False

    def filepath(self):
        return self._filepath

    def ignoreExternals(self):
        return self._ignore_externals

    def isRecursive(self):
        return self._recurse

    def pegRevision(self):
        return self._peg_revision

    def revision(self):
        return self._revision

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        if not self.url():
            self.notify({'error': 'No url was specified to checkout from.'})
        elif not self.filepath():
            self.notify({'error': 'No filepath was specified to checkout to.'})

        client.checkout(
            self.url(),
            self.filepath(),
            self.isRecursive(),
            self.revision(),
            self.pegRevision(),
            self.ignoreExternals(),
        )

    def setFilepath(self, filepath):
        self._filepath = str(filepath)

    def setIgnoreExternals(self, state):
        self._ignore_externals = state

    def setPegRevision(self, revision):
        self._peg_revision = revision

    def setRecursive(self, state):
        self._recurse = state

    def setRevision(self, revision):
        self._revision = revision

    def setUrl(self, url):
        self._url = str(url)

    def url(self):
        return self._url
