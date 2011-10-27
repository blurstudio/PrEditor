##
# 	\namespace	blurdev.ide.addons.svn.threads
#
# 	\remarks	Contains various threads to be run during the SVN process
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/25/11
#

import pysvn

from blurdev.ide.addons.svn.threads import ActionThread


class RevertThread(ActionThread):
    def __init__(self):
        super(RevertThread, self).__init__()

        self.setTitle('Revert')

        self._filepaths = []

    def filepaths(self):
        return self._filepaths

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        for path in self._filepaths:
            client.revert(path)
        self.notify(
            {'action': 'Completed', 'path': 'Revert has completed successfully.'}
        )

    def setFilepaths(self, filepaths):
        self._filepaths = filepaths