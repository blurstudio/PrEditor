##
#
#   \remarks    This dialog allows the user to create new python classes and packages
#               based on plugin templates
#
#   \author     beta@blur.com
#   \author     Blur Studio
#   \date       08/19/10
#
from __future__ import absolute_import

import logging
import os.path
import re
import string
import sys
import time
from collections import OrderedDict
from contextlib import contextmanager
from functools import partial

from PyQt5.Qsci import QsciScintilla
from PyQt5.QtCore import QTextCodec
from Qt import QtCompat
from Qt.QtCore import Property, QFile, QPoint, Qt, Signal
from Qt.QtGui import QColor, QFont, QFontMetrics, QIcon
from Qt.QtWidgets import (
    QAction,
    QApplication,
    QInputDialog,
    QMenu,
    QMessageBox,
    QShortcut,
)

from .. import osystem, resourcePath
from ..delayable_engine import DelayableEngine
from ..enum import Enum, EnumGroup
from ..gui import QtPropertyInit
from . import lang

logger = logging.getLogger(__name__)


class SearchDirection(EnumGroup):
    First = Enum()
    Forward = Enum()
    Backward = Enum()


class SearchOptions(EnumGroup):
    Backward = Enum()
    CaseSensitive = Enum()
    WholeWords = Enum()
    QRegExp = Enum()


@contextmanager
def undo_step(editor):
    """Context manager that combines all changes performed inside it as a
    single undo action for the document editor."""
    editor.beginUndoAction()
    try:
        yield
    finally:
        editor.endUndoAction()


