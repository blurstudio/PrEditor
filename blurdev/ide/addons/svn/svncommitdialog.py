##
# 	\namespace	blurdev.ide.addons.svn.svncommitdialog
#
# 	\remarks	Creates the Commit Dialog instance
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import pysvn
import os.path

from blurdev.gui import Dialog
from PyQt4.QtCore import QThread, QFileInfo, QVariant, Qt
from PyQt4.QtGui import QFileIconProvider, QTreeWidgetItem, QMessageBox

from blurdev.ide.addons.svn import svnconfig
from blurdev.ide.addons.svn import svnops
from blurdev.ide.addons.svn.threads import DataCollectionThread


class SvnCommitDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # define local properties
        self._commitCount = 0
        self._filepath = ''
        self._thread = DataCollectionThread()

        # update the header
        header = self.uiChangeTREE.header()
        for i in range(self.uiChangeTREE.columnCount() - 1):
            header.setResizeMode(i, header.ResizeToContents)

        # create temp item
        item = QTreeWidgetItem(['Loading...'])
        item.setTextAlignment(0, Qt.AlignCenter)
        self.uiChangeTREE.addTopLevelItem(item)
        item.setFirstColumnSpanned(True)

        # create connections
        self._thread.finished.connect(self.refreshResults)
        self.uiRecentBTN.clicked.connect(self.pickMessage)
        self.uiOkBTN.clicked.connect(self.accept)
        self.uiCancelBTN.clicked.connect(self.reject)
        self.uiShowUnversionedCHK.clicked.connect(self.refreshResults)
        self.uiChangeTREE.itemChanged.connect(self.updateInfo)
        self.uiChangeTREE.customContextMenuRequested.connect(self.showMenu)

        self.uiOkBTN.setEnabled(False)

    def accept(self):
        if self._thread.isRunning():
            return

        # grab the commit comment
        comment = str(self.uiMessageTXT.toPlainText())
        if not comment:
            answer = QMessageBox.question(
                self,
                'No Comment Supplied',
                'Are you sure you want to commit without a comment?',
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.No:
                return False

        # record the current message
        svnconfig.recordMessage(comment)

        # collect the files to submit
        nonversioned = []
        filepaths = []
        for i in range(self.uiChangeTREE.topLevelItemCount()):
            item = self.uiChangeTREE.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                filepath = str(item.data(0, Qt.UserRole).toString())
                if item.text(2) == 'unversioned':
                    nonversioned.append(filepath)
                filepaths.append(filepath)

        # make sure we have a filepath
        if not filepaths:
            QMessageBox.critical(
                self,
                'No Files Selected',
                'There were no files selected to add to the commit.',
            )
            return False

        # create the commit thread
        from threads.committhread import CommitThread

        thread = CommitThread()
        thread.setFilepaths(filepaths)
        thread.setComments(comment)

        # run add & commit actions
        from svnactiondialog import SvnActionDialog

        if nonversioned:
            from threads.addthread import AddThread

            addthread = AddThread()
            addthread.setFilepaths(nonversioned)
            SvnActionDialog.start(self.parent(), addthread, thread, title='Commit')
        else:
            # run the commit action
            SvnActionDialog.start(self.parent(), thread, title='Commit')

        # accept the dialog
        super(SvnCommitDialog, self).accept()

    def filepath(self):
        return self._filepath

    def refresh(self):
        client = pysvn.Client()

        # load the url information
        self.uiUrlTXT.setText(client.info(self.filepath()).url)

        # load the commit data
        self._thread.setFilepath(self._filepath)
        self._thread.start()

    def pickMessage(self):
        message = svnops.getMessage()
        if message:
            self.uiMessageTXT.setText(message)

    def reject(self):
        if self._thread.isRunning():
            return

        # grab the commit comment
        comment = str(self.uiMessageTXT.toPlainText())
        if comment:
            svnconfig.recordMessage(comment)

        super(SvnCommitDialog, self).reject()

    def refreshResults(self):
        self.uiChangeTREE.blockSignals(True)
        self.uiChangeTREE.setUpdatesEnabled(False)

        # create the file icon provider
        provider = QFileIconProvider()
        comcount = 0

        # collect the results and sort them
        results = self._thread.results()
        results.sort(svnconfig.sortStatus)

        if os.path.isfile(self._filepath):
            basepath = os.path.dirname(self._filepath)
        else:
            basepath = self._filepath

        # reload the tree
        self.uiChangeTREE.clear()
        for result in results:
            data = svnconfig.statusData(result.text_status)

            # determine if this file should be committable
            if not data['commit_visible'] or (
                not self.uiShowUnversionedCHK.isChecked()
                and str(result.text_status) == 'unversioned'
            ):
                continue

            # increment the number of committable files
            comcount += 1

            # create the item (only show relative paths)
            item = QTreeWidgetItem(
                [
                    result.path.replace(basepath, '.'),
                    os.path.splitext(result.path)[1],
                    str(result.text_status),
                ]
            )
            item.setData(0, Qt.UserRole, QVariant(result.path))

            # check if this status should be checked
            if data['commit_checked']:
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)

            # set the fg/bg colors based on status
            fg = svnconfig.ACTION_COLORS[data['foreground']]
            bg = svnconfig.ACTION_COLORS[data['background']]

            for i in range(item.columnCount()):
                if fg:
                    item.setForeground(i, fg)
                if bg:
                    item.setBackground(i, bg)

            # set the icon from the filesystem
            item.setIcon(0, provider.icon(QFileInfo(result.path)))

            # add the item to the tree
            self.uiChangeTREE.addTopLevelItem(item)

        # display no items
        if not self.uiChangeTREE.topLevelItemCount():
            item = QTreeWidgetItem(
                [
                    'No files were changed or added since\nthe last commit.  There is nothing\nfor SVN to do here...'
                ]
            )
            item.setTextAlignment(0, Qt.AlignCenter)
            self.uiChangeTREE.addTopLevelItem(item)
            item.setFirstColumnSpanned(True)

        # update the committable count
        self._commitCount = comcount

        # update the info based on the selection
        self.updateInfo()

        self.uiChangeTREE.setUpdatesEnabled(True)
        self.uiChangeTREE.blockSignals(False)

    def showMenu(self):
        item = self.uiChangeTREE.currentItem()
        if item:
            from PyQt4.QtGui import QCursor
            from svnactionmenu import SvnActionMenu

            menu = SvnActionMenu(
                self, 'commit', str(item.data(0, Qt.UserRole).toString())
            )
            menu.exec_(QCursor.pos())

    def updateInfo(self):
        checked = 0
        for i in range(self.uiChangeTREE.topLevelItemCount()):
            item = self.uiChangeTREE.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                checked += 1

        self.uiInfoLBL.setText(
            '%i files selected, %i files total' % (checked, self._commitCount)
        )
        self.uiOkBTN.setEnabled(checked > 0)

    def setFilepath(self, filepath):
        self._filepath = filepath

        # determine information about this filepath
        self.refresh()

    # define static methods
    @staticmethod
    def commit(parent, filepath):
        dlg = SvnCommitDialog(parent)
        dlg.setFilepath(filepath)
        dlg.show()
