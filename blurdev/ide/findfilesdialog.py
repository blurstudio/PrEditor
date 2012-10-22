##
# 	\namespace	python.blurdev.ide.findfilesdialog
#
# 	\remarks	Creates file searching options
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/22/11
#

import os
import re

from blurdev.gui import Dialog
from PyQt4.QtGui import QTreeWidgetItem, QIcon
from PyQt4.QtCore import pyqtSignal, QThread, QTimer, Qt, QVariant

from blurdev.ide import ideglobals
from blurdev.gui.widgets.pyularwidget import PyularDialog


class FindFilesThread(QThread):
    textFound = pyqtSignal(str, str, int)  # filename, line, lineno

    def __init__(self, parent):
        QThread.__init__(self, parent)

        self._basepath = ''
        self._filetypes = ''
        self._searchText = ''
        self._findall = False
        self._results = {}  # file, lines pairing
        self._resultsCount = 0
        self._searchedCount = 0
        self._useRegex = False

    def clear(self):
        self._results.clear()
        self._resultsCount = 0

    def searchedCount(self):
        return self._searchedCount

    def results(self):
        return self._results

    def resultsCount(self):
        """
            \remarks	returns the total number of lines containing the search text
            \return		<int>
        """
        return self._resultsCount

    def run(self):
        # create expressions
        exprs = [
            re.compile(str(os.path.splitext(ftype)[0]).replace('*', '[^\.]*'))
            for ftype in self._filetypes.split(';')
        ]
        filetypes = [os.path.splitext(ftype)[1] for ftype in self._filetypes.split(';')]

        self._resultsCount = 0
        self._searchedCount = 0

        # look up the files in a separate thread
        for (path, dirs, files) in os.walk(self._basepath):
            for file in files:
                filename = os.path.join(path, file)

                # make sure we have the proper file type
                if not (self._findall or os.path.splitext(filename)[1] in filetypes):
                    continue

                # make sure the filename matches the expression
                for expr in exprs:
                    if expr.match(filename):
                        self.searchFile(filename)
                        break

    def searchFile(self, filename):
        # look for the text within the lines
        try:
            f = open(filename, 'r')
        except:
            return

        lines = f.readlines()
        f.close()

        self._searchedCount += 1

        if self._useRegex:
            regex = re.compile(self._searchText, flags=re.I)

        # search through the lines in the file
        for lineno, line in enumerate(lines):
            found = False
            if self._useRegex:
                found = regex.findall(line) != []
            elif self._searchText in line:
                found = True
            if found:
                self._resultsCount += 1
                if not filename in self._results:
                    self._results[filename] = [(lineno + 1, line.strip())]
                else:
                    self._results[filename].append((lineno + 1, line.strip()))

    def setSearchText(self, text):
        self._searchText = str(text)

    def setBasePath(self, basepath):
        self._basepath = basepath

    def setFileTypes(self, filetypes):
        self._filetypes = filetypes
        self._findall = '.*' in filetypes

    def setUseRegex(self, state):
        self._useRegex = state

    def useRegex(self):
        return self._useRegex


