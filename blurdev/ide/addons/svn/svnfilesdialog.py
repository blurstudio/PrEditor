##
# 	\namespace	blurdev.ide.addons.svn.svnfilesdialog
#
# 	\remarks	Prompts the user to select files based on a status criteria
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/25/11
#

import os.path

from blurdev.gui import Dialog
from Qt import QtCompat
from Qt.QtCore import QFileInfo, Qt
from Qt.QtWidgets import QFileIconProvider, QMessageBox, QTreeWidgetItem

from blurdev.ide.addons.svn import svnconfig
from blurdev.ide.addons.svn.threads import DataCollectionThread


class SvnFilesDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create custom methods
        self._statusFilters = []
        self._emptyMessage = 'Could not find any matching files.'

        self.uiOkBTN.setEnabled(False)

        # create temp item
        item = QTreeWidgetItem(['Loading...'])
        item.setTextAlignment(0, Qt.AlignCenter)
        self.uiFilesTREE.addTopLevelItem(item)
        item.setFirstColumnSpanned(True)

        # update the header
        header = self.uiFilesTREE.header()
        for i in range(self.uiFilesTREE.columnCount() - 1):
            QtCompat.QHeaderView.setSectionResizeMode(
                header, i, header.ResizeToContents
            )

        # define custom properties
        self._filepath = ''
        self._thread = DataCollectionThread()

        # create connections
        self._thread.finished.connect(self.refreshResults)
        self.uiOkBTN.clicked.connect(self.accept)
        self.uiCancelBTN.clicked.connect(self.reject)
        self.uiFilesTREE.itemChanged.connect(self.updateInfo)
        self.uiSelectAllCHK.clicked.connect(self.toggleChecked)

    def accept(self):
        # collect the files to submit
        filepaths = self.currentFilepaths()

        # make sure we have a filepath
        if not filepaths:
            QMessageBox.critical(
                self,
                'No Files Selected',
                'There were no files selected to perform the desired action.',
            )
            return False

        # accept the dialog
        super(SvnFilesDialog, self).accept()

    def currentFilepaths(self):
        filepaths = []
        for i in range(self.uiFilesTREE.topLevelItemCount()):
            item = self.uiFilesTREE.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                filepath = item.data(0, Qt.UserRole)
                if filepath:
                    filepaths.append(filepath)
        return filepaths

    # define instance methods
    def filepath(self):
        return self._filepath

    def refresh(self):
        # load the commit data
        self._thread.setFilepath(self._filepath)
        self._thread.start()

    def refreshResults(self):
        self.uiFilesTREE.blockSignals(True)
        self.uiFilesTREE.setUpdatesEnabled(False)

        # create the file icon provider
        provider = QFileIconProvider()
        comcount = 0

        # collect the results and sort them
        results = self._thread.results()
        results.sort(svnconfig.sortStatus)

        # update the base path
        if os.path.isfile(self._filepath):
            basepath = os.path.dirname(self._filepath)
        else:
            basepath = self._filepath

        # reload the tree
        self.uiFilesTREE.clear()
        for result in results:
            if not str(result.text_status) in self._statusFilters:
                continue

            data = svnconfig.statusData(result.text_status)

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
            item.setData(0, Qt.UserRole, result.path)
            item.setCheckState(0, Qt.Checked)

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
            self.uiFilesTREE.addTopLevelItem(item)

        # display no items
        if not self.uiFilesTREE.topLevelItemCount():
            item = QTreeWidgetItem([self._emptyMessage])
            item.setTextAlignment(0, Qt.AlignCenter)
            self.uiFilesTREE.addTopLevelItem(item)
            item.setFirstColumnSpanned(True)

        # update the committable count
        self._commitCount = comcount

        # update the info based on the selection
        self.updateInfo()

        self.uiFilesTREE.setUpdatesEnabled(True)
        self.uiFilesTREE.blockSignals(False)

    def setEmptyMessage(self, emptyMessage):
        self._emptyMessage = emptyMessage

    def setStatusFilters(self, statusFilters):
        self._statusFilters = statusFilters

    def statusFilters(self):
        return self._statusFilters

    def toggleChecked(self, checked):
        self.uiFilesTREE.setUpdatesEnabled(False)
        self.uiFilesTREE.blockSignals(True)

        if checked:
            state = Qt.Checked
        else:
            state = Qt.Unchecked

        count = 0
        for i in range(self.uiFilesTREE.topLevelItemCount()):
            item = self.uiFilesTREE.topLevelItem(i)
            if item.data(0, Qt.UserRole):
                item.setCheckState(0, state)
                count += 1

        self.uiOkBTN.setEnabled(count > 0)

        self.uiFilesTREE.setUpdatesEnabled(True)
        self.uiFilesTREE.blockSignals(False)

    def updateInfo(self):
        # collect the number of checked items
        checked = 0
        for i in range(self.uiFilesTREE.topLevelItemCount()):
            item = self.uiFilesTREE.topLevelItem(i)
            if item.data(0, Qt.UserRole) and item.checkState(0) == Qt.Checked:
                checked += 1

        # select all
        if checked == self.uiFilesTREE.topLevelItemCount():
            self.uiSelectAllCHK.setCheckState(Qt.Checked)
        elif not checked:
            self.uiSelectAllCHK.setCheckState(Qt.Unchecked)
        else:
            self.uiSelectAllCHK.setCheckState(Qt.PartiallyChecked)

        self.uiOkBTN.setEnabled(checked > 0)

    def setFilepath(self, filepath):
        self._filepath = filepath
        self.refresh()

    # define static methods
    @staticmethod
    def collect(
        parent, filepath, statusFilters=[], title='Collect Files', emptyMessage=''
    ):
        dlg = SvnFilesDialog(parent)
        dlg.setWindowTitle('SVN %s' % title)
        dlg.setStatusFilters(statusFilters)

        if emptyMessage:
            dlg.setEmptyMessage(emptyMessage)

        dlg.setFilepath(filepath)

        if dlg.exec_():
            return (dlg.currentFilepaths(), True)
        return ([], False)