class DocumentEditor(QsciScintilla):
    _defaultFont = QFont()
    _defaultFont.fromString('Courier New,9,-1,5,50,0,0,0,1,0')

    fontsChanged = Signal(
        QFont, QFont
    )  # emits the font size change (font size, margin font size)
    documentSaved = Signal(
        QsciScintilla, object
    )  # (DocumentEditor, filename) emitted when ever the document is saved.

    def __init__(self, parent, filename='', lineno=0, delayable_engine='default'):
        super(DocumentEditor, self).__init__(parent)
        self.setObjectName('DocumentEditor')
        # Spell check variables
        self.__speller__ = None
        self.pos = None
        self.anchor = None

        # create custom properties
        self._filename = ''
        self.additionalFilenames = []
        self._language = ''
        self._lastSearch = ''
        self._textCodec = None
        self._fileMonitoringActive = False
        self._marginsFont = self._defaultFont
        self._lastSearchDirection = SearchDirection.First
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

        # Setup the DelayableEngine and add the document to it
        self.delayable_info = OrderedDict()
        self.delayable_engine = DelayableEngine.instance(delayable_engine)
        self.delayable_engine.add_document(self)
        # ------------------------------------------------------------------------------
        # used to store the right click location
        self._clickPos = None
        # dialog shown is used to prevent showing multiple versions of the of the
        # confirmation dialog. this is caused because multiple signals are emitted and
        # processed.
        self._dialogShown = False
        # used to store perminately highlighted keywords
        self._permaHighlight = []
        self.setSmartHighlightingRegEx()

        # intialize settings
        self.initSettings(first_time=True)

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
        window = self.window()
        if hasattr(window, 'openFileMonitor'):
            window.styleSheetChanged.connect(self.updateColorScheme)

        # Create shortcuts
        icon = QIcon(resourcePath('img/content-copy.png'))

        # We have to re-create the copy shortcut so we can use our implementation
        self.uiCopyACT = QAction(icon, 'Copy', self)
        self.uiCopyACT.setShortcut('Ctrl+C')
        self.uiCopyACT.triggered.connect(self.copy)
        self.addAction(self.uiCopyACT)

        iconlstrip = QIcon(resourcePath('img/content-duplicate.png'))
        self.uiCopyLstripACT = QAction(iconlstrip, 'Copy lstrip', self)
        self.uiCopyLstripACT.setShortcut('Ctrl+Shift+C')
        self.uiCopyLstripACT.triggered.connect(self.copyLstrip)
        self.addAction(self.uiCopyLstripACT)

        self.uiCopySpaceIndentationACT = QAction(icon, 'Copy Tabs to Spaces', self)
        self.uiCopySpaceIndentationACT.setShortcut('Ctrl+Shift+Space')
        self.uiCopySpaceIndentationACT.triggered.connect(self.copySpaceIndentation)
        self.addAction(self.uiCopySpaceIndentationACT)

        # Update keyboard shortcuts that come with QsciScintilla
        commands = self.standardCommands()
        # Remove the Ctrl+/ "Move left one word part" shortcut so it can be used to
        # comment
        command = commands.boundTo(Qt.ControlModifier | Qt.Key_Slash)
        if command is not None:
            command.setKey(0)

        for command in commands.commands():
            if command.description() == 'Move selected lines up one line':
                command.setKey(Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_Up)
            if command.description() == 'Move selected lines down one line':
                command.setKey(Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_Down)
            if command.description() == 'Duplicate selection':
                command.setKey(Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_D)
            if command.description() == 'Cut current line':
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

    def clear(self):
        super(DocumentEditor, self).clear()
        self._filename = ''

    def closeEvent(self, event):
        self.disableTitleUpdate()
        # unsubcribe the file from the open file monitor
        self.enableFileWatching(False)
        super(DocumentEditor, self).closeEvent(event)

    def closeEditor(self):
        parent = self.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            parent.close()

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

    def commentToggle(self, doWhich=None):
        """Toggle comments, mimicing SublimeText functionality.

        - Comments will be indented to match the outermost line being commented.
        - Commenting / uncommenting is determined by whether all non-empty lines are
          currently commented or not. If they ALL are, then uncomment, otherwise
          comment.
        """

        # If called by 'triggered' signal, clear out passed argument.
        if not isinstance(doWhich, str):
            doWhich = None

        comment, result = self.commentCheck()
        if not result:
            return False
        commentSpace = comment + " "

        with undo_step(self):
            # lookup the selected text positions
            cursorLine, cursorIndex = self.expandCursorToLineSelection()
            startLine, startCol, endLine, endCol = self.getSelection()

            # Collect comments and indents, to determine indentation to use, and whether
            # to comment or uncomment.
            comments = []
            indents = []
            for line in range(startLine, endLine + 1):
                lineText = self.getSelectionCurrentLineText(line)

                # Skip if line is empty, or line is last line without selection
                if not lineText.strip() or (line == endLine and not endCol):
                    continue

                comments.append(lineText.lstrip()[0] == comment)

                curIndent = self.determineIndent(lineText, comment)
                indents.append(curIndent)

            if not indents:
                return
            indent = min(indents)

            # If all lines are comments, we un-comment. If any aren't
            # comments, we comment.
            if doWhich is None:
                if all(comments):
                    doWhich = "Uncomment"
                else:
                    doWhich = "Comment"

            for line in range(startLine, endLine + 1):
                lineText = self.getSelectionCurrentLineText(line)
                if not lineText.strip():
                    continue

                # Do not toggle comments on the last line if it contains no selection
                if line != endLine or endCol:
                    if doWhich == "Comment":
                        self.setCursorPosition(line, indent)
                        self.insert(commentSpace)
                        if cursorIndex is not None and cursorIndex >= indent:
                            cursorIndex += len(commentSpace)
                        if line == startLine:
                            startCol -= len(commentSpace)
                        if line == endLine:
                            endCol += len(commentSpace)

                    elif doWhich == "Uncomment":
                        for curComment in [commentSpace, comment]:
                            foundText = self.getSelectedCommentText(
                                line, indent, len(curComment)
                            )
                            startCol, endCol, cursorIndex, removed = self.removeComment(
                                foundText,
                                curComment,
                                line,
                                indent,
                                startLine,
                                startCol,
                                endLine,
                                endCol,
                                cursorIndex,
                            )
                            if removed:
                                break

            # restore the currently selected text, or cursor position
            if cursorLine is not None:
                startLine, endLine = cursorLine, cursorLine
                startCol, endCol = cursorIndex, cursorIndex
            self.setSelection(startLine, startCol, endLine, endCol)

    def removeComment(
        self,
        text,
        comment,
        line,
        indent,
        startLine,
        startCol,
        endLine,
        endCol,
        cursorIndex,
    ):
        removed = False
        if text == comment:
            commentLen = len(comment)
            self.setSelection(line, indent, line, indent + commentLen)
            self.removeSelectedText()

            # py3 will throw an error if comparing None, so only compare if cursorIndex
            # is not None
            if cursorIndex is not None and cursorIndex > indent:
                adjustment = None
                for checkIndex in range(commentLen - 1):
                    newIndex = indent + checkIndex + 1
                    if cursorIndex == newIndex:
                        adjustment = checkIndex + 1
                        break
                if adjustment is None:
                    adjustment = commentLen
                cursorIndex -= adjustment

            if line == startLine:
                startCol -= commentLen
            if line == endLine:
                endCol -= commentLen

            removed = True
        return startCol, endCol, cursorIndex, removed

    def determineIndent(self, lineText, comment=None):
        indent = len(lineText) - len(lineText.lstrip())
        return indent

    def getSelectedCommentText(self, line, indent, commentLen):
        """Because QScintilla.setSelection automatically strips trailing
        whitespace, we grab the whole rest of the line, then reset it
        to just the length of the currentComment
        """
        self.setSelection(line, indent, line, self.lineLength(line))
        text = self.selectedText()
        if len(text) >= commentLen:
            text = text[:commentLen]
        return text

    def getSelectionCurrentLineText(self, line):
        lineLength = len(self.text(line).rstrip())
        self.setSelection(line, 0, line, lineLength)
        lineText = self.selectedText()
        return lineText

    def expandCursorToLineSelection(self):
        line, index = None, None
        if not self.hasSelectedText():
            line, index = self.getCursorPosition()
            self.setSelection(line, 0, line, self.lineLength(line))
        return line, index

    def copy(self):
        """Copies the selected text.

        If copyIndentsAsSpaces and self.indentationsUseTabs() is True it will convert
        any indents to spaces before copying the text.
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
        """Copy's the selected text, but strips off any leading whitespace shared by the
        entire selection.
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
        """Copy the selected text with any tab indents converted to space indents.

        If indentationsUseTabs is False it will just copy the text
        """
        txt = self.selectedText()

        def replacement(match):
            return match.group().replace('\t', ' ' * self.tabWidth())

        # NOTE: Don't use re.M, it does not support mac line endings.
        ret = re.sub('(?:^|\r\n?|\n)\t+', replacement, txt)
        QApplication.clipboard().setText(ret)

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
        if sys.platform == 'win32':
            return self.EolWindows
        return self.EolUnix

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
        """Enables/Disables open file change monitoring. If enabled, A dialog will pop
        up when ever the open file is changed externally. If file monitoring is
        disabled in the IDE settings it will be ignored.

        Returns:
            bool:
        """
        # if file monitoring is enabled and we have a file name then set up the file
        # monitoring
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
            osystem.explore(path)
        else:
            QMessageBox.critical(
                self, 'Missing Path', 'Could not find %s' % path.replace('/', '\\')
            )

    def execStandalone(self):
        if self.save():
            os.startfile(str(self.filename()))

    def foldMarginColors(self):
        """Returns the fold margin's foreground and background QColor

        Returns:
            foreground(QColor): The foreground color
            background(QColor): The background color
        """
        return self._foldMarginForegroundColor, self._foldMarginBackgroundColor

    def setFoldMarginColors(self, foreground, background):
        """Sets the fold margins foreground and background QColor

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
            # MH 04/12/11 changed from line + 1 to line - 1 to make the gotoLine dialog
            # go to the correct line.
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
        self.setLanguage(action.text())
        self.updateColorScheme()
        self._fileMonitoringActive = False
        window = self.window()
        if hasattr(window, 'uiLanguageDDL'):
            window.uiLanguageDDL.blockSignals(True)
            window.uiLanguageDDL.setCurrentLanguage(action.text())
            window.uiLanguageDDL.blockSignals(False)

    def lineMarginWidth(self):
        return self.marginWidth(self.SymbolMargin)

    def load(self, filename):
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
        re = (flags & SearchOptions.QRegExp) != 0
        cs = (flags & SearchOptions.CaseSensitive) != 0
        wo = (flags & SearchOptions.WholeWords) != 0
        wrap = True
        forward = True

        result = self.findFirst(text, re, cs, wo, wrap, forward)

        if not result:
            self.findTextNotFound(text)

        return result

    def findPrev(self, text, flags):
        re = (flags & SearchOptions.QRegExp) != 0
        cs = (flags & SearchOptions.CaseSensitive) != 0
        wo = (flags & SearchOptions.WholeWords) != 0
        wrap = True
        forward = False

        isSelected = self.hasSelectedText()
        result = self.findFirst(text, re, cs, wo, wrap, forward)
        if result and isSelected:
            # If text is selected when finding previous, it will find the currently
            # selected text so do another find.
            result = QsciScintilla.findNext(self)

        if not result:
            self.findTextNotFound(text)

        return result

    def find_simple(self, find_state):
        """Python implementation of QsciScintilla.simpleFind.

        Args:
            find_state (preditor.scintilla.FindState): A find state used to
                manage the find.

        https://github.com/josephwilk/qscintilla/blob/master/Qt4Qt5/qsciscintilla.cpp
        """
        if find_state.start_pos == find_state.end_pos:
            return -1

        self.SendScintilla(self.SCI_SETTARGETSTART, find_state.start_pos)
        self.SendScintilla(self.SCI_SETTARGETEND, find_state.end_pos)

        # scintilla can't match unicode strings, even in python 3
        # In python 3 you have to cast it to a bytes object
        expr = bytes(str(find_state.expr).encode("utf-8"))

        return self.SendScintilla(self.SCI_SEARCHINTARGET, len(expr), expr)

    def find_text(self, find_state):
        """Finds text in the document without changing the selection.

        Args:
            find_state (preditor.scintilla.FindState): A find state used to
                manage the find.

        Based on QsciScintilla.doFind.
        https://github.com/josephwilk/qscintilla/blob/master/Qt4Qt5/qsciscintilla.cpp
        """
        # Set the search flags
        self.SendScintilla(self.SCI_SETSEARCHFLAGS, find_state.flags)
        # If no end was specified, use the end of the document
        if find_state.end_pos is None:
            find_state.end_pos = self.SendScintilla(self.SCI_GETLENGTH)

        pos = self.find_simple(find_state)

        # See if it was found.  If not and wraparound is wanted, try again.
        if pos == -1 and find_state.wrap:
            if find_state.forward:
                find_state.start_pos = 0
                if find_state.start_pos_original is None:
                    find_state.end_pos = self.SendScintilla(self.SCI_GETLENGTH)
                else:
                    find_state.end_pos = find_state.start_pos_original
            else:
                if find_state.start_pos_original is None:
                    find_state.start_pos = self.SendScintilla(self.SCI_GETLENGTH)
                else:
                    find_state.start_pos = find_state.start_pos_original
                find_state.end_pos = 0
            # Give a indication that we have wrapped
            find_state.wrapped = True

            pos = self.find_simple(find_state)

        if pos == -1:
            return -1, 0

        # It was found.
        target_start = self.SendScintilla(self.SCI_GETTARGETSTART)
        target_end = self.SendScintilla(self.SCI_GETTARGETEND)

        # Finally adjust the start position so that we don't find the same one again.
        if find_state.forward:
            find_state.start_pos = target_end
        else:
            find_state.start_pos = target_start - 1
            if find_state.start_pos < 0:
                find_state.start_pos = 0

        return target_start, target_end

    def find_text_from_cursor(self, find_state):
        """Starting from the current cursor position wrapping around, return all
        matches to the provided find_state.

        Args:
            find_state (preditor.scintilla.FindState): A find state used to
                manage the find.
        """
        # Start searching from the cursor, wrap past the end and stop where we started
        current_position = self.positionFromLineIndex(*self.getCursorPosition())
        find_state.start_pos = current_position
        find_state.start_pos_original = current_position

        positions = []
        start, end = self.find_text(find_state)
        while start != -1:
            positions.append((start, end))
            if find_state.wrapped:
                # once we have wrapped, disable wrap
                find_state.wrap = False
            start, end = self.find_text(find_state)
        return positions

    def findTextNotFound(self, text):
        try:
            # If a number was typed in, ask the user if they wanted to goto that line
            # number.
            line = int(text)
            msg = (
                'Search string "%s" was not found. \nIt looks like a line number, '
                'would you like to goto line %i?'
            )
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

    def initSettings(self, first_time=False):
        """Set/reset settings using the IDE section settings."""

        # set visibility settings
        self.setAutoIndent(True)
        if first_time:
            self.setIndentationsUseTabs(False)
        self.setTabIndents(True)
        self.setTabWidth(4)
        self.setCaretLineVisible(False)
        self.setShowWhitespaces(False)
        self.setMarginLineNumbers(0, True)
        self.setIndentationGuides(False)
        self.setEolVisibility(False)
        self.setShowSmartHighlighting(True)
        self.setBackspaceUnindents(True)

        self.setEdgeMode(self.EdgeNone)

        # set autocompletion settings
        self.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.setAutoCompletionThreshold(3)

        self.setFont(self.documentFont)
        self.setMarginsFont(self.marginsFont())
        self.setMarginWidth(0, QFontMetrics(self.marginsFont()).width('0000000') + 5)

    def markerNext(self):
        line, index = self.getCursorPosition()
        newline = self.markerFindNext(line + 1, self.marginMarkerMask(1))

        # wrap around the document if necessary
        if newline == -1:
            newline = self.markerFindNext(0, self.marginMarkerMask(1))

        self.setCursorPosition(newline, index)

    def markerLoad(self, input):
        r"""
        \remarks    Takes a list of line numbers and adds a marker to each of them
        in the file.
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

    def marginsFont(self):
        return self._marginsFont

    def multipleSelection(self):
        """Returns if multiple selection is enabled."""
        return self.SendScintilla(self.SCI_GETMULTIPLESELECTION)

    def multipleSelectionAdditionalSelectionTyping(self):
        """Returns if multiple selection allows additional typing."""
        return self.SendScintilla(self.SCI_GETMULTIPLESELECTION)

    def multipleSelectionMultiPaste(self):
        """Paste into all multiple selections."""
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

    def refreshToolTip(self):
        # TODO: This will proably be removed once I add a user interface to
        # additionalFilenames.
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
        """Callback for file monitoring. If a file was modified or deleted this method
        is called when Open File Monitoring is enabled. Returns if the file was updated
        or left open

        Returns:
            bool:
        """
        logger.debug(
            'Reload Change called: %0.3f Dialog Shown: %r'
            % (self._saveTimer, self._dialogShown),
        )
        if time.time() - self._saveTimer < 0.5:
            # If we are saving no need to reload the file
            logger.debug('timer has not expired')
            return False
        if not os.path.isfile(self.filename()) and not self._dialogShown:
            logger.debug('The file was deleted')
            # the file was deleted, ask the user if they still want to keep the file in
            # the editor.
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
                logger.debug(
                    'The file was deleted, removing document from editor',
                )
                self.parent().close()
                return False
            # TODO: The file no longer exists, and the document should be marked as
            # changed.
            logger.debug(
                'The file was deleted, But the user left it in the editor',
            )
            self.enableFileWatching(False)
            return True
        logger.debug('Defaulting to reload message')
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

        with undo_step(self):
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

        return count

    def setText(self, text):
        self.blockSignals(True)
        super(DocumentEditor, self).setText(text)
        self.blockSignals(False)
        self.spellCheck(0, None)

    def refreshTitle(self):
        try:
            parent = self.parent()
            if parent and parent.inherits('QMdiSubWindow'):
                parent.setWindowTitle(self.windowTitle())
        except RuntimeError:
            pass

    def save(self):
        logger.debug(' Saved Called'.center(60, '-'))
        ret = self.saveAs(self.filename())
        # If the user has provided additionalFilenames to save, process each of them
        # without switching the current filename.
        for filename in self.additionalFilenames:
            self.saveAs(filename, setFilename=False)
        return ret

    def saveAs(self, filename='', setFilename=True):
        logger.debug(' Save As Called '.center(60, '-'))
        newFile = False
        if not filename:
            newFile = True
            filename = self.filename()
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
                logger.debug('An error occured while saving')
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

    def selection_is_word(self):
        """Checks if the current selection is a single word.

        Returns:
            bool: The selected text is a single word.
        """
        sel = self.getSelection()
        start = self.positionFromLineIndex(*sel[:2])
        end = self.positionFromLineIndex(*sel[2:])
        return self.is_word(start, end)

    def is_word(self, start, end):
        """Checks if the text between start and end position is a word

        Args:
            start (int): Start of text offset index position.
            end (int): End of text offset index position.

        Returns:
            bool: The text between the start and end position is a single word.
        """
        if start == end:
            return False
        # Get the word at the start of selection, if the selection doesn't match
        # its not a word.
        start_pos = self.SendScintilla(self.SCI_WORDSTARTPOSITION, start, True)
        end_pos = self.SendScintilla(self.SCI_WORDENDPOSITION, start, True)

        return start == start_pos and end == end_pos

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

        # set the lexer & init the settings
        self.setLexer(lexer)
        self.initSettings()

        # Add language keywords to aspell session dictionary
        if self.spellCheckEnabled():
            self.delayable_engine.delayables['spell_check'].reset_session(self)

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
        # QSciLexer.wordCharacters is not virtual, or even exposed. This hack allows
        # custom lexers to define their own wordCharacters
        if hasattr(lexer, 'wordCharactersOverride'):
            wordCharacters = lexer.wordCharactersOverride
        else:
            # We can't query the lexer for its word characters, but we can query the
            # document. This ensures the lexer's wordCharacters are used if switching
            # from a wordCharactersOverride lexer to a lexer that doesn't define custom
            # wordCharacters.
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
        """Enables or disables multiple selection

        Args:
            state (bool): Enable or disable multiple selection. When multiple
                selection is disabled, it is not possible to select multiple
                ranges by holding down the Ctrl key while dragging with the
                mouse.
        """
        self.SendScintilla(self.SCI_SETMULTIPLESELECTION, state)

    def setMultipleSelectionAdditionalSelectionTyping(self, state):
        """Enables or disables multiple selection allows additional typing.

        Args:
            state (bool): Whether typing, new line, cursor left/right/up/down,
                backspace, delete, home, and end work with multiple selections
                simultaneously. Also allows selection and word and line
                deletion commands.
        """
        self.SendScintilla(self.SCI_SETADDITIONALSELECTIONTYPING, state)

    def setMultipleSelectionMultiPaste(self, state):
        """Enables or disables multiple selection allows additional typing.

        Args:
            state (int): When pasting into multiple selections, the pasted text
            can go into just the main selection with self.SC_MULTIPASTE_ONCE or
            into each selection with self.SC_MULTIPASTE_EACH.
            self.SC_MULTIPASTE_ONCE is the default.
        """
        self.SendScintilla(self.SCI_SETMULTIPASTE, state)

    def setSmartHighlightingRegEx(
        self, exp=r'[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>\']'
    ):
        """Set the regular expression used to control if a selection is considered
        valid for smart highlighting.

        Args:
            exp (str):
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
        self.delayable_engine.set_delayable_enabled('smart_highlight', state)

    def setShowWhitespaces(self, state):
        if state:
            self.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.setWhitespaceVisibility(QsciScintilla.WsInvisible)

    def spellCheckEnabled(self):
        """Is spellcheck is enabled for this document."""
        return self.delayable_engine.delayable_enabled('spell_check')

    def setSpellCheckEnabled(self, state):
        """Enable/disable spellcheck if spellcheck can be enabled.
        This changes spellcheck for all documents attached to this
        documents delayable_engine.
        """
        self.delayable_engine.set_delayable_enabled('spell_check', state)

    def addWordToDict(self, word):
        self.__speller__.addtoPersonal(word)
        self.__speller__.saveAllwords()
        self.spellCheck(0, None)
        self.pos += len(word)
        self.SendScintilla(self.SCI_GOTOPOS, self.pos)

    def correctSpelling(self, action):
        self.SendScintilla(self.SCI_GOTOPOS, self.pos)
        self.SendScintilla(self.SCI_SETANCHOR, self.anchor)
        with undo_step(self):
            self.SendScintilla(self.SCI_REPLACESEL, action.text())

    def spellCheck(self, start_pos, end_pos):
        """Check spelling for some text in the document.

        Args:
            start_pos (int): The document position to start spell checking.
            end_pos (int): The document position to stop spell checking.

        Returns:
            int: Returns 0 if spell check is finished. 1 if additional
                processing is scheduled. 2 if the spell check was canceled
                because the widget is not visible.
        """
        self.delayable_engine.enqueue(self, 'spell_check', start_pos, end_pos)

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
        if self.spellCheckEnabled() and (
            (mtype & self.SC_MOD_INSERTTEXT) == self.SC_MOD_INSERTTEXT
            or (mtype & self.SC_MOD_DELETETEXT) == self.SC_MOD_DELETETEXT
        ):
            # Only spell-check if text was inserted/deleted
            line = self.SendScintilla(self.SCI_LINEFROMPOSITION, pos)
            # More than one line could have been inserted.
            # If this number is negative it will cause Qt to crash.
            lines_to_check = line + max(0, linesAdded)
            self.spellCheck(
                self.SendScintilla(self.SCI_POSITIONFROMLINE, line),
                self.SendScintilla(self.SCI_GETLINEENDPOSITION, lines_to_check),
            )

    def showAutoComplete(self, toggle=False):
        # if using autoComplete toggle the autoComplete list
        if self.autoCompletionSource() == QsciScintilla.AcsAll:
            if self.isListActive():  # is the autoComplete list visible
                if toggle:
                    self.cancelList()  # Close the autoComplete list
            else:
                self.autoCompleteFromAll()  # Show the autoComplete list

    def showMenu(self, pos, popup=True):
        menu = QMenu(self)
        pos = self.mapToGlobal(pos)
        self._clickPos = pos

        if self.spellCheckEnabled():
            # Get the word under the mouse and split the word if camelCase
            point = self.mapFromGlobal(self._clickPos)
            x = point.x()
            y = point.y()
            wordUnderMouse = self.wordAtPoint(point)
            positionMouse = self.SendScintilla(self.SCI_POSITIONFROMPOINT, x, y)
            wordStartPosition = self.SendScintilla(
                self.SCI_WORDSTARTPOSITION, positionMouse, True
            )
            spell_check = self.delayable_engine.delayables['spell_check']
            results = spell_check.chunk_re.findall(
                self.text(wordStartPosition, wordStartPosition + len(wordUnderMouse))
            )

            for space, wordChunk in results:
                camel_case_words = spell_check.camel_case_split(wordChunk)
                lengthSpace = len(space)
                for word in camel_case_words:
                    lengthWord = len(word)
                    # Calcualate the actual word start position accounting for any
                    # non-alpha chars word_new_start_position = wordStartPosition +
                    # lengthSpace
                    if (
                        wordStartPosition + lengthSpace <= positionMouse
                        and wordStartPosition + lengthSpace + lengthWord > positionMouse
                        and not any(letter in string.digits for letter in word)
                        and not self.__speller__.check(word)
                    ):
                        # For camelCase words, get the exact word under the mouse
                        self.pos = wordStartPosition + lengthSpace
                        self.anchor = wordStartPosition + lengthSpace + lengthWord
                        # Add spelling suggestions to menu
                        submenu = menu.addMenu(word)
                        submenu.setObjectName('uiSpellCheckMENU')
                        wordSuggestionList = self.__speller__.suggest(word)
                        for wordSuggestion in wordSuggestionList:
                            act = submenu.addAction(wordSuggestion)
                        submenu.triggered.connect(self.correctSpelling)
                        addmenu = menu.addAction('Add %s to dictionary' % word)
                        addmenu.triggered.connect(partial(self.addWordToDict, word))
                        addmenu.setObjectName('uiSpellCheckAddWordACT')
                        menu.addSeparator()
                        break
                    else:
                        wordStartPosition += lengthWord
                wordStartPosition += lengthSpace

        act = menu.addAction('Goto')
        # act.setShortcut('Ctrl+G')
        act.triggered.connect(self.goToLine)
        act.setIcon(QIcon(resourcePath('img/skip-next-outline.png')))
        act = menu.addAction('Go to Definition')
        # act.setShortcut('Ctrl+Shift+G')
        act.triggered.connect(self.goToDefinition)
        act.setIcon(QIcon(resourcePath('img/skip-forward-outline.png')))
        if self.showSmartHighlighting():
            act = menu.addAction('Edit PermaHighlight')
            act.setIcon(QIcon(resourcePath('img/marker.png')))
            act.triggered.connect(self.editPermaHighlight)

        menu.addSeparator()

        act = menu.addAction('Collapse/Expand All')
        act.triggered.connect(self.toggleFolding)
        act.setIcon(QIcon(resourcePath('img/plus-minus-variant.png')))

        menu.addSeparator()

        act = menu.addAction('Cut')
        act.triggered.connect(self.cut)
        act.setShortcut('Ctrl+X')
        act.setIcon(QIcon(resourcePath('img/content-cut.png')))

        act = menu.addAction('Copy')
        act.triggered.connect(self.copy)
        act.setShortcut('Ctrl+C')
        act.setIcon(QIcon(resourcePath('img/content-copy.png')))

        copyMenu = menu.addMenu('Advanced Copy')

        # Note: I cant use the actions defined above because they end up getting garbage
        # collected
        iconlstrip = QIcon(resourcePath('img/content-duplicate.png'))
        act = QAction(iconlstrip, 'Copy lstrip', copyMenu)
        act.setShortcut('Ctrl+Shift+C')
        act.triggered.connect(self.copyLstrip)
        copyMenu.addAction(act)

        icon = QIcon(resourcePath('img/content-copy.png'))
        act = QAction(icon, 'Copy Tabs to Spaces', copyMenu)
        act.setShortcut('Ctrl+Shift+Space')
        act.triggered.connect(self.copySpaceIndentation)
        copyMenu.addAction(act)

        act = menu.addAction('Paste')
        act.triggered.connect(self.paste)
        act.setShortcut('Ctrl+V')
        act.setIcon(QIcon(resourcePath('img/content-paste.png')))

        menu.addSeparator()

        act = menu.addAction('Copy Line Reference')
        act.triggered.connect(self.copyLineReference)
        act.setIcon(QIcon(resourcePath('img/content-copy.png')))

        menu.addSeparator()

        act = menu.addAction('Comment Toggle')
        act.triggered.connect(self.commentToggle)
        act.setShortcut("Ctrl+/")
        act.setIcon(QIcon(resourcePath('img/comment-edit.png')))

        menu.addSeparator()

        act = menu.addAction('To Lowercase')
        act.triggered.connect(self.toLower)
        # act.setShortcut('Ctrl+L')
        act.setIcon(QIcon(resourcePath('img/format-letter-case-lower.png')))
        act = menu.addAction('To Uppercase')
        act.triggered.connect(self.toUpper)
        # act.setShortcut('Ctrl+U')
        act.setIcon(QIcon(resourcePath('img/format-letter-case-upper.png')))

        menu.addSeparator()

        submenu = menu.addMenu('View as...')
        submenu.setIcon(QIcon(resourcePath('img/eye-check.png')))
        lg = self.language()
        act = submenu.addAction('Plain Text')
        if lg == "":
            act.setIcon(QIcon(resourcePath('img/check-bold.png')))
        submenu.addSeparator()

        for language in lang.languages():
            act = submenu.addAction(language)
            if language == lg:
                act.setIcon(QIcon(resourcePath('img/check-bold.png')))

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

        if popup:
            menu.popup(self._clickPos)
        return menu

    def showEvent(self, event):
        super(DocumentEditor, self).showEvent(event)
        # Update the colorScheme after the stylesheet has been fully loaded.
        self.updateColorScheme()

    def showFolding(self):
        return self.folding() != self.NoFoldStyle

    def showLineNumbers(self):
        return self.marginLineNumbers(self.SymbolMargin)

    def showSmartHighlighting(self):
        return self.delayable_engine.delayable_enabled('smart_highlight')

    def showWhitespaces(self):
        return self.whitespaceVisibility() == QsciScintilla.WsVisible

    def smartHighlightingRegEx(self):
        return self._smartHighlightingRegEx

    def toLower(self):
        with undo_step(self):
            lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
            text = self.selectedText().lower()
            self.removeSelectedText()
            self.insert(text)
            self.setSelection(lineFrom, indexFrom, lineTo, indexTo)

    def toggleFolding(self):
        self.foldAll(QApplication.instance().keyboardModifiers() == Qt.ShiftModifier)

    def toUpper(self):
        with undo_step(self):
            lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
            text = self.selectedText().upper()
            self.removeSelectedText()
            self.insert(text)
            self.setSelection(lineFrom, indexFrom, lineTo, indexTo)

    def updateColorScheme(self):
        """Sets the DocumentEditor's lexer colors, see colorScheme for a compatible
        dict
        """
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
        except Exception:
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
                text = (
                    'Line: {sline} Pos: {spos} To Line: {eline} '
                    'Pos: {epos} Line Count: {lineCount}'
                )
                text = text.format(
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

    def indentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        with undo_step(self):
            for line in range(lineFrom, lineTo + 1):
                self.indent(line)

    def unindentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        with undo_step(self):
            for line in range(lineFrom, lineTo + 1):
                self.unindent(line)

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
            # If used in LoggerWindow, use that wheel event
            # May not want to import LoggerWindow, so perhaps
            # check by str(type())
            # if isinstance(self.window(), "LoggerWindow"):
            if "LoggerWindow" in str(type(self.window())):
                self.window().wheelEvent(event)
                return

            font = self.documentFont
            marginsFont = self.marginsFont()
            lexer = self.lexer()
            if lexer:
                font = lexer.font(0)
            try:
                # Qt5 support
                delta = event.angleDelta().y()
            except Exception:
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
        """This is subclassed so we can create a Property of it"""
        return super(DocumentEditor, self).edgeColor()

    def setEdgeColor(self, color):
        """This is subclassed so we can create a Property of it"""
        super(DocumentEditor, self).setEdgeColor(color)

    # Because foreground and background must be set together, this cant use
    # QtPropertyInit
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

    # Handle Stylesheet colors for properties that are built into QsciScintilla but dont
    # have getters.
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
    paperSmartHighlight = QtPropertyInit(
        '_paperSmartHighlight', QColor(155, 255, 155, 75)
    )
    paperDecorator = QtPropertyInit('_paperDecorator', _defaultPaper)
