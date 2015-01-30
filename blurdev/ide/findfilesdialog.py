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
from PyQt4.QtGui import QTreeWidgetItem, QIcon, QApplication, QVBoxLayout, QTextEdit
from PyQt4.QtCore import pyqtSignal, QThread, QTimer, Qt, QVariant, QString

from blurdev.ide import ideglobals
from blurdev.gui.widgets.pyularwidget import PyularDialog


class FindFilesThread(QThread):
    textFound = pyqtSignal(str, str, int)  # filename, line, lineno

    def __init__(self, parent):
        QThread.__init__(self, parent)

        self._basepath = ''
        self._filetypes = ''
        self._excludeRegex = ''
        self._searchText = ''
        self._findall = False
        self._results = {}  # file, lines pairing
        self._errors = []
        self._resultsCount = 0
        self._searchedCount = 0
        self._useRegex = False
        self._exit = False
        self._output = []

    def clear(self):
        self._results.clear()
        self._errors = []
        self._output = []
        self._resultsCount = 0

    def errors(self):
        return self._errors

    def output(self):
        return self._output

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
            re.compile(unicode(os.path.splitext(ftype)[0]).replace('*', '[^\.]*'))
            for ftype in self._filetypes.split(';')
        ]
        filetypes = set(
            [os.path.splitext(ftype)[1] for ftype in self._filetypes.split(';')]
        )

        self._resultsCount = 0
        self._searchedCount = 0

        # look up the files in a separate thread
        try:
            # It would be very expensive to search the same path twice
            basepaths = [
                os.path.normpath(os.path.normcase(p)) for p in self._basepath.split(';')
            ]
            # The treeview used to display the results alphabetically is updated durring the
            # search, so we must search basepaths alphabetically so the results list doesn't
            # have results appended before the previous results
            for basepath in sorted(set(basepaths)):
                self._output.append('Searching Basepath: %s' % basepath)
                for (path, dirs, files) in os.walk(basepath):
                    self._output.append('Checking Directory: %s' % path)
                    for file in files:
                        try:
                            self._output.append('	Checking File: %s' % file)
                            if self._exit:
                                self._exit = False
                                self._output.append(
                                    "!!!!!!!!!!!!!!!!!!!! Exiting !!!!!!!!!!!!!!!!!!!!!!!!!!!"
                                )
                                return
                            filename = os.path.join(path, file)

                            # Ignore any files that matach the provided exclude regex
                            if self._excludeRegex and re.findall(
                                self._excludeRegex, filename
                            ):
                                continue
                            # make sure we have the proper file type
                            if not (
                                self._findall
                                or os.path.splitext(filename)[1] in filetypes
                            ):
                                continue

                            # make sure the filename matches the expression
                            for expr in exprs:
                                if expr.match(filename):
                                    self.searchFile(filename)
                                    break
                        except Exception, e:
                            self._errors.append({"exception": e, "file": file})
                            self._output.append(
                                "	------ Error Reading file: %s Exception: %s"
                                % (filename, repr(e))
                            )
        except Exception, e:
            self._errors.append({"exception": e})
            self._output.append("------ Error looping over dirs: %s" % repr(e))

    def stop(self):
        self._exit = True

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
            try:
                if self._useRegex:
                    found = regex.findall(line) != []
                elif self._searchText in line:
                    found = True
                if found:
                    self._resultsCount += 1
                    self._output.append(
                        "		Result! Line Number: %i File: %s Line: %s"
                        % (lineno, filename, line.strip())
                    )
                    if not filename in self._results:
                        self._results[filename] = [(lineno + 1, line.strip())]
                    else:
                        self._results[filename].append((lineno + 1, line.strip()))
            except Exception, e:
                self._errors.append(
                    {
                        "exception": e,
                        "filename": filename,
                        "lineno": lineno,
                        "line": line,
                    }
                )
                self._output.append(
                    "	------ Error reading line: %i File: %s Exception: %s"
                    % (lineno, filename, repr(e))
                )

    def setSearchText(self, text):
        self._searchText = unicode(text)

    def setBasePath(self, basepath):
        self._basepath = basepath

    def setExcludeRegex(self, filetypes):
        self._excludeRegex = filetypes

    def setFileTypes(self, filetypes):
        self._filetypes = filetypes
        self._findall = '.*' in filetypes

    def setUseRegex(self, state):
        self._useRegex = state

    def useRegex(self):
        return self._useRegex


