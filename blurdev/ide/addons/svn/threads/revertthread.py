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
        try:
            for path in self._filepaths:
                client.revert(path)
        except pysvn._pysvn_2_5.ClientError, e:
            self.notify({'error': str(e.message)})
            return
        except:
            self.notify({'error': 'Unknown revert error occurred.'})
            return

        self.notify(
            {'action': 'Completed', 'path': 'Revert has completed successfully.'}
        )

    def setFilepaths(self, filepaths):
        self._filepaths = filepaths
