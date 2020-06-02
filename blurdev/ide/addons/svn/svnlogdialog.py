##
# 	\namespace	blurdev.ide.addons.svn.svnlogdialog
#
# 	\remarks	Creates a dialog with a log of all the commits that have been done for a url
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

import pysvn
import datetime

from Qt import QtCompat
from Qt.QtCore import QSize, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QInputDialog, QMessageBox, QTreeWidgetItem

from blurdev.gui import Dialog

from blurdev.ide.addons import svn
from blurdev.ide.addons.svn import svnops

ACTION_MAP = {
    'A': 'Added',
    'M': 'Modified',
    'D': 'Deleted',
}


class LogItem(QTreeWidgetItem):
    def __init__(self, entry):
        # format the entry date
        dtime = datetime.datetime.fromtimestamp(entry.date).strftime('%D %H:%m %P')

        # initialize the base class
        super(LogItem, self).__init__(
            [
                str(entry.revision.number),
                entry.author,
                dtime,
                entry.message.split('\n')[-1],
            ]
        )

        # set the size hint
        self.setSizeHint(1, QSize(120, 18))

        # store custom properties
        self._entry = entry

    def entry(self):
        return self._entry


class ActionItem(QTreeWidgetItem):
    def __init__(self, action):
        super(ActionItem, self).__init__([action['action'], action['path']])

        action_type = action['action']
        self.setText(0, ACTION_MAP.get(action_type, action_type))
        self.setText(1, action['path'])

        # create the copy from information
        cpy = action['copyfrom_path']
        if cpy:
            self.setText(2, cpy)

        rev = action['copyfrom_revision']
        if rev:
            self.setText(3, str(rev.number))


class SvnLogDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # set custom properties
        self._url = ''

        header = self.uiLogTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 2, header.ResizeToContents)

        header = self.uiActionTREE.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)
        QtCompat.QHeaderView.setSectionResizeMode(header, 2, header.Stretch)
        QtCompat.QHeaderView.setSectionResizeMode(header, 3, header.ResizeToContents)

        # create the query thread
        from threads import LogThread

        self._thread = LogThread()
        self._thread.setDiscoverChanged(True)

        # create connections
        self._thread.finished.connect(self.refreshResults)
        self.uiLogTREE.currentItemChanged.connect(self.refreshEntry)
        self.uiLogTREE.customContextMenuRequested.connect(self.showMenu)

    def accept(self):
        if self._thread.isRunning():
            return

        super(SvnLogDialog, self).accept()

    def compare(self):
        items = self.uiLogTREE.selectedItems()
        if len(items) != 2:
            QMessageBox.critical(
                self,
                'Invalid Number of Revisions',
                'You need to select exactly 2 revisions to compare against.',
            )
            return False

        # lookup the common paths
        apaths = [str(path['path']) for path in items[0].entry().changed_paths]
        bpaths = [str(path['path']) for path in items[1].entry().changed_paths]
        paths = list(set(apaths).intersection(bpaths))

        if len(paths) == 0:
            QMessageBox.critical(
                self,
                'No files to compare',
                'There are no files between these revisions to compare.',
            )
            return False
        elif len(paths) > 1:
            path, accepted = QInputDialog.getItem(
                self, 'Select Path', 'Select path to compare', paths
            )
            if not accepted:
                return False
        else:
            path = paths[0]
            path = str(path)

        url = pysvn.Client().root_url_from_path(self._url)
        svnops.compare(
            url + str(path),
            items[0].entry().revision.number,
            items[1].entry().revision.number,
        )

    def reject(self):
        if self._thread.isRunning():
            return

        super(SvnLogDialog, self).reject()

    def currentRevisions(self):
        output = []
        for item in self.uiLogTREE.selectedItems():
            if isinstance(item, LogItem):
                output.append(item.entry().revision.number)
        return output

    def refresh(self):
        self.uiLogTREE.setUpdatesEnabled(False)
        self.uiLogTREE.blockSignals(True)

        self.uiLogTREE.clear()
        item = QTreeWidgetItem(['Loading...'])
        item.setSizeHint(0, QSize(120, 18))
        item.setTextAlignment(0, Qt.AlignCenter)

        self.uiLogTREE.addTopLevelItem(item)
        item.setFirstColumnSpanned(True)

        self._thread.setLimit(100)
        self._thread.setFilepath(self.url())
        self._thread.start()

        self.uiLogTREE.setUpdatesEnabled(True)
        self.uiLogTREE.blockSignals(False)

    def refreshEntry(self):
        item = self.uiLogTREE.currentItem()

        self.uiActionTREE.setUpdatesEnabled(False)
        self.uiActionTREE.blockSignals(True)
        self.uiMessageTXT.setText('')
        self.uiActionTREE.clear()

        # update the entry look
        if isinstance(item, LogItem):
            self.uiMessageTXT.setText(item.entry().message)

            # refresh the items in the actions tree
            for action in item.entry().changed_paths:
                self.uiActionTREE.addTopLevelItem(ActionItem(action))

        self.uiActionTREE.setUpdatesEnabled(True)
        self.uiActionTREE.blockSignals(False)

    def refreshResults(self):
        self.uiLogTREE.setUpdatesEnabled(False)
        self.uiLogTREE.blockSignals(True)

        self.uiLogTREE.clear()

        entries = self._thread.results()
        if not entries:
            item = QTreeWidgetItem(['No entries were found.'])
            item.setSizeHint(0, QSize(120, 18))
            item.setTextAlignment(0, Qt.AlignCenter)

            self.uiLogTREE.addTopLevelItem(item)
            item.setFirstColumnSpanned(True)
        else:
            entries.sort(key=lambda x: x.revision.date, reverse=True)
            for entry in entries:
                item = LogItem(entry)
                self.uiLogTREE.addTopLevelItem(item)

        self.uiLogTREE.setUpdatesEnabled(True)
        self.uiLogTREE.blockSignals(False)

    def showMenu(self):
        from Qt.QtGui import QCursor
        from Qt.QtWidgets import QMenu

        menu = QMenu(self)

        # create compare selected action
        act = menu.addAction('Compare selected...')
        act.setIcon(QIcon(svn.resource('img/compare.png')))
        act.triggered.connect(self.compare)
        menu.exec_(QCursor.pos())

    def setUrl(self, url):
        self._url = str(url)
        self.refresh()

    def url(self):
        return self._url

    @staticmethod
    def getRevisions(url):
        import blurdev

        dlg = SvnLogDialog(blurdev.core.activeWindow())
        dlg.setUrl(url)
        if dlg.exec_():
            return (dlg.currentRevisions(), True)
        return ([], False)

    @staticmethod
    def showLog(url):
        import blurdev

        dlg = SvnLogDialog(blurdev.core.rootWindow())
        dlg.setUrl(url)
        dlg.show()
