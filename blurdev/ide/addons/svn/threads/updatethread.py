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
        client.update(self._filepath)

    def setFilepath(self, filepath):
        self._filepath = filepath
