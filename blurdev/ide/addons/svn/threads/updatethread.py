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


class UpdateThread(ActionThread):
    def __init__(self):
        super(UpdateThread, self).__init__()

        self.setTitle('Update')

        self._filepath = ''

    def filepath(self):
        return self._filepath

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        try:
            client.update(self._filepath)
        except pysvn.ClientError, e:
            self.notify({'error': str(e.message)})
            return
        except:
            self.notify({'error': 'Unknown update error occurred.'})
            return

    def setFilepath(self, filepath):
        self._filepath = filepath