class FindFilesDialog(Dialog):
    _instance = None

    fileDoubleClicked = pyqtSignal(str, int)

    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create the thread
        self._searchThread = FindFilesThread(self)

        # create a refresh timer
        self._refreshTimer = QTimer(self)
        self._refreshTimer.setInterval(5000)
        self._refreshTimer.timeout.connect(self.refreshResults)

        # initialize the ui from the prefs
        self.uiSearchTXT.setText(ideglobals.FILE_SEARCH_TEXT)
        self.uiBasePathTXT.setText(ideglobals.FILE_SEARCH_PATH)
        self.uiFileTypesTXT.setText(ideglobals.FILE_SEARCH_TYPES)

        # create the connections
        self.uiSearchBTN.clicked.connect(self.toggleSearch)
        self.uiCloseBTN.clicked.connect(self.close)
        self.uiBasePathBTN.clicked.connect(self.pickFolder)
        self.uiResultsTREE.itemDoubleClicked.connect(self.loadFile)
        self.uiPyularBTN.clicked.connect(self.showPyular)

        self._searchThread.finished.connect(self.searchFinished)

        self.uiPyularBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/pyular.png')))
        self.uiPyularBTN.setVisible(self.uiRegexCHK.isChecked())

        self.refreshFeedbackLabel(0, 0, 0)

    def closeEvent(self, event):
        # make sure to kill the thread before closing
        self._searchThread.terminate()

        Dialog.closeEvent(self, event)

        # set the properties in the prefs module
        ideglobals.FILE_SEARCH_TEXT = str(self.uiSearchTXT.text())
        ideglobals.FILE_SEARCH_TYPES = str(self.uiFileTypesTXT.text())
        ideglobals.FILE_SEARCH_PATH = str(self.uiBasePathTXT.text())

    def loadFile(self, item):
        if item.parent():
            filename = str(item.parent().data(0, Qt.UserRole).toString())
            lineno = item.data(0, Qt.UserRole).toInt()[0]
        else:
            filename = str(item.data(0, Qt.UserRole).toString())
            lineno = 0

        self.fileDoubleClicked.emit(filename, lineno)

    def pickFolder(self):
        from PyQt4.QtGui import QFileDialog

        path = QFileDialog.getExistingDirectory(
            self, directory=self.uiBasePathTXT.text()
        )
        if path:
            self.uiBasePathTXT.setText(path)

    def recordOpenState(self, item=None, key=''):
        output = []
        if not item:
            for i in range(self.uiResultsTREE.topLevelItemCount()):
                output += self.recordOpenState(self.uiResultsTREE.topLevelItem(i))
        else:
            text = str(item.text(0))
            if item.isExpanded():
                output.append(key + text)
            key += text + '::'
            for c in range(item.childCount()):
                output += self.recordOpenState(item.child(c), key)
        return output

    def refreshResults(self):
        self.uiResultsTREE.blockSignals(True)
        self.uiResultsTREE.setUpdatesEnabled(False)

        openState = self.recordOpenState()

        self.uiResultsTREE.clear()
        results = self._searchThread.results()

        self.refreshFeedbackLabel(
            len(results),
            self._searchThread.resultsCount(),
            self._searchThread.searchedCount(),
        )

        filenames = results.keys()
        filenames.sort()
        for filename in filenames:
            lines = results[filename]

            item = QTreeWidgetItem(['from "%s"' % filename])
            item.setData(0, Qt.UserRole, QVariant(filename))
            item.setData(1, Qt.UserRole, QVariant(0))

            for lineno, line in lines:
                lineitem = QTreeWidgetItem(['%06i: %s' % (lineno, line)])
                lineitem.setData(0, Qt.UserRole, QVariant(lineno))
                item.addChild(lineitem)

            self.uiResultsTREE.addTopLevelItem(item)

        self.restoreOpenState(openState)

        self.uiResultsTREE.setUpdatesEnabled(True)
        self.uiResultsTREE.blockSignals(False)

    def restoreOpenState(self, openState, item=None, key=''):
        if not item:
            for i in range(self.uiResultsTREE.topLevelItemCount()):
                self.restoreOpenState(openState, self.uiResultsTREE.topLevelItem(i))
        else:
            text = str(item.text(0))
            itemkey = key + text
            if itemkey in openState:
                item.setExpanded(True)
            key += text + '::'
            for c in range(item.childCount()):
                self.restoreOpenState(openState, item.child(c), key)

    def toggleSearch(self):
        if self.uiSearchBTN.text() == 'Start Search':
            self.search()
        else:
            self.stopSearch()

    def searchFinished(self):
        self._refreshTimer.stop()
        self.uiSearchBTN.setText('Start Search')
        self.refreshResults()

    def search(self):
        # verify the basepath exists
        basepath = str(self.uiBasePathTXT.text())
        if not os.path.exists(basepath):
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(
                self, 'Invalid Basepath', 'The basepath you entered does not exist'
            )
            return False

        # update the button
        self.uiSearchBTN.setText('Stop Search')

        # clear the data
        self._searchThread.clear()
        self.uiResultsTREE.clear()
        self.refreshFeedbackLabel(0, 0, 0)

        # set the search options
        self._searchThread.setSearchText(str(self.uiSearchTXT.text()))
        self._searchThread.setBasePath(basepath)
        self._searchThread.setFileTypes(str(self.uiFileTypesTXT.text()))
        self._searchThread.setUseRegex(self.uiRegexCHK.isChecked())

        # start the search thrad
        self._refreshTimer.start()
        self._searchThread.start()

    def setBasePath(self, path):
        self.uiBasePathTXT.setText(path)

    def showPyular(self):
        dlg = PyularDialog(self)
        dlg.setExpression(self.uiSearchTXT.text())
        dlg.setFlags('I')
        dlg.exec_()
        self.uiSearchTXT.setText(dlg.expression())

    def refreshFeedbackLabel(self, fileCount, resultCount, searchedCount):
        """ Updates the file count label """
        self.uiFeedbackLBL.setText(
            'Found %i times in %s files out of %s files searched.'
            % (resultCount, fileCount, searchedCount)
        )

    def setResultsCount(self, count):
        """ Updates the results count label """
        self.uiResultsCountLBL.setText('Instances: %i' % count)

    def setSearchedCount(self, count):
        self.uiSearchedLBL.setText('in %i' % count)

    def setSearchText(self, text):
        self.uiSearchTXT.setText(text)

    def stopSearch(self):
        self._searchThread.terminate()
        self.searchFinished()

    # define static methods
    @staticmethod
    def instance(parent=None):
        if not FindFilesDialog._instance:
            from PyQt4.QtCore import Qt

            FindFilesDialog._instance = FindFilesDialog(parent)
            FindFilesDialog._instance.setAttribute(Qt.WA_DeleteOnClose, False)

        FindFilesDialog._instance.uiSearchTXT.setFocus()
        return FindFilesDialog._instance
