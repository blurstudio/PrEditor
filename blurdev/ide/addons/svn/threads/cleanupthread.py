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


class CleanupThread(ActionThread):
    def __init__(self):
        super(CleanupThread, self).__init__()

        self.setTitle('Cleanup')

        self._filepath = ''

    def filepath(self):
        return self._filepath

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        client.cleanup(self._filepath)
        self.notify(
            {'action': 'Completed', 'path': 'Cleanup command completed successfully.'}
        )

    def setFilepath(self, filepath):
        self._filepath = filepath
