##
# 	\namespace	blurdev.ide.addons.svn.threads
#
# 	\remarks	Contains various threads to be run during the SVN process
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/25/11
#

from blurdev.ide.addons.svn.threads import ActionThread


class CommitThread(ActionThread):
    def __init__(self):
        super(CommitThread, self).__init__()

        self.setTitle('Commit')

        self._filepaths = []
        self._comments = ''

    def comments(self):
        return self._comments

    def filepaths(self):
        return self._filepaths

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        client.checkin(self._filepaths, self._comments)
        self.notify(
            {'action': 'Completed', 'path': 'Commit has completed successfully.'}
        )

    def setComments(self, comments):
        self._comments = comments

    def setFilepaths(self, filepaths):
        self._filepaths = filepaths