class FindFilesOutputDialog(Dialog):
    def __init__(self, parent=None, lines=[]):
        super(FindFilesOutputDialog, self).__init__(parent)
        self.setWindowTitle('Search output')
        self.uiDocumentWGT = QTextEdit(self)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(self.uiDocumentWGT)
        self.setLines(lines)

    def setLines(self, lines):
        self.uiDocumentWGT.clear()
        self.uiDocumentWGT.setText('\n'.join(lines))


class FindFilesDialog(Dialog):
    _instance = None

    fileDoubleClicked = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super(FindFilesDialog, self).__init__(parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create the thread
        self._searchThread = FindFilesThread(self)

        # create a refresh timer
        self._refreshTimer = QTimer(self)
        self._refreshTimer.setInterval(5000)
        self._refreshTimer.timeout.connect(self.refreshResults)
        self._allResultsText = ''
        self._resultsFileText = ''

        # initialize the ui from the prefs
        self.uiSearchTXT.setText(ideglobals.FILE_SEARCH_TEXT)
        self.uiBasePathTXT.setText(ideglobals.FILE_SEARCH_PATH)
        excludes = set(os.environ['bdev_find_in_files_exclude'].split(','))
        excludes.add(ideglobals.FILE_SEARCH_EXCLUDE)
        self.uiExcludeRegexDDL.clear()
        self.uiExcludeRegexDDL.addItems(sorted(excludes))
        self.uiExcludeRegexDDL.setCurrentIndex(
            self.uiExcludeRegexDDL.findText(ideglobals.FILE_SEARCH_EXCLUDE)
        )

        ftypes = set(os.environ['bdev_find_in_files_exts'].split(','))
        ftypes.add(ideglobals.FILE_SEARCH_TYPES)
        self.uiFileTypesDDL.clear()
        self.uiFileTypesDDL.addItems(sorted(ftypes))
        self.uiFileTypesDDL.setCurrentIndex(
            self.uiFileTypesDDL.findText(ideglobals.FILE_SEARCH_TYPES)
        )
        self.uiCopyFilenamesBTN.setVisible(False)
        self.uiCopyResultsBTN.setVisible(False)

        # create the connections
        self.uiSearchBTN.clicked.connect(self.toggleSearch)
        self.uiCloseBTN.clicked.connect(self.close)
        self.uiBasePathBTN.clicked.connect(self.pickFolder)
        self.uiResultsTREE.itemDoubleClicked.connect(self.loadFile)
        self.uiPyularBTN.clicked.connect(self.showPyular)
        self.uiCopyFilenamesBTN.clicked.connect(self.copyFilenames)
        self.uiCopyResultsBTN.clicked.connect(self.copyResults)
        self.addAction(self.uiShowOutputACT)

        self._searchThread.finished.connect(self.searchFinished)

        self.uiPyularBTN.setIcon(QIcon(blurdev.resourcePath('img/ide/pyular.png')))
        self.uiPyularBTN.setVisible(self.uiRegexCHK.isChecked())

        self.refreshFeedbackLabel(0, 0, 0)

    def closeEvent(self, event):
        # make sure to kill the thread before closing
        self._searchThread.stop()

        Dialog.closeEvent(self, event)

        # set the properties in the prefs module
        ideglobals.FILE_SEARCH_TEXT = unicode(self.uiSearchTXT.text())
        ideglobals.FILE_SEARCH_TYPES = unicode(self.uiFileTypesDDL.currentText())
        ideglobals.FILE_SEARCH_PATH = unicode(self.uiBasePathTXT.text())
        ideglobals.FILE_SEARCH_EXCLUDE = unicode(self.uiExcludeRegexDDL.currentText())

    def copyFilenames(self):
        QApplication.clipboard().setText(self._resultsFileText)

    def copyResults(self):
        QApplication.clipboard().setText(self._allResultsText)

    def loadFile(self, item):
        if item.parent():
            filename = unicode(item.parent().data(0, Qt.UserRole).toString())
            lineno = item.data(0, Qt.UserRole).toInt()[0]
        else:
            filename = unicode(item.data(0, Qt.UserRole).toString())
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
            text = item.text(0)
            if not isinstance(key, QString):
                key = QString(key)
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

        baseText = (
            'Base Path: {basepath}\n'
            'Exclude: {exclude}\n'
            'File Types: {fileTypes}\n'
            'Find Text: {findText}\n'
            'Is Regular Exp: {isRe}\n\n'
        )
        baseText = baseText.format(
            basepath=self.uiBasePathTXT.text(),
            exclude=self.uiExcludeRegexDDL.currentText(),
            fileTypes=self.uiFileTypesDDL.currentText(),
            findText=self.uiSearchTXT.text(),
            isRe=self.uiRegexCHK.isChecked(),
        )
        self._allResultsText = baseText
        self._resultsFileText = baseText

        filenames = results.keys()
        filenames.sort()
        for filename in filenames:
            lines = results[filename]

            self._allResultsText += '%s\n' % filename
            self._resultsFileText += '%s\n' % filename
            item = QTreeWidgetItem(['from "%s"' % filename])
            item.setData(0, Qt.UserRole, QVariant(filename))
            item.setData(1, Qt.UserRole, QVariant(0))

            for lineno, line in lines:
                self._allResultsText += '\t%06i: %s\n' % (lineno, line)
                lineitem = QTreeWidgetItem(['%06i: %s' % (lineno, line)])
                lineitem.setData(0, Qt.UserRole, QVariant(lineno))
                item.addChild(lineitem)

            self.uiResultsTREE.addTopLevelItem(item)

        self.restoreOpenState(openState)

        self.uiResultsTREE.setUpdatesEnabled(True)
        self.uiResultsTREE.blockSignals(False)
        # remove the trailing new line character
        self._allResultsText.rstrip('\n')
        self._resultsFileText.rstrip('\n')

    def restoreOpenState(self, openState, item=None, key=''):
        if not item:
            for i in range(self.uiResultsTREE.topLevelItemCount()):
                self.restoreOpenState(openState, self.uiResultsTREE.topLevelItem(i))
        else:
            text = item.text(0)
            if not isinstance(key, QString):
                key = QString(key)
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
        basepaths = unicode(self.uiBasePathTXT.text())
        for basepath in basepaths.split(';'):
            if not os.path.exists(basepath):
                from PyQt4.QtGui import QMessageBox

                QMessageBox.critical(
                    self,
                    'Invalid Basepath',
                    'The basepath you entered does not exist.\n{}'.format(basepath),
                )
                return False

        # update the button
        self.uiSearchBTN.setText('Stop Search')

        # clear the data
        self._searchThread.clear()
        self.uiResultsTREE.clear()
        self.refreshFeedbackLabel(0, 0, 0)

        # set the search options
        self._searchThread.setSearchText(unicode(self.uiSearchTXT.text()))
        self._searchThread.setBasePath(basepaths)
        self._searchThread.setFileTypes(unicode(self.uiFileTypesDDL.currentText()))
        self._searchThread.setExcludeRegex(
            unicode(self.uiExcludeRegexDDL.currentText())
        )
        self._searchThread.setUseRegex(self.uiRegexCHK.isChecked())

        # start the search thrad
        self._refreshTimer.start()
        self._searchThread.start()

    def showOutput(self):
        if self.uiSearchBTN.text() != 'Stop Search':
            dlg = FindFilesOutputDialog(self, self._searchThread.output())
            dlg.show()

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
        self.uiCopyFilenamesBTN.setVisible(fileCount)
        self.uiCopyResultsBTN.setVisible(fileCount)

    def setResultsCount(self, count):
        """ Updates the results count label """
        self.uiResultsCountLBL.setText('Instances: %i' % count)

    def setSearchedCount(self, count):
        self.uiSearchedLBL.setText('in %i' % count)

    def setSearchText(self, text):
        self.uiSearchTXT.setText(text)

    def stopSearch(self):
        self._searchThread.stop()
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
