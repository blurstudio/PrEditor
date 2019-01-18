##
# 	\namespace	blurdev.ide.documenteditor
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

import os
import os.path

from Qt.QtCore import QFile, QTextCodec, Qt, Property, Signal, QPoint, QTimer
from Qt.Qsci import QsciScintilla, QsciLexer, QsciLexerCustom
from Qt.QtGui import QColor, QFont, QIcon, QCursor, QFontMetrics
from Qt.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
    QAction,
    QMenu,
    QShortcut,
)
from Qt import QtCompat

import blurdev
from blurdev.enum import enum
from blurdev.ide import lang
from blurdev.gui import QtPropertyInit
from blurdev.debug import debugMsg, DebugLevel
from .ideeditor import IdeEditor
import re
import string
import time

aspell = None
try:
    import aspell
except ImportError:
    pass


class DocumentEditor(QsciScintilla):
    SearchDirection = enum('First', 'Forward', 'Backward')
    SearchOptions = enum('Backward', 'CaseSensitive', 'WholeWords', 'QRegExp')
    _defaultFont = QFont()
    _defaultFont.fromString('Courier New,9,-1,5,50,0,0,0,1,0')

    fontsChanged = Signal(
        QFont, QFont
    )  # emits the font size change (font size, margin font size)
    documentSaved = Signal(
        QsciScintilla, object
    )  # (DocumentEditor, filename) emitted when ever the document is saved.

    def __init__(self, parent, filename='', lineno=0):
        self._showSmartHighlighting = True
        self._smartHighlightingSupported = False
        QsciScintilla.__init__(self, parent)
        self.setObjectName('DocumentEditor')
        self._speller = None
        self.initialSpellCheckComplete = False
        self.spellCheckTimeout = 0.01
        self.initSpellCheck()

        # create custom properties
        self._filename = ''
        self.additionalFilenames = []
        self._language = ''
        self._lastSearch = ''
        self._textCodec = None
        self._fileMonitoringActive = False
        self._marginsFont = self._defaultFont
        self._lastSearchDirection = self.SearchDirection.First
        self._saveTimer = 0.0
        self._autoReloadOnChange = False
        self._enableFontResizing = True
        # QSci doesnt provide accessors to these values, so store them internally
        self._foldMarginBackgroundColor = QColor(224, 224, 224)
        self._foldMarginForegroundColor = QColor(Qt.white)
        self._marginsBackgroundColor = QColor(224, 224, 224)
        self._marginsForegroundColor = QColor()
        self._matchedBraceBackgroundColor = QColor(224, 224, 224)
        self._matchedBraceForegroundColor = QColor()
        self._unmatchedBraceBackgroundColor = QColor(Qt.white)
        self._unmatchedBraceForegroundColor = QColor(Qt.blue)
        self._caretForegroundColor = QColor()
        self._caretBackgroundColor = QColor(255, 255, 255, 255)
        self._selectionBackgroundColor = QColor(192, 192, 192)
        self._selectionForegroundColor = QColor(Qt.black)
        self._indentationGuidesBackgroundColor = QColor(Qt.white)
        self._indentationGuidesForegroundColor = QColor(Qt.black)
        self._markerBackgroundColor = QColor(Qt.white)
        self._markerForegroundColor = QColor(Qt.black)
        # --------------------------------------------------------------------------------
        # used to store the right click location
        self._clickPos = None
        # dialog shown is used to prevent showing multiple versions of the of the confirmation dialog.
        # this is caused because multiple signals are emitted and processed.
        self._dialogShown = False
        # used to store perminately highlighted keywords
        self._permaHighlight = []
        self._highlightedKeywords = ''
        self.setSmartHighlightingRegEx()

        # intialize settings
        self.initSettings()

        # set one time properties
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(False)
        # Not supported by older builds of QsciScintilla
        if hasattr(self, 'setTabDrawMode'):
            self.setTabDrawMode(QsciScintilla.TabStrikeOut)

        # create connections
        self.customContextMenuRequested.connect(self.showMenu)
        self.selectionChanged.connect(self.updateSelectionInfo)
        blurdev.core.styleSheetChanged.connect(self.updateColorScheme)

        # Create shortcuts
        icon = QIcon(blurdev.resourcePath('img/ide/copy.png'))

        # We have to re-create the copy shortcut so we can use our implementation
        self.uiCopyACT = QAction(icon, 'Copy', self)
        self.uiCopyACT.setShortcut('Ctrl+C')
        self.uiCopyACT.triggered.connect(self.copy)
        self.addAction(self.uiCopyACT)

        iconlstrip = QIcon(blurdev.resourcePath('img/ide/copylstrip.png'))
        self.uiCopyLstripACT = QAction(iconlstrip, 'Copy lstrip', self)
        self.uiCopyLstripACT.setShortcut('Ctrl+Shift+C')
        self.uiCopyLstripACT.triggered.connect(self.copyLstrip)
        self.addAction(self.uiCopyLstripACT)

        self.uiCopyHtmlACT = QAction(icon, 'Copy Html', self)
        self.uiCopyHtmlACT.triggered.connect(self.copyHtml)
        self.addAction(self.uiCopyHtmlACT)

        self.uiCopySpaceIndentationACT = QAction(icon, 'Copy Tabs to Spaces', self)
        self.uiCopySpaceIndentationACT.setShortcut('Ctrl+Shift+Space')
        self.uiCopySpaceIndentationACT.triggered.connect(self.copySpaceIndentation)
        self.addAction(self.uiCopySpaceIndentationACT)

        # Update keyboard shortcuts that come with QsciScintilla
        commands = self.standardCommands()
        # Remove the Ctrl+/ "Move left one word part" shortcut so it can be used to comment
        command = commands.boundTo(Qt.ControlModifier | Qt.Key_Slash)
        if command is not None:
            command.setKey(0)

        # Add QShortcuts
        self.uiShowAutoCompleteSCT = QShortcut(
            Qt.CTRL | Qt.Key_Space, self, context=Qt.WidgetShortcut
        )
        self.uiShowAutoCompleteSCT.activated.connect(lambda: self.showAutoComplete())

        # load the file
        if filename:
            self.load(filename)
        else:
            self.refreshTitle()
            self.setLanguage('Plain Text')

        # goto the line
        if lineno:
            self.setCursorPosition(lineno, 0)

    def autoFormat(self):
        try:
            import autopep8
        except ImportError:
            QMessageBox.warning(
                self.window(),
                'autopep8 missing',
                'The autopep8 library is missing. To use this feature you must install it. https://pypi.python.org/pypi/autopep8/ ',
                QMessageBox.Ok,
            )
            return
        version = autopep8.__version__.split('.')
        if version and version[0] < 1:
            QMessageBox.warning(
                self.window(),
                'autopep8 out of date',
                'The autopep8 library is out of date and needs to be updated. To use this feature you must install it. https://pypi.python.org/pypi/autopep8/ ',
                QMessageBox.Ok,
            )
            return
        options = autopep8.parse_args([''])
        options.max_line_length = self.edgeColumn()
        fixed = autopep8.fix_code(self.text(), options=options)
        self.beginUndoAction()
        startline, startcol, endline, endcol = self.getSelection()
        self.selectAll()
        self.removeSelectedText()
        self.insert(fixed)
        if self.indentationsUseTabs():
            # fix tab indentations
            self.indentSelection(True)
            self.unindentSelection(True)
        self.setSelection(startline, startcol + 1, endline, endcol)
        self.endUndoAction()

    def autoReloadOnChange(self):
        return self._autoReloadOnChange

    def caretBackgroundColor(self):
        return self._caretBackgroundColor

    def caretForegroundColor(self):
        return self._caretForegroundColor

    def setCaretLineBackgroundColor(self, color):
        self._caretBackgroundColor = color
        super(DocumentEditor, self).setCaretLineBackgroundColor(color)

    def setCaretForegroundColor(self, color):
        self._caretForegroundColor = color
        super(DocumentEditor, self).setCaretForegroundColor(color)

    def checkForSave(self):
        if self.isModified():
            result = QMessageBox.question(
                self.window(),
                'Save changes to...',
                'Do you want to save your changes?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if result == QMessageBox.Yes:
                return self.save()
            elif result == QMessageBox.Cancel:
                return False
        return True

    def closeEvent(self, event):
        self.disableTitleUpdate()
        super(DocumentEditor, self).closeEvent(event)

    def closeEditor(self):
        parent = self.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            parent.close()

    def closeAllExcept(self):
        window = self.window()
        parent = self.parent()
        if (
            (isinstance(window, IdeEditor))
            and parent
            and parent.inherits('QMdiSubWindow')
        ):
            window.documentCloseAllExcept(self.parent())

    def closeEvent(self, event):
        # unsubcribe the file from the open file monitor
        self.enableFileWatching(False)
        super(DocumentEditor, self).closeEvent(event)

    def commentCheck(self):
        # collect the language
        language = lang.byName(self._language)
        if not language:
            QMessageBox.critical(
                self,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return '', False

        # grab the line comment
        comment = language.lineComment()
        if not comment:
            QMessageBox.critical(
                self,
                'No Line Comment Defined',
                'There is no line comment symbol defined for the "%s" language.'
                % self._language,
            )
            return '', False
        return comment, True

    def commentAdd(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        self.beginUndoAction()
        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()

        for line in range(startline, endline + 1):
            # do not comment the last line if it contains no selection
            if line != endline or endcol:
                self.setCursorPosition(line, 0)
                self.insert(comment)
        # restore the currently selected text and compensate for the new characters
        if endcol:
            # only adjust the end column value if it contained a selection in the first place.
            endcol += 1
        self.setSelection(startline, startcol + 1, endline, endcol)
        self.endUndoAction()
        return True

    def commentRemove(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        # lookup the selected text positions
        self.beginUndoAction()
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(comment)

        for line in range(startline, endline + 1):
            # do not un-comment the last line if it contains no selection
            if line != endline or endcol:
                self.setSelection(line, 0, line, commentlen)
                if self.selectedText() == comment:
                    self.removeSelectedText()
                    if line == startline:
                        startcol -= 1
                    if line == endline:
                        endcol -= 1
        # restore the currently selected text
        self.setSelection(startline, startcol, endline, endcol)
        self.endUndoAction()
        return True

    def commentToggle(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        self.beginUndoAction()
        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(comment)

        for line in range(startline, endline + 1):
            # do not toggle comments on the last line if it contains no selection
            if line != endline or endcol:
                self.setSelection(line, 0, line, commentlen)
                if self.selectedText() == comment:
                    self.removeSelectedText()
                    if line == startline:
                        startcol -= 1
                    elif line == endline:
                        endcol -= 1
                else:
                    self.setCursorPosition(line, 0)
                    self.insert(comment)
                    if line == startline:
                        startcol += 1
                    elif line == endline:
                        endcol += 1
        # restore the currently selected text
        self.setSelection(startline, startcol, endline, endcol)
        self.endUndoAction()
        return True

    def copy(self):
        """ Copies the selected text.
        
        If copyIndentsAsSpaces and self.indentationsUseTabs() is True it will convert any indents
        to spaces before copying the text.
        """
        if self.copyIndentsAsSpaces and self.indentationsUseTabs():
            self.copySpaceIndentation()
        else:
            super(DocumentEditor, self).copy()

    def copyFilenameToClipboard(self):
        QApplication.clipboard().setText(self._filename)

    def copyLineReference(self):
        sel = self.getSelection()
        # Note: getSelection is 0 based like all good code
        if sel[0] == -1 and self._clickPos:
            lines = (self.lineAt(self.mapFromGlobal(self._clickPos)) + 1, -1)
        else:
            end = sel[2]
            if sel[3] == 0:
                # if nothing is selected on the last line, exclude it
                end -= 1
            lines = (sel[0] + 1, end + 1)
        args = {'filename': self.filename(), 'plural': ''}
        if lines[1] == -1 or lines[0] == lines[1]:
            args['line'] = lines[0]
        else:
            args['line'] = '{}-{}'.format(*lines)
            args['plural'] = 's'
        QApplication.clipboard().setText(
            '{filename}: Line{plural} {line}'.format(**args)
        )

    def copyLstrip(self):
        """Copy's the selected text, but strips off any leading whitespace shared by the entire selection.
        """
        start, s, end, e = self.getSelection()
        count = end - start + 1
        self.setSelection(start, 0, end, e)
        txt = self.selectedText()

        def replacement(match):
            return re.sub('[ \t]', '', match.group(), count=1)

        # NOTE: Don't use re.M, it does not support mac line endings.
        regex = re.compile('(?:^|\r\n?|\n)[ \t]')
        while len(regex.findall(txt)) == count:
            # We found the same number of leading whitespace as lines of text.
            # This means that it all has leading whitespace that needs removed.
            txt = regex.sub(replacement, txt)
        QApplication.clipboard().setText(txt)

    def copySpaceIndentation(self):
        """ Copy the selected text with any tab indents converted to space indents. 
        
        If indentationsUseTabs is False it will just copy the text
        """
        txt = self.selectedText()

        def replacement(match):
            return match.group().replace('\t', ' ' * self.tabWidth())

        # NOTE: Don't use re.M, it does not support mac line endings.
        ret = re.sub('(?:^|\r\n?|\n)\t+', replacement, txt)
        QApplication.clipboard().setText(ret)

    def copyHtml(self):
        """ Copy's the selected text, but formats it using pygments if installed into html."""
        text = self.selectedText()
        from blurdev.utils.errorEmail import highlightCodeHtml

        text = highlightCodeHtml(text, self.language(), None)
        QApplication.clipboard().setText(text)

    def detectEndLine(self, text):
        newlineN = text.find('\n')
        newlineR = text.find('\r')
        if newlineN != -1 and newlineR != -1:
            if newlineN == newlineR + 1:
                # CR LF Windows
                return self.EolWindows
            elif newlineR == newlineN + 1:
                # LF CR ACorn and RISC unsuported
                return self.eolMode()
        if newlineN != -1 and newlineR != -1:
            if newlineN < newlineR:
                # First return is a LF
                return self.EolUnix
            else:
                # first return is a CR
                return self.EolMac
        if newlineN != -1:
            return self.EolUnix
        return self.EolMac

    def editPermaHighlight(self):
        text, success = QInputDialog.getText(
            self,
            'Edit PermaHighlight keywords',
            'Add keywords separated by a space',
            text=' '.join(self.permaHighlight()),
        )
        if success:
            self.setPermaHighlight(text.split(' '))

    def enableFileWatching(self, state):
        """
            \Remarks	Enables/Disables open file change monitoring. If enabled, A dialog will pop up when ever the open file is changed externally.
                        If file monitoring is disabled in the IDE settings it will be ignored
            \Return		<bool>
        """
        # if file monitoring is enabled and we have a file name then set up the file monitoring
        window = self.window()
        self._fileMonitoringActive = False
        if hasattr(window, 'openFileMonitor'):
            fm = window.openFileMonitor()
            if fm:
                if state:
                    fm.addPath(self._filename)
                    self._fileMonitoringActive = True
                else:
                    fm.removePath(self._filename)
        return self._fileMonitoringActive

    def disableTitleUpdate(self):
        self.modificationChanged.connect(self.refreshTitle)

    def enableTitleUpdate(self):
        self.modificationChanged.connect(self.refreshTitle)

    def eventFilter(self, object, event):
        if event.type() == event.Close and not self.checkForSave():
            event.ignore()
            return True
        return False

    def exploreDocument(self):
        path = self._filename
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        if os.path.exists(path):
            blurdev.osystem.explore(path)
        else:
            QMessageBox.critical(
                self, 'Missing Path', 'Could not find %s' % path.replace('/', '\\')
            )

    def exec_(self):
        if self.save():
            blurdev.core.runScript(self.filename())

    def execStandalone(self):
        if self.save():
            os.startfile(str(self.filename()))

    def findInFiles(self, state=False):
        window = self.window()
        if isinstance(window, IdeEditor):
            window.searchFileDialog().setSearchText(self.selectedText())
            window.uiFindInFilesACT.triggered.emit(False)

    def findInFilesPath(self):
        path = self._filename
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        window = self.window()
        if isinstance(window, IdeEditor):
            if os.path.exists(path):
                window.searchFileDialog().setBasePath(path)
            window.uiFindInFilesACT.triggered.emit(False)

    def foldMarginColors(self):
        """ Returns the fold margin's foreground and background QColor
        
        Returns:
            foreground(QColor): The foreground color
            background(QColor): The background color
        """
        return self._foldMarginForegroundColor, self._foldMarginBackgroundColor

    def setFoldMarginColors(self, foreground, background):
        """ Sets the fold margins foreground and background QColor
        
        Args:
            foreground(QColor): The forground color of the checkerboard
            background(QColor): The background color of the checkerboard
        """
        self._foldMarginForegroundColor = foreground
        self._foldMarginBackgroundColor = background
        super(DocumentEditor, self).setFoldMarginColors(foreground, background)

    def goToLine(self, line=None):
        if type(line) != int:
            line, accepted = QInputDialog.getInt(self, 'Line Number', 'Line:')
        else:
            accepted = True

        if accepted:
            # MH 04/12/11 changed from line + 1 to line - 1 to make the gotoLine dialog go to the correct line.
            self.setCursorPosition(line - 1, 0)
            self.ensureLineVisible(line)

    def goToDefinition(self, text=None):
        if not text:
            text = self.selectedText()
            if not text:
                text, accepted = QInputDialog.getText(self, 'def Name', 'Name:')
            else:
                accepted = True
        else:
            accepted = True
        if accepted:
            descriptors = lang.byName(self.language()).descriptors()
            docText = self.text()
            for descriptor in descriptors:
                result = descriptor.search(docText)
                while result:
                    name = result.group('name')
                    if name.startswith(text):
                        self.findNext(name, 0)
                        return
                    result = descriptor.search(docText, result.end())

    def language(self):
        return self._language

    def languageChosen(self, action):
        window = self.window()
        self._fileMonitoringActive = False
        if isinstance(window, IdeEditor):
            window.uiLanguageDDL.setCurrentLanguage(action.text())

    def launchConsole(self):
        if not self._filename:
            return False
        blurdev.osystem.console(self._filename)

    def lineMarginWidth(self):
        return self.marginWidth(self.SymbolMargin)

    def load(self, filename):
        self.initialSpellCheckComplete = False
        filename = str(filename)
        if filename and os.path.exists(filename):
            f = QFile(filename)
            f.open(QFile.ReadOnly)
            text = f.readAll()
            self._textCodec = QTextCodec.codecForUtfText(
                text, QTextCodec.codecForName('UTF-8')
            )
            self.setText(self._textCodec.toUnicode(text))
            f.close()
            self.updateFilename(filename)
            self.enableFileWatching(True)
            self.setEolMode(self.detectEndLine(self.text()))
            return True
        return False

    def filename(self):
        return self._filename

    def findNext(self, text, flags):
        re = (flags & self.SearchOptions.QRegExp) != 0
        cs = (flags & self.SearchOptions.CaseSensitive) != 0
        wo = (flags & self.SearchOptions.WholeWords) != 0
        wrap = True
        forward = True

        result = self.findFirst(text, re, cs, wo, wrap, forward)

        if not result:
            self.findTextNotFound(text)

        return result

    def findPrev(self, text, flags):
        re = (flags & self.SearchOptions.QRegExp) != 0
        cs = (flags & self.SearchOptions.CaseSensitive) != 0
        wo = (flags & self.SearchOptions.WholeWords) != 0
        wrap = True
        forward = False

        isSelected = self.hasSelectedText()
        result = self.findFirst(text, re, cs, wo, wrap, forward)
        if result and isSelected:
            # If text is selected when finding previous, it will find the currently selected text so do another find.
            result = QsciScintilla.findNext(self)

        if not result:
            self.findTextNotFound(text)

        return result

    def findTextNotFound(self, text):
        try:
            # If a number was typed in, ask the user if they wanted to goto that line number.
            line = int(text)
            msg = 'Search string "%s" was not found. \nIt looks like a line number, would you like to goto line %i?'
            result = QMessageBox.critical(
                self,
                'No Text Found',
                msg % (text, line),
                buttons=(QMessageBox.Yes | QMessageBox.No),
                defaultButton=QMessageBox.Yes,
            )
            if result == QMessageBox.Yes:
                self.goToLine(line)
        except ValueError:
            QMessageBox.critical(
                self, 'No Text Found', 'Search string "%s" was not found.' % text
            )

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Backtab:
            self.unindentSelection()
        elif key == Qt.Key_Escape:
            # Using QShortcut for Escape did not seem to work.
            self.showAutoComplete(True)
        else:
            return QsciScintilla.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Menu:
            # Calculate the screen coordinates of the text cursor.
            position = self.positionFromLineIndex(*self.getCursorPosition())
            x = self.SendScintilla(self.SCI_POINTXFROMPOSITION, 0, position)
            y = self.SendScintilla(self.SCI_POINTYFROMPOSITION, 0, position)
            # When using the menu key, show the right click menu at the text
            # cursor, not the mouse cursor, it is not in the correct place.
            self.showMenu(QPoint(x, y))
        else:
            return super(DocumentEditor, self).keyReleaseEvent(event)

    def initSettings(self):
        # grab the document settings config set

        configSet = IdeEditor.documentConfigSet()

        # set the document settings
        section = configSet.section('Common::Document')

        # set visibility settings
        self.setAutoIndent(section.value('autoIndent'))
        self.setIndentationsUseTabs(section.value('indentationsUseTabs'))
        self.setTabIndents(section.value('tabIndents'))
        self.copyIndentsAsSpaces = section.value('copyIndentsAsSpaces')
        self.setTabWidth(section.value('tabWidth'))
        self.setCaretLineVisible(section.value('caretLineVisible'))
        self.setShowWhitespaces(section.value('showWhitespaces'))
        self.setMarginLineNumbers(0, section.value('showLineNumbers'))
        self.setIndentationGuides(section.value('showIndentations'))
        self.setEolVisibility(section.value('showEol'))
        self.setShowSmartHighlighting(section.value('smartHighlighting'))
        self.setBackspaceUnindents(section.value('backspaceUnindents'))
        enableSpellCheck = section.value('spellCheck')

        if section.value('showLimitColumn'):
            self.setEdgeMode(self.EdgeLine)
            self.setEdgeColumn(section.value('limitColumn'))
        else:
            self.setEdgeMode(self.EdgeNone)

        # set autocompletion settings
        if section.value('autoComplete'):
            self.setAutoCompletionSource(QsciScintilla.AcsAll)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)

        self.setAutoCompletionThreshold(section.value('autoCompleteThreshold'))

        # set the scheme settings
        scheme = configSet.section('Editor::Scheme')

        self.setFont(self.documentFont)
        self.setMarginsFont(self.marginsFont())
        self.setMarginWidth(0, QFontMetrics(self.marginsFont()).width('0000000') + 5)
        self._enableFontResizing = scheme.value('document_EnableFontResize')
        self.setSpellCheckEnabled(enableSpellCheck)

    def markerNext(self):
        line, index = self.getCursorPosition()
        newline = self.markerFindNext(line + 1, self.marginMarkerMask(1))

        # wrap around the document if necessary
        if newline == -1:
            newline = self.markerFindNext(0, self.marginMarkerMask(1))

        self.setCursorPosition(newline, index)

    def markerLoad(self, input):
        r"""
            \remarks	Takes a list of line numbers and adds a marker to each of them in the file.
        """
        for line in input:
            marker = self.markerDefine(self.Circle)
            self.markerAdd(line, marker)

    def markerToggle(self):
        line, index = self.getCursorPosition()
        markers = self.markersAtLine(line)
        if not markers:
            marker = self.markerDefine(self.Circle)
            self.markerAdd(line, marker)
        else:
            self.markerDelete(line)
        # update the dictionary that stores the document markers when the ide is closed.
        window = self.window()
        if isinstance(window, IdeEditor):
            if self._filename in window.documentMarkrerDict:
                if line in window.documentMarkrerDict[self._filename]:
                    window.documentMarkrerDict[self._filename].remove(line)
                else:
                    window.documentMarkrerDict[self._filename].append(line)
            else:
                window.documentMarkrerDict[self._filename] = [line]

    def marginsFont(self):
        return self._marginsFont

    def multipleSelection(self):
        """ Returns if multiple selection is enabled. """
        return self.SendScintilla(self.SCI_GETMULTIPLESELECTION)

    def multipleSelectionAdditionalSelectionTyping(self):
        """ Returns if multiple selection allows additional typing. """
        return self.SendScintilla(self.SCI_GETMULTIPLESELECTION)

    def multipleSelectionMultiPaste(self):
        """ Paste into all multiple selections. """
        return self.SendScintilla(self.SCI_GETMULTIPASTE)

    def paste(self):
        text = QApplication.clipboard().text()
        if text.find('\n') == -1 and text.find('\r') == -1:
            return super(DocumentEditor, self).paste()

        def repForMode(mode):
            if mode == self.EolWindows:
                return '\r\n'
            elif mode == self.EolUnix:
                return '\n'
            else:
                return '\r'

        text = text.replace(
            repForMode(self.detectEndLine(text)), repForMode(self.eolMode())
        )
        QApplication.clipboard().setText(text)
        return super(DocumentEditor, self).paste()

    def permaHighlight(self):
        return self._permaHighlight

    def setPermaHighlight(self, value):
        if not isinstance(value, list):
            raise TypeError('PermaHighlight must be a list')
        lexer = self.lexer()
        if self._smartHighlightingSupported:
            self._permaHighlight = value
            self.setHighlightedKeywords(lexer, self._highlightedKeywords)
        else:
            raise TypeError('PermaHighlight is not supported by this lexer.')

    def refreshToolTip(self):
        # TODO: This will proably be removed once I add a user interface to additionalFilenames.
        toolTip = []
        if self.additionalFilenames:
            toolTip.append('<u><b>Additional Filenames:</b></u>')
            for filename in self.additionalFilenames:
                toolTip.append(filename)
        self.setToolTip('\n<br>'.join(toolTip))

    def reloadFile(self):
        return self.reloadDialog(
            'Are you sure you want to reload %s? You will lose all changes'
            % os.path.basename(self.filename())
        )

    def reloadChange(self):
        """
            \Remarks	Callback for file monitoring. If a file was modified or deleted this method is called when Open File Monitoring is enabled.
                        Returns if the file was updated or left open
            \Return		<bool>
        """
        debugMsg(
            'Reload Change called: %0.3f Dialog Shown: %r'
            % (self._saveTimer, self._dialogShown),
            DebugLevel.High,
        )
        if time.time() - self._saveTimer < 0.25:
            # If we are saving no need to reload the file
            debugMsg('timer has not expired', DebugLevel.High)
            return False
        if not os.path.isfile(self.filename()) and not self._dialogShown:
            debugMsg('The file was deleted', DebugLevel.High)
            # the file was deleted, ask the user if they still want to keep the file in the editor.
            self._dialogShown = True
            result = QMessageBox.question(
                self.window(),
                'File Removed...',
                'File: %s has been deleted.\nKeep file in editor?' % self.filename(),
                QMessageBox.Yes,
                QMessageBox.No,
            )
            self._dialogShown = False
            if result == QMessageBox.No:
                debugMsg(
                    'The file was deleted, removing document from editor',
                    DebugLevel.High,
                )
                self.parent().close()
                return False
            # TODO: The file no longer exists, and the document should be marked as changed.
            debugMsg(
                'The file was deleted, But the user left it in the editor',
                DebugLevel.High,
            )
            self.enableFileWatching(False)
            return True
        debugMsg('Defaulting to reload message', DebugLevel.High)
        return self.reloadDialog(
            'File: %s has been changed.\nReload from disk?' % self.filename()
        )

    def reloadDialog(self, message, title='Reload File...'):
        if not self._dialogShown:
            self._dialogShown = True
            if self._autoReloadOnChange or not self.isModified():
                result = QMessageBox.Yes
            else:
                result = QMessageBox.question(
                    self.window(), title, message, QMessageBox.Yes | QMessageBox.No
                )
            self._dialogShown = False
            if result == QMessageBox.Yes:
                return self.load(self.filename())
        return False

    def replace(self, text, searchtext=None, all=False):
        # replace the current text with the inputed text
        if not searchtext:
            searchtext = self.selectedText()

        # make sure something is selected
        if not searchtext:
            return 0

        self.beginUndoAction()
        sel = self.getSelection()

        # replace all of the instances of the text
        if all:
            count = self.text().count(searchtext, Qt.CaseInsensitive)
            found = 0
            while self.findFirst(searchtext, False, False, False, True, True):
                if found == count:
                    # replaced all items, exit so we don't get a infinite loop
                    break
                found += 1
                super(DocumentEditor, self).replace(text)

        # replace a single instance of the text
        else:
            count = 1
            super(DocumentEditor, self).replace(text)

        self.setSelection(*sel)
        self.endUndoAction()

        return count

    def setText(self, text):
        self.blockSignals(True)
        super(DocumentEditor, self).setText(text)
        self.blockSignals(False)
        self.spellCheck(0, len(self.text()), initial=True)

    def refreshTitle(self):
        try:
            parent = self.parent()
            if parent and parent.inherits('QMdiSubWindow'):
                parent.setWindowTitle(self.windowTitle())
        except RuntimeError:
            pass

    def save(self):
        debugMsg(
            '------------------------------ Save Called ------------------------------ ',
            DebugLevel.High,
        )
        ret = self.saveAs(self.filename())
        # If the user has provided additionalFilenames to save, process each of them without
        # switching the current filename.
        for filename in self.additionalFilenames:
            r = self.saveAs(filename, setFilename=False)
        return ret

    def saveAs(self, filename='', setFilename=True):
        debugMsg(
            '------------------------------ Save As Called ------------------------------ ',
            DebugLevel.High,
        )
        newFile = False
        if not filename:
            newFile = True
            filename = self.filename()
            if not filename:
                window = self.window()
                if isinstance(window, IdeEditor):
                    if window.lastSavedFilename():
                        filename = os.path.split(window.lastSavedFilename())[0]
            filename, extFilter = QtCompat.QFileDialog.getSaveFileName(
                self.window(), 'Save File as...', filename
            )

        if filename:
            self._saveTimer = time.time()
            # save the file to disk
            f = QFile(filename)
            f.open(QFile.WriteOnly)
            # make sure the file is writeable
            if f.error() != QFile.NoError:
                debugMsg('An error occured while saving', DebugLevel.High)
                QMessageBox.question(
                    self.window(),
                    'Error saving file...',
                    'There was a error saving the file. Error Code: %i' % f.error(),
                    QMessageBox.Ok,
                )
                f.close()
                return False
            # Attempt to save the file using the same codec that it used to display it
            if self._textCodec:
                f.write(self._textCodec.fromUnicode(self.text()))
            else:
                self.write(f)
            f.close()
            # notify that the document was saved
            self.documentSaved.emit(self, filename)

            # update the file
            if setFilename:
                self.updateFilename(filename)
                if newFile:
                    self.enableFileWatching(True)
            return True
        return False

    def selectProjectItem(self):
        window = self.window()
        if window:
            window.selectProjectItem(self.filename())

    def selectionBackgroundColor(self):
        return self._selectionBackgroundColor

    def setSelectionBackgroundColor(self, color):
        self._selectionBackgroundColor = color
        super(DocumentEditor, self).setSelectionBackgroundColor(color)

    def selectionForegroundColor(self):
        return self._selectionForegroundColor

    def setSelectionForegroundColor(self, color):
        self._selectionForegroundColor = color
        super(DocumentEditor, self).setSelectionForegroundColor(color)

    def setLanguage(self, language):
        if language == 'Plain Text':
            language = ''
        # grab the language from the lang module if it is a string
        if type(language) != lang.Language:
            language = str(language)
            language = lang.byName(language)

        # collect the language's lexer
        if language:
            lexer = language.createLexer(self)
            self._language = language.name()
        else:
            lexer = None
            self._language = ''

        # connect the lexer if possible
        self.setShowSmartHighlighting(self._showSmartHighlighting)

        # set the lexer & init the settings
        self.setLexer(lexer)
        self.initSettings()

        # Add language keywords to aspell session dictionary
        keywords = ''
        if self._speller and self.lexer() and self._language:
            language = lang.byName(self._language)
            lexer = language.createLexer()
            maxEnumIntList = {
                key
                for colorName, keys in language.lexerColorTypes().items()
                for key in keys
            }
            if set([]) == maxEnumIntList:
                # max() needs a non-empty list and the SQL lexer returns an empty set([])
                maxEnumIntList = set([0])
            maxInt = max(maxEnumIntList)
            while maxInt >= 0:
                lexerKeywords = self.lexer().keywords(maxInt)
                if lexerKeywords:
                    keywords = keywords + ' ' + lexerKeywords
                maxInt -= 1
            self._speller.clearSession()

            if not keywords:
                keywords = ''

            for keyword in keywords.split():
                # Split along whitespace
                # Convert '-' to '_' because aspell doesn't process words with '-'
                keyword = keyword.replace('-', '_')
                # Strip '_' because aspell doesn't process words with '_'
                keyword = keyword.strip('_')
                # Remove non-alpha chars because aspell doesn't process words with non-alpha chars
                keyword = ''.join(i for i in keyword if i.isalpha())
                for word in keyword.split('_'):
                    # Split along '_' because aspell doesn't process words with '_'
                    if '' != word:
                        self._speller.addtoSession(word)
            self.spellCheck(0, len(self.text()))

    def setLexer(self, lexer):
        font = self.documentFont
        if lexer:
            font = lexer.font(0)
        # Backup values destroyed when we set the lexer
        marginFont = self.marginsFont()
        folds = self.contractedFolds()
        super(DocumentEditor, self).setLexer(lexer)
        # Restore values destroyed when we set the lexer
        self.setContractedFolds(folds)
        self.setMarginsFont(marginFont)
        self.setMarginsBackgroundColor(self.marginsBackgroundColor())
        self.setMarginsForegroundColor(self.marginsForegroundColor())
        self.setFoldMarginColors(*self.foldMarginColors())
        self.setMatchedBraceBackgroundColor(self.matchedBraceBackgroundColor())
        self.setMatchedBraceForegroundColor(self.matchedBraceForegroundColor())
        if lexer:
            lexer.setColor(
                self.pyIndentationGuidesForegroundColor, self.STYLE_INDENTGUIDE
            )
            lexer.setPaper(
                self.pyIndentationGuidesBackgroundColor, self.STYLE_INDENTGUIDE
            )
        # QSciLexer.wordCharacters is not virtual, or even exposed. This hack allows custom lexers
        # to define their own wordCharacters
        if hasattr(lexer, 'wordCharactersOverride'):
            wordCharacters = lexer.wordCharactersOverride
        else:
            # We can't query the lexer for its word characters, but we can query the document.
            # This ensures the lexer's wordCharacters are used if switching from a wordCharactersOverride
            # lexer to a lexer that doesn't define custom wordCharacters.
            wordCharacters = self.wordCharacters()
        self.SendScintilla(self.SCI_SETWORDCHARS, wordCharacters.encode('utf8'))

        if lexer:
            lexer.setFont(font)
        else:
            self.setFont(font)

    def setLineMarginWidth(self, width):
        self.setMarginWidth(self.SymbolMargin, width)

    def setMarginsFont(self, font):
        super(DocumentEditor, self).setMarginsFont(font)
        self._marginsFont = font

    def setMultipleSelection(self, state):
        """ Enables or disables multiple selection

        Args:
            state (bool): Enable or disable multiple selection. When multiple
                selection is disabled, it is not possible to select multiple
                ranges by holding down the Ctrl key while dragging with the
                mouse.
        """
        self.SendScintilla(self.SCI_SETMULTIPLESELECTION, state)

    def setMultipleSelectionAdditionalSelectionTyping(self, state):
        """ Enables or disables multiple selection allows additional typing.

        Args:
            state (bool): Whether typing, new line, cursor left/right/up/down,
                backspace, delete, home, and end work with multiple selections
                simultaneously. Also allows selection and word and line
                deletion commands.
        """
        self.SendScintilla(self.SCI_SETADDITIONALSELECTIONTYPING, state)

    def setMultipleSelectionMultiPaste(self, state):
        """ Enables or disables multiple selection allows additional typing.

        Args:
            state (int): When pasting into multiple selections, the pasted text
            can go into just the main selection with self.SC_MULTIPASTE_ONCE or
            into each selection with self.SC_MULTIPASTE_EACH.
            self.SC_MULTIPASTE_ONCE is the default.
        """
        self.SendScintilla(self.SCI_SETMULTIPASTE, state)

    def setSmartHighlightingRegEx(
        self, exp='[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>\']'
    ):
        r"""
            \remarks	Set the regular expression used to control if a selection is considered valid for
                        smart highlighting.
            \param		exp		<str>	Default:'[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>]'
        """
        self._smartHighlightingRegEx = exp
        self.selectionValidator = re.compile(exp)

    def setShowFolding(self, state):
        if state:
            self.setFolding(self.BoxedTreeFoldStyle)
        else:
            self.setFolding(self.NoFoldStyle)

    def setShowLineNumbers(self, state):
        self.setMarginLineNumbers(self.SymbolMargin, state)

    def setShowSmartHighlighting(self, state):
        self._showSmartHighlighting = state
        # Disconnect existing connections
        try:
            self.selectionChanged.disconnect(self.updateHighlighter)
        except:
            pass
        self._smartHighlightingSupported = False
        lexer = self.lexer()
        # connect to signal if enabling and possible
        if hasattr(lexer, 'highlightedKeywords'):
            if state:
                self.selectionChanged.connect(self.updateHighlighter)
                self._smartHighlightingSupported = True
            else:
                self.setHighlightedKeywords(lexer, '')

    def setShowWhitespaces(self, state):
        if state:
            self.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.setWhitespaceVisibility(QsciScintilla.WsInvisible)

    def spellCheckEnabled(self):
        if self._speller:
            return True
        else:
            return False

    def setSpellCheckEnabled(self, state):
        if state:
            if aspell:
                self._speller = None
                try:
                    self._speller = aspell.Speller()
                except:
                    pass
                if self._speller:
                    self.initSpellCheck()
                    self.SCN_MODIFIED.connect(self.onTextModified)
                    if self.initialSpellCheckComplete:
                        self.spellCheck(0, len(self.text()))
        else:
            self._speller = None
            try:
                self.SCN_MODIFIED.disconnect(self.onTextModified)
            except TypeError:
                pass
            # Remove indicator
            self.SendScintilla(
                QsciScintilla.SCI_SETINDICATORCURRENT, self.spellCheckIndicatorNumber
            )
            self.SendScintilla(
                QsciScintilla.SCI_INDICATORCLEARRANGE, 0, len(self.text())
            )

    def initSpellCheck(self):
        self.chunkRE = re.compile('([^A-Za-z0-9]*)([A-Za-z0-9]*)')
        self.camelCaseRE = re.compile(
            '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)'
        )
        # https://www.scintilla.org/ScintillaDox.html#SCI_INDICSETSTYLE
        # https://qscintilla.com/indicators/
        self.spellCheckIndicatorNumber = 31
        self.indicatorDefine(
            QsciScintilla.SquiggleLowIndicator, self.spellCheckIndicatorNumber
        )
        self.SendScintilla(
            QsciScintilla.SCI_SETINDICATORCURRENT, self.spellCheckIndicatorNumber
        )
        self.setIndicatorForegroundColor(
            QColor(255, 0, 0), self.spellCheckIndicatorNumber
        )
        self.pos = None
        self.anchor = None

    def camelCaseSplit(self, identifier):
        return [m.group(0) for m in self.camelCaseRE.finditer(identifier)]

    def addWordToDict(self, word):
        self._speller.addtoPersonal(word)
        self._speller.saveAllwords()
        self.spellCheck(0, len(self.text()))
        self.pos += len(word)
        self.SendScintilla(self.SCI_GOTOPOS, self.pos)

    def correctSpelling(self, action):
        self.SendScintilla(self.SCI_GOTOPOS, self.pos)
        self.SendScintilla(self.SCI_SETANCHOR, self.anchor)
        self.beginUndoAction()
        self.SendScintilla(self.SCI_REPLACESEL, action.text())
        self.endUndoAction()

    def spellCheck(self, startPos, lengthText, force=False, initial=False):
        """ Spell check some text in the document.

        This function will run until self.spellCheckTimeout seconds has elapsed
        or it finishes processing. If the spell check timed out, it will
        automatically call spellCheck and continue processing where it left off.

        Args:
            startPos (int): The document position to start spell checking.
            lengthText (int): The document position to stop spell checking.
            force (bool, optional): If False(default) and this widget is not
                visible, this function will just exit. Setting this to True
                will force the document to spell check even if not visible.
            initial (bool, optional): If True, set initialSpellCheckComplete
                to True. Defaults to False.

        Returns:
            int: Returns 0 if spell check is finished. 1 if additional
                processing is scheduled. 2 if the spell check was canceled
                because the widget is not visible.
        """
        if not force and not self.isVisible():
            return 2
        if self._speller:
            start = startPos
            startTime = time.time()
            for match in self.chunkRE.finditer(self.text(startPos, lengthText)):
                # To-do: test if match.start()/end() is optimal
                space, result = tuple(match.groups())
                if space:
                    # If the user inserted space between two words, that space
                    # will still be marked as incorrect. Clear its indicator.
                    self.SendScintilla(
                        QsciScintilla.SCI_SETINDICATORCURRENT,
                        self.spellCheckIndicatorNumber,
                    )
                    self.SendScintilla(
                        QsciScintilla.SCI_INDICATORCLEARRANGE, start, len(space)
                    )
                start += len(space)
                for word in self.camelCaseSplit(result):
                    lengthWord = len(word)
                    if any(
                        letter in string.digits for letter in word
                    ) or self._speller.check(word):
                        self.SendScintilla(
                            QsciScintilla.SCI_SETINDICATORCURRENT,
                            self.spellCheckIndicatorNumber,
                        )
                        self.SendScintilla(
                            QsciScintilla.SCI_INDICATORCLEARRANGE, start, lengthWord
                        )
                    else:
                        self.SendScintilla(
                            QsciScintilla.SCI_SETINDICATORCURRENT,
                            self.spellCheckIndicatorNumber,
                        )
                        self.SendScintilla(
                            QsciScintilla.SCI_INDICATORFILLRANGE, start, lengthWord
                        )
                    start += lengthWord
                if (
                    self.spellCheckTimeout
                    and time.time() - startTime > self.spellCheckTimeout
                ):
                    QTimer.singleShot(
                        0,
                        lambda: self.spellCheck(
                            start, lengthText, force=force, initial=initial
                        ),
                    )
                    return 1
        if initial:
            self.initialSpellCheckComplete = True
        return 0

    def onTextModified(
        self,
        pos,
        mtype,
        text,
        length,
        linesAdded,
        line,
        foldNow,
        foldPrev,
        token,
        annotationLinesAdded,
    ):
        if (
            self._speller
            and self.initialSpellCheckComplete
            and (
                (mtype & self.SC_MOD_INSERTTEXT) == self.SC_MOD_INSERTTEXT
                or (mtype & self.SC_MOD_DELETETEXT) == self.SC_MOD_DELETETEXT
            )
        ):
            # Only spell-check if text was inserted/deleted
            line = self.SendScintilla(self.SCI_LINEFROMPOSITION, pos)
            numberOfLinesToCheck = line + linesAdded
            while line <= numberOfLinesToCheck:
                # If more than 1 line was inserted/deleted, check additional lines
                self.spellCheck(
                    self.SendScintilla(self.SCI_POSITIONFROMLINE, line),
                    self.SendScintilla(self.SCI_GETLINEENDPOSITION, line),
                )
                line += 1

    def showAutoComplete(self, toggle=False):
        # if using autoComplete toggle the autoComplete list
        if self.autoCompletionSource() == QsciScintilla.AcsAll:
            if self.isListActive():  # is the autoComplete list visible
                if toggle:
                    self.cancelList()  # Close the autoComplete list
            else:
                self.autoCompleteFromAll()  # Show the autoComplete list

    def showMenu(self, pos):
        menu = QMenu(self)
        pos = self.mapToGlobal(pos)
        self._clickPos = pos

        if self._speller and self.initialSpellCheckComplete:
            # Get the word under the mouse and split the word if camelCase
            point = self.mapFromGlobal(self._clickPos)
            x = point.x()
            y = point.y()
            wordUnderMouse = self.wordAtPoint(point)
            positionMouse = self.SendScintilla(self.SCI_POSITIONFROMPOINT, x, y)
            wordStartPosition = self.SendScintilla(
                self.SCI_WORDSTARTPOSITION, positionMouse, True
            )
            results = self.chunkRE.findall(
                self.text(wordStartPosition, wordStartPosition + len(wordUnderMouse))
            )

            for space, wordChunk in results:
                camelCaseWords = self.camelCaseSplit(wordChunk)
                lengthSpace = len(space)
                for word in camelCaseWords:
                    lengthWord = len(word)
                    # Calcualate the actual word start position accounting for any non-alpha chars
                    # word_new_start_position = wordStartPosition + lengthSpace
                    if (
                        wordStartPosition + lengthSpace <= positionMouse
                        and wordStartPosition + lengthSpace + lengthWord > positionMouse
                        and not any(letter in string.digits for letter in word)
                        and not self._speller.check(word)
                    ):
                        spellCheckMenuShown = True
                        # For camelCase words, get the exact word under the mouse
                        self.pos = wordStartPosition + lengthSpace
                        self.anchor = wordStartPosition + lengthSpace + lengthWord
                        # Add spelling suggestions to menu
                        submenu = menu.addMenu(word)
                        submenu.setObjectName('uiSpellCheckMENU')
                        wordSuggestionList = self._speller.suggest(word)
                        for wordSuggestion in wordSuggestionList:
                            act = submenu.addAction(wordSuggestion)
                        submenu.triggered.connect(self.correctSpelling)
                        addmenu = menu.addAction('Add %s to dictionary' % word)
                        addmenu.triggered.connect(lambda: self.addWordToDict(word))
                        addmenu.setObjectName('uiSpellCheckAddWordACT')
                        menu.addSeparator()
                        break
                    else:
                        wordStartPosition += lengthWord
                wordStartPosition += lengthSpace

        act = menu.addAction('Find in Files...')
        act.triggered.connect(self.findInFiles)
        # act.setShortcut('Ctrl+Alt+F')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/folder_find.png')))
        act = menu.addAction('Goto')
        # act.setShortcut('Ctrl+G')
        act.triggered.connect(self.goToLine)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto.png')))
        act = menu.addAction('Go to Definition')
        # act.setShortcut('Ctrl+Shift+G')
        act.triggered.connect(self.goToDefinition)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto_def.png')))
        if self._showSmartHighlighting and self._smartHighlightingSupported:
            act = menu.addAction('Edit PermaHighlight')
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/highlighter.png')))
            act.triggered.connect(self.editPermaHighlight)

        menu.addSeparator()

        act = menu.addAction('Collapse/Expand All')
        act.triggered.connect(self.toggleFolding)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/plus_minus.png')))

        menu.addSeparator()

        act = menu.addAction('Cut')
        act.triggered.connect(self.cut)
        act.setShortcut('Ctrl+X')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/cut.png')))

        act = menu.addAction('Copy')
        act.triggered.connect(self.copy)
        act.setShortcut('Ctrl+C')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        copyMenu = menu.addMenu('Advanced Copy')

        # Note: I cant use the actions defined above because they end up getting garbage collected
        iconlstrip = QIcon(blurdev.resourcePath('img/ide/copylstrip.png'))
        act = QAction(iconlstrip, 'Copy lstrip', copyMenu)
        act.setShortcut('Ctrl+Shift+C')
        act.triggered.connect(self.copyLstrip)
        copyMenu.addAction(act)

        icon = QIcon(blurdev.resourcePath('img/ide/copy.png'))
        act = QAction(icon, 'Copy Html', copyMenu)
        act.triggered.connect(self.copyHtml)
        copyMenu.addAction(act)

        act = QAction(icon, 'Copy Tabs to Spaces', copyMenu)
        act.setShortcut('Ctrl+Shift+Space')
        act.triggered.connect(self.copySpaceIndentation)
        copyMenu.addAction(act)

        act = menu.addAction('Paste')
        act.triggered.connect(self.paste)
        act.setShortcut('Ctrl+V')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/paste.png')))

        menu.addSeparator()

        act = menu.addAction('Copy Line Reference')
        act.triggered.connect(self.copyLineReference)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        menu.addSeparator()

        act = menu.addAction('Comment Add')
        act.triggered.connect(self.commentAdd)
        act.setShortcut("Alt+3")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_add.png')))

        act = menu.addAction('Comment Remove')
        act.triggered.connect(self.commentRemove)
        act.setShortcut("Alt+#")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_remove.png')))

        act = menu.addAction('Comment Toggle')
        act.triggered.connect(self.commentToggle)
        act.setShortcut("Ctrl+/")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_toggle.png')))

        menu.addSeparator()

        act = menu.addAction('To Lowercase')
        act.triggered.connect(self.toLower)
        # act.setShortcut('Ctrl+L')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/lowercase.png')))
        act = menu.addAction('To Uppercase')
        act.triggered.connect(self.toUpper)
        # act.setShortcut('Ctrl+U')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/uppercase.png')))

        menu.addSeparator()

        submenu = menu.addMenu('View as...')
        submenu.setIcon(QIcon(blurdev.resourcePath('img/ide/view_as.png')))
        l = self.language()
        act = submenu.addAction('Plain Text')
        if l == "":
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/check.png')))
        submenu.addSeparator()

        for language in lang.languages():
            act = submenu.addAction(language)
            if language == l:
                act.setIcon(QIcon(blurdev.resourcePath('img/ide/check.png')))

        submenu.triggered.connect(self.languageChosen)

        menu.addSeparator()

        act = menu.addAction('Indent using tabs')
        act.triggered.connect(self.setIndentationsUseTabs)
        act.setCheckable(True)
        act.setChecked(self.indentationsUseTabs())

        if self._fileMonitoringActive:
            act = menu.addAction('Auto Reload file')
            act.triggered.connect(self.setAutoReloadOnChange)
            act.setCheckable(True)
            act.setChecked(self._autoReloadOnChange)

        if self.language() == 'Python':
            menu.addSeparator()
            act = menu.addAction('Autoformat (PEP 8)')
            act.triggered.connect(self.autoFormat)
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/python.png')))

        menu.popup(self._clickPos)

    def showEvent(self, event):
        super(DocumentEditor, self).showEvent(event)
        # Update the colorScheme after the stylesheet has been fully loaded.
        self.updateColorScheme()
        if not self.initialSpellCheckComplete:
            self.spellCheck(0, len(self.text()), initial=True)

    def showFolding(self):
        return self.folding() != self.NoFoldStyle

    def showLineNumbers(self):
        return self.marginLineNumbers(self.SymbolMargin)

    def showSmartHighlighting(self):
        return self._showSmartHighlighting

    def showWhitespaces(self):
        return self.whitespaceVisibility() == QsciScintilla.WsVisible

    def smartHighlightingRegEx(self):
        return self._smartHighlightingRegEx

    def toLower(self):
        self.beginUndoAction()
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        text = self.selectedText().lower()
        self.removeSelectedText()
        self.insert(text)
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

    def toggleFolding(self):
        self.foldAll(QApplication.instance().keyboardModifiers() == Qt.ShiftModifier)

    def toUpper(self):
        self.beginUndoAction()
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        text = self.selectedText().upper()
        self.removeSelectedText()
        self.insert(text)
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

    def updateColorScheme(self):
        """ Sets the DocumentEditor's lexer colors, see colorScheme for a compatible dict """
        # lookup the language
        language = lang.byName(self.language())
        lex = self.lexer()
        if not lex:
            self.setPaper(self.paperDefault)
            self.setColor(self.colorDefault)
            return
        # Backup the lexer font. The calls to setPaper/setColor cause it to be reset.
        font = lex.font(0)
        # Set Default lexer colors
        for i in range(128):
            lex.setPaper(self.paperDefault, i)
            lex.setColor(self.colorDefault, i)
        lex.setDefaultPaper(self.paperDefault)
        lex.setDefaultColor(self.colorDefault)
        # Override lexer color/paper values
        if language:
            _lexerColorNames = set(
                [
                    x.replace('color', '')
                    for x in dir(self)
                    if x.startswith('color') and x.replace('color', '')
                ]
            )
            for colorName, keys in language.lexerColorTypes().items():
                color = None
                paper = None
                if colorName == 'misc':
                    color = self.colorDefault
                    paper = self.paperDefault
                else:
                    for name in _lexerColorNames:
                        if name.lower() == colorName:
                            color = getattr(self, 'color{}'.format(name))
                            paper = getattr(self, 'paper{}'.format(name))
                            break
                for key in keys:
                    if paper:
                        lex.setPaper(paper, key)
                    if color:
                        lex.setColor(color, key)
        lex.setColor(self.braceBadForeground, self.STYLE_BRACEBAD)
        lex.setPaper(self.braceBadBackground, self.STYLE_BRACEBAD)
        lex.setColor(self.pyIndentationGuidesForegroundColor, self.STYLE_INDENTGUIDE)
        lex.setPaper(self.pyIndentationGuidesBackgroundColor, self.STYLE_INDENTGUIDE)
        # Update other values stored in the lexer
        self.setFoldMarginColors(
            self.foldMarginsForegroundColor, self.foldMarginsBackgroundColor
        )
        self.setMarginsBackgroundColor(self.marginsBackgroundColor())
        self.setMarginsForegroundColor(self.marginsForegroundColor())
        self.setFoldMarginColors(*self.foldMarginColors())
        self.setMatchedBraceBackgroundColor(self.matchedBraceBackgroundColor())
        self.setMatchedBraceForegroundColor(self.matchedBraceForegroundColor())
        # Restore the existing font
        lex.setFont(font, 0)

    def updateFilename(self, filename):
        filename = str(filename)
        extension = os.path.splitext(filename)[1]

        # determine if we need to modify the language
        if not self._filename or extension != os.path.splitext(self._filename)[1]:
            self.setLanguage(lang.byExtension(extension))

        # update the filename information
        self._filename = os.path.abspath(filename)
        self.setModified(False)

        try:
            self.window().emitDocumentTitleChanged()
        except:
            pass

        self.refreshTitle()

    def updateHighlighter(self):
        # Get selection
        selectedText = self.selectedText()
        # if text is selected make sure it is a word
        lexer = self.lexer()
        if selectedText != lexer.highlightedKeywords:
            if selectedText:
                validator = self.selectionValidator
                if hasattr(lexer, 'selectionValidator'):
                    # If a lexer has defined its own selectionValidator use that instead
                    validator = lexer.selectionValidator
                # Does the text contain a non allowed word?
                if not validator.findall(selectedText) == []:
                    return
                else:
                    selection = self.getSelection()
                    # the character before and after the selection must not be a word.
                    text = self.text(selection[2])  # Character after
                    if selection[3] < len(text):
                        if validator.findall(text[selection[3]]) == []:
                            return
                    text = self.text(selection[0])  # Character Before
                    if selection[1] and selection[1] != -1:
                        if validator.findall(text[selection[1] - 1]) == []:
                            return
            # Make the lexer highlight words
            self.setHighlightedKeywords(lexer, selectedText)

    def updateSelectionInfo(self):
        window = self.window()
        if window and hasattr(window, 'uiCursorInfoLBL'):
            sline, spos, eline, epos = self.getSelection()
            # Add 1 to line numbers because document line numbers are 1 based
            text = ''
            if sline == -1:
                line, pos = self.getCursorPosition()
                line += 1
                text = 'Line: {} Pos: {}'.format(line, pos)
            else:
                sline += 1
                eline += 1
                text = 'Line: {sline} Pos: {spos} To Line: {eline} Pos: {epos} Line Count: {lineCount}'.format(
                    sline=sline,
                    spos=spos,
                    eline=eline,
                    epos=epos,
                    lineCount=eline - sline + 1,
                )
            if self._textCodec and self._textCodec.name() != 'System':
                text = 'Encoding: {enc} {text}'.format(
                    enc=self._textCodec.name(), text=text
                )
            window.uiCursorInfoLBL.setText(text)

    def setAutoReloadOnChange(self, state):
        self._autoReloadOnChange = state

    def setHighlightedKeywords(self, lexer, keywords):
        """
            :remarks	Updates the lexers highlighted keywords
            :param		lexer		<QSciLexer>	Update this lexer and set as the lexer on the document.
            :param		keywords	<str>	keywords to highlight
        """
        self.updateColorScheme()
        self._highlightedKeywords = keywords
        lexer.highlightedKeywords = ' '.join(self._permaHighlight + [keywords])

        # Clearing the lexer before re-setting the lexer seems to fix the scroll/jump issue
        # when using smartHighlighting near the end of the document.
        self.setLexer(None)
        self.setLexer(lexer)
        # repaint appears to fix the problem with text being squashed when smartHighlighting
        # is activated by clicking and draging to select text.
        self.repaint()

    def indentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        self.beginUndoAction()
        for line in range(lineFrom, lineTo + 1):
            self.indent(line)
        self.endUndoAction()

    def unindentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        self.beginUndoAction()
        for line in range(lineFrom, lineTo + 1):
            self.unindent(line)
        self.endUndoAction()

    def windowTitle(self):
        if self._filename:
            title = os.path.basename(self._filename)
        else:
            title = 'New Document'

        if self.isModified():
            title += '*'

        if self.additionalFilenames:
            title = '[{}]'.format(title)

        return title

    def wheelEvent(self, event):
        if self._enableFontResizing and event.modifiers() == Qt.ControlModifier:
            font = self.documentFont
            marginsFont = self.marginsFont()
            lexer = self.lexer()
            if lexer:
                font = lexer.font(0)
            try:
                # Qt5 support
                delta = event.angleDelta().y()
            except:
                # Qt4 support
                delta = event.delta()
            if delta > 0:
                font.setPointSize(font.pointSize() + 1)
                marginsFont.setPointSize(marginsFont.pointSize() + 1)
            else:
                if font.pointSize() - 1 > 0:
                    font.setPointSize(font.pointSize() - 1)
                if marginsFont.pointSize() - 1 > 0:
                    marginsFont.setPointSize(marginsFont.pointSize() - 1)

            self.setMarginsFont(marginsFont)
            if lexer:
                lexer.setFont(font)
            else:
                self.setFont(font)

            self.fontsChanged.emit(font, marginsFont)
            event.accept()
        else:
            super(DocumentEditor, self).wheelEvent(event)

    # expose properties for the designer
    pyLanguage = Property("QString", language, setLanguage)
    pyLineMarginWidth = Property("int", lineMarginWidth, setLineMarginWidth)
    pyShowLineNumbers = Property("bool", showLineNumbers, setShowLineNumbers)
    pyShowFolding = Property("bool", showFolding, setShowFolding)
    pyShowSmartHighlighting = Property(
        "bool", showSmartHighlighting, setShowSmartHighlighting
    )
    pySmartHighlightingRegEx = Property(
        "QString", smartHighlightingRegEx, setSmartHighlightingRegEx
    )

    pyAutoCompletionCaseSensitivity = Property(
        "bool",
        QsciScintilla.autoCompletionCaseSensitivity,
        QsciScintilla.setAutoCompletionCaseSensitivity,
    )
    pyAutoCompletionReplaceWord = Property(
        "bool",
        QsciScintilla.autoCompletionReplaceWord,
        QsciScintilla.setAutoCompletionReplaceWord,
    )
    pyAutoCompletionShowSingle = Property(
        "bool",
        QsciScintilla.autoCompletionShowSingle,
        QsciScintilla.setAutoCompletionShowSingle,
    )
    pyAutoCompletionThreshold = Property(
        "int",
        QsciScintilla.autoCompletionThreshold,
        QsciScintilla.setAutoCompletionThreshold,
    )
    pyAutoIndent = Property(
        "bool", QsciScintilla.autoIndent, QsciScintilla.setAutoIndent
    )
    pyBackspaceUnindents = Property(
        "bool", QsciScintilla.backspaceUnindents, QsciScintilla.setBackspaceUnindents
    )
    pyIndentationGuides = Property(
        "bool", QsciScintilla.indentationGuides, QsciScintilla.setIndentationGuides
    )
    pyIndentationsUseTabs = Property(
        "bool", QsciScintilla.indentationsUseTabs, QsciScintilla.setIndentationsUseTabs
    )
    pyTabIndents = Property(
        "bool", QsciScintilla.tabIndents, QsciScintilla.setTabIndents
    )
    pyUtf8 = Property("bool", QsciScintilla.isUtf8, QsciScintilla.setUtf8)
    pyWhitespaceVisibility = Property(
        "bool",
        QsciScintilla.whitespaceVisibility,
        QsciScintilla.setWhitespaceVisibility,
    )

    # Color Setters required because QSci doesn't expose getters.
    # --------------------------------------------------------------------------------
    def edgeColor(self):
        """ This is subclassed so we can create a Property of it"""
        return super(DocumentEditor, self).edgeColor()

    def setEdgeColor(self, color):
        """ This is subclassed so we can create a Property of it"""
        super(DocumentEditor, self).setEdgeColor(color)

    # Because foreground and background must be set together, this cant use QtPropertyInit
    @Property(QColor)
    def foldMarginsBackgroundColor(self):
        return self._foldMarginBackgroundColor

    @foldMarginsBackgroundColor.setter
    def foldMarginsBackgroundColor(self, color):
        self._foldMarginBackgroundColor = color
        self.setFoldMarginColors(self._foldMarginForegroundColor, color)

    @Property(QColor)
    def foldMarginsForegroundColor(self):
        return self._foldMarginForegroundColor

    @foldMarginsForegroundColor.setter
    def foldMarginsForegroundColor(self, color):
        self._foldMarginForegroundColor = color
        self.setFoldMarginColors(color, self._foldMarginBackgroundColor)

    def indentationGuidesBackgroundColor(self):
        return self._indentationGuidesBackgroundColor

    def setIndentationGuidesBackgroundColor(self, color):
        self._indentationGuidesBackgroundColor = color
        super(DocumentEditor, self).setIndentationGuidesBackgroundColor(color)

    def indentationGuidesForegroundColor(self):
        return self._indentationGuidesForegroundColor

    def setIndentationGuidesForegroundColor(self, color):
        self._indentationGuidesForegroundColor = color
        super(DocumentEditor, self).setIndentationGuidesForegroundColor(color)

    def marginsBackgroundColor(self):
        return self._marginsBackgroundColor

    def setMarginsBackgroundColor(self, color):
        self._marginsBackgroundColor = color
        super(DocumentEditor, self).setMarginsBackgroundColor(color)

    def marginsForegroundColor(self):
        return self._marginsForegroundColor

    def setMarginsForegroundColor(self, color):
        self._marginsForegroundColor = color
        super(DocumentEditor, self).setMarginsForegroundColor(color)

    def matchedBraceBackgroundColor(self):
        return self._matchedBraceBackgroundColor

    def matchedBraceForegroundColor(self):
        return self._matchedBraceForegroundColor

    def setMatchedBraceBackgroundColor(self, color):
        self._matchedBraceBackgroundColor = color
        super(DocumentEditor, self).setMatchedBraceBackgroundColor(color)

    def setMatchedBraceForegroundColor(self, color):
        self._matchedBraceForegroundColor = color
        super(DocumentEditor, self).setMatchedBraceForegroundColor(color)

    def markerBackgroundColor(self):
        return self._markerBackgroundColor

    def setMarkerBackgroundColor(self, color):
        self._markerBackgroundColor = color
        super(DocumentEditor, self).setMarkerBackgroundColor(color)

    def markerForegroundColor(self):
        return self._markerForegroundColor

    def setMarkerForegroundColor(self, color):
        self._markerForegroundColor = color
        super(DocumentEditor, self).setMarkerForegroundColor(color)

    def unmatchedBraceBackgroundColor(self):
        return self._unmatchedBraceBackgroundColor

    def setUnmatchedBraceBackgroundColor(self, color):
        self._unmatchedBraceBackgroundColor = color
        super(DocumentEditor, self).setUnmatchedBraceBackgroundColor(color)

    def unmatchedBraceForegroundColor(self):
        return self._unmatchedBraceForegroundColor

    def setUnmatchedBraceForegroundColor(self, color):
        self._unmatchedBraceForegroundColor = color
        super(DocumentEditor, self).setUnmatchedBraceForegroundColor(color)

    # Handle Stylesheet colors for properties that are built into QsciScintilla but dont have getters.
    pyMarginsBackgroundColor = Property(
        QColor, marginsBackgroundColor, setMarginsBackgroundColor
    )
    pyMarginsForegroundColor = Property(
        QColor, marginsForegroundColor, setMarginsForegroundColor
    )
    pyMatchedBraceBackgroundColor = Property(
        QColor, matchedBraceBackgroundColor, setMatchedBraceBackgroundColor
    )
    pyMatchedBraceForegroundColor = Property(
        QColor, matchedBraceForegroundColor, setMatchedBraceForegroundColor
    )
    pyCaretBackgroundColor = Property(
        QColor, caretBackgroundColor, setCaretLineBackgroundColor
    )
    pyCaretForegroundColor = Property(
        QColor, caretForegroundColor, setCaretForegroundColor
    )
    pySelectionBackgroundColor = Property(
        QColor, selectionBackgroundColor, setSelectionBackgroundColor
    )
    pySelectionForegroundColor = Property(
        QColor, selectionForegroundColor, setSelectionForegroundColor
    )
    pyIndentationGuidesBackgroundColor = Property(
        QColor, indentationGuidesBackgroundColor, setIndentationGuidesBackgroundColor
    )
    pyIndentationGuidesForegroundColor = Property(
        QColor, indentationGuidesForegroundColor, setIndentationGuidesForegroundColor
    )
    pyMarkerBackgroundColor = Property(
        QColor, markerBackgroundColor, setMarkerBackgroundColor
    )
    pyMarkerForegroundColor = Property(
        QColor, markerForegroundColor, setMarkerForegroundColor
    )
    pyUnmatchedBraceBackgroundColor = Property(
        QColor, unmatchedBraceBackgroundColor, setUnmatchedBraceBackgroundColor
    )
    pyUnmatchedBraceForegroundColor = Property(
        QColor, unmatchedBraceForegroundColor, setUnmatchedBraceForegroundColor
    )
    pyEdgeColor = Property(QColor, edgeColor, setEdgeColor)
    documentFont = QtPropertyInit('_documentFont', _defaultFont)
    pyMarginsFont = Property(QFont, marginsFont, setMarginsFont)

    copyIndentsAsSpaces = QtPropertyInit('_copyIndentsAsSpaces', False)

    # These colors are purely defined in DocumentEditor so we can use QtPropertyInit
    braceBadForeground = QtPropertyInit('_braceBadForeground', QColor(255, 255, 255))
    braceBadBackground = QtPropertyInit('_braceBadBackground', QColor(100, 60, 60))

    colorDefault = QtPropertyInit('_colorDefault', QColor())
    colorComment = QtPropertyInit('_colorComment', QColor(0, 127, 0))
    colorNumber = QtPropertyInit('_colorNumber', QColor(0, 127, 127))
    colorString = QtPropertyInit('_colorString', QColor(127, 0, 127))
    colorKeyword = QtPropertyInit('_colorKeyword', QColor(0, 0, 127))
    colorTripleQuotedString = QtPropertyInit(
        '_colorTripleQuotedString', QColor(127, 0, 0)
    )
    colorMethod = QtPropertyInit('_colorMethod', QColor(0, 0, 255))
    colorFunction = QtPropertyInit('_colorFunction', QColor(0, 127, 127))
    colorOperator = QtPropertyInit('_colorOperator', QColor(0, 0, 0))
    colorIdentifier = QtPropertyInit('_colorIdentifier', QColor(0, 0, 0))
    colorCommentBlock = QtPropertyInit('_colorCommentBlock', QColor(127, 127, 127))
    colorUnclosedString = QtPropertyInit('_colorUnclosedString', QColor(0, 0, 0))
    colorSmartHighlight = QtPropertyInit('_colorSmartHighlight', QColor(64, 112, 144))
    colorDecorator = QtPropertyInit('_colorDecorator', QColor(128, 80, 0))

    _defaultPaper = QColor(255, 255, 255)
    paperDefault = QtPropertyInit('_paperDefault', _defaultPaper)
    paperComment = QtPropertyInit('_paperComment', _defaultPaper)
    paperNumber = QtPropertyInit('_paperNumber', _defaultPaper)
    paperString = QtPropertyInit('_paperString', _defaultPaper)
    paperKeyword = QtPropertyInit('_paperKeyword', _defaultPaper)
    paperTripleQuotedString = QtPropertyInit('_paperTripleQuotedString', _defaultPaper)
    paperMethod = QtPropertyInit('_paperMethod', _defaultPaper)
    paperFunction = QtPropertyInit('_paperFunction', _defaultPaper)
    paperOperator = QtPropertyInit('_paperOperator', _defaultPaper)
    paperIdentifier = QtPropertyInit('_paperIdentifier', _defaultPaper)
    paperCommentBlock = QtPropertyInit('_paperCommentBlock', _defaultPaper)
    paperUnclosedString = QtPropertyInit('_paperUnclosedString', QColor(224, 192, 224))
    paperSmartHighlight = QtPropertyInit('_paperSmartHighlight', QColor(155, 255, 155))
    paperDecorator = QtPropertyInit('_paperDecorator', _defaultPaper)
