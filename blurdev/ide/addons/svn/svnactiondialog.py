##
# 	\namespace	blurdev.ide.addons.svn.svncommiteventsdialog
#
# 	\remarks	Displays commit events information to the user
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/24/11
#

import blurdev
from Qt import QtCompat
from Qt.QtCore import Qt
from Qt.QtGui import QColor
from Qt.QtWidgets import QTreeWidgetItem
from blurdev.gui import Dialog
from blurdev.ide.addons.svn import svnconfig


class SvnActionDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        blurdev.gui.loadUi(__file__, self)

        # update the header
        header = self.uiLogTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 2, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 3, header.Stretch)

        # define custom properties
        self._currthread = -1
        self._errored = False
        self._threads = []

    def accept(self):
        if self.canClose():
            super(SvnActionDialog, self).accept()

    def canClose(self):
        for thread in self._threads:
            if thread.isRunning():
                return False
        return True

    def reject(self):
        if self.canClose():
            super(SvnActionDialog, self).reject()

    def threads(self):
        return self._threads

    def setThreads(self, threads):
        # store the threads
        self._threads = threads

        # connect the thread
        for thread in threads:
            # attach this thread so it is protected
            thread.setParent(self)

            # create connections
            thread.updated.connect(self.log)
            thread.finished.connect(self.startNextThread)

    def startThreads(self):
        # grab the threads
        threads = self.threads()

        # make sure we have a valid threads
        if not threads:
            return False

        # clear the current log
        self.uiLogTREE.clear()

        # disable the ability to close during the threads process
        self.uiDialogBTNS.setEnabled(False)

        # log the threads action
        self._errored = False
        self._currthread = -1
        self.startNextThread()

    def startNextThread(self):
        # increment the thread
        self._currthread += 1
        if self._errored or len(self._threads) <= self._currthread:
            self.finish()
            return True

        # run the thread
        self.log('Command', self._threads[self._currthread].title())
        self._threads[self._currthread].start()

    def finish(self):
        # re-enable the close action when the thread finishes
        self.uiDialogBTNS.setEnabled(True)

        try:
            self.parent().projectRefreshItem()
        except Exception:
            pass

    def log(self, action, path, mime_type=None, revision=-1):
        item = QTreeWidgetItem([action, path])

        if action == 'Error':
            self._errored = True

        # add the mime type
        if mime_type:
            item.setText(2, mime_type)

        # add the revision information
        if revision != -1:
            item.setText(1, 'at revision %i' % revision)

        # grab the action color
        clr = svnconfig.ACTION_COLORS.get(str(action), QColor('black'))
        for i in range(item.columnCount()):
            item.setForeground(i, clr)
            item.setTextAlignment(i, Qt.AlignLeft | Qt.AlignTop)

        self.uiLogTREE.addTopLevelItem(item)

    # define static methods
    @staticmethod
    def start(parent, *threads, **kwds):

        # create the action dialog
        dlg = SvnActionDialog(parent)
        dlg.setWindowTitle('SVN %s' % kwds.get('title', 'Action'))
        dlg.setThreads(threads)
        dlg.show()

        # start the process
        dlg.startThreads()
