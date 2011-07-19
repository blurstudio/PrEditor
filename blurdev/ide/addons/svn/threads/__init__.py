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
import blurdev

from PyQt4.QtCore import QThread, pyqtSignal

from blurdev.decorators import abstractmethod
from blurdev.ide.addons import svn


class DataCollectionThread(QThread):
    def __init__(self):
        QThread.__init__(self)

        self._filepath = ''
        self._results = []

    def results(self):
        return self._results

    def run(self):
        # create expressions
        client = pysvn.Client()
        self._results = client.status(self._filepath)

    def setFilepath(self, filepath):
        self._filepath = filepath


class ActionThread(QThread):
    """
        \remarks	this base class is to be used with the SvnActionDialog
                    to manage various SVN actions that will need to occur
    """

    updated = pyqtSignal(str, str, str, int)

    def __init__(self):
        super(ActionThread, self).__init__()

        # setup default options
        self._title = 'Action'

    def connectClient(self, client):
        """
            \remarks	connects the callbacks for the client for this thread
                        can be sub-classed for custom callbacks
        """
        client.callback_notify = self.notify
        client.callback_get_login = svn.login

    def notify(self, event_dict):
        """
            \remarks	triggers the updated event based on the inputed event dictionary
            \param		event_dict		<dict> { <str> key, <str> value }
                        should contain:
                            'action'		<str>
                            'path'			<str>
                            'mime_type'		<str> || None 		(optional)
                            'revision'		<pysvn.Revision>	(optional)
                            'error' 		<str> 				(optional)
        """
        # look for errors
        if event_dict.get('error'):
            self.updated.emit('Error', event_dict['error'], '', -1)

        # look for changes
        else:
            # extract the mime_type
            mime_type = str(event_dict.get('mime_type', ''))
            if mime_type == 'None':
                mime_type = ''

            # extract the revision number
            rev = event_dict.get('revision')
            if rev:
                rev_number = rev.number
            else:
                rev_number = -1

            # extract the user friendly action name
            action = (
                str(event_dict['action'])
                .replace(self.title().lower() + '_', '')
                .capitalize()
            )
            if action == 'Postfix_txdelta':
                action = 'Sending content'

            # trigger the event occurred action
            self.updated.emit(action, event_dict['path'], mime_type, rev_number)

    def setTitle(self, title):
        self._title = title

    def run(self):
        """
            \remarks	main method for the thread.  this will create the client, connect the 
                        required callbacks, and then call the runAction method that should be
                        defined in subclasses
        """
        # create the callbacks
        client = pysvn.Client()
        self.connectClient(client)
        self.runClient(client)

    def title(self):
        return self._title

    @abstractmethod
    def runClient(self, client):
        """
            \remarks	method to apply the action for this thread to the client
            \param		client	<pysvn.Client>
        """
        self.notify(
            {'error': 'The ActionThread.runClient method is not defined properly.'}
        )
