from __future__ import absolute_import, print_function

import re
import time

from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction

from .. import core, resourcePath
from ..gui.workbox_mixin import WorkboxMixin
from ..scintilla.documenteditor import DocumentEditor, SearchOptions
from ..scintilla.finddialog import FindDialog


class WorkboxWidget(DocumentEditor, WorkboxMixin):
    def __init__(self, parent, console=None, delayable_engine='default'):
        self.__set_console__(console)
        self._searchFlags = 0
        self._searchText = ''
        self._searchDialog = None

        # initialize the super class
        super(WorkboxWidget, self).__init__(parent, delayable_engine=delayable_engine)

        # Store the software name so we can handle custom keyboard shortcuts bassed on
        # software
        self._software = core.objectName()
        self.regex = re.compile(r'\s+$')
        self.initShortcuts()
        self.setLanguage('Python')

    def __auto_complete_enabled__(self):
        return self.autoCompletionSource() == self.AcsAll

    def __set_auto_complete_enabled__(self, state):
        state = self.AcsAll if state else self.AcsNone
        self.setAutoCompletionSource(state)

    def __clear__(self):
        self.clear()

    def __comment_toggle__(self):
        self.commentToggle()

    def __copy_indents_as_spaces__(self):
        return self.copyIndentsAsSpaces

    def __set_copy_indents_as_spaces__(self, state):
        self.copyIndentsAsSpaces = state

    def __cursor_position__(self):
        """Returns the line and index of the cursor."""
        return self.getCursorPosition()

    def __set_cursor_position__(self, line, index):
        """Set the cursor to this line number and index"""
        self.setCursorPosition(line, index)

    def __exec_all__(self):
        """re-implement the DocumentEditor.exec_ method to run this code without saving"""
        txt = self.toUnixLineEndings(self.text()).rstrip()
        idx = self.parent().indexOf(self)
        filename = '<WorkboxWidget>:{}'.format(idx)
        self.__console__().executeString(txt, filename=filename)

    def __exec_selected__(self):
        # Get the first line number of the selection so we can report correct line
        # numbers. If text is selected use it, otherwise use the text of the current
        # line.
        txt = self.__selected_text__()
        if txt:
            line, s, end, e = self.getSelection()
        else:
            line, index = self.getCursorPosition()
            txt = self.text(line)

        # Get rid of pesky \r's
        txt = self.toUnixLineEndings(txt)

        stripCommon = True
        if stripCommon:
            lines = txt.split('\n')
            rep = self.findLeadingWhitespace(lines)
            if rep:
                lines = self.stripLeadingWhitespace(lines, rep)
            txt = u'\n'.join(lines)

        # Make workbox line numbers match the workbox line numbers.
        txt = '\n' * line + txt

        # execute the code
        idx = self.parent().indexOf(self)
        filename = '<WorkboxSelection>:{}'.format(idx)
        ret, wasEval = self.__console__().executeString(txt, filename=filename)
        if wasEval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(ret)
            self.__console__().startOutputLine()
            print(self.truncate_middle(ret, 100))

    def __file_monitoring_enabled__(self):
        return self._fileMonitoringActive

    def __set_file_monitoring_enabled__(self, state):
        self.setAutoReloadOnChange(state)
        self.enableFileWatching(state)

    def __filename__(self):
        return self.filename()

    def __font__(self):
        if self.lexer():
            return self.lexer().font(0)
        else:
            self.font()

    def __set_font__(self, font):
        self.documentFont = font
        if self.lexer():
            self.lexer().setFont(font)
        else:
            self.setFont(font)

    def __goto_line__(self, line):
        self.goToLine(line)

    def __indentations_use_tabs__(self):
        return self.indentationsUseTabs()

    def __set_indentations_use_tabs__(self, state):
        self.setIndentationsUseTabs(state)

    def __insert_text__(self, txt):
        self.insert(txt)

    def __load__(self, filename):
        self.load(filename)

    def __margins_font__(self):
        return self.marginsFont()

    def __set_margins_font__(self, font):
        self.setMarginsFont(font)

    def __marker_add__(self, line):
        try:
            marker = self._marker
        except AttributeError:
            self._marker = self.markerDefine(self.Circle)
            marker = self._marker
        self.markerAdd(line, marker)

    def __marker_clear_all__(self):
        try:
            self.markerDeleteAll(self._marker)
        except AttributeError:
            # self._marker has not been created yet
            pass

    def __reload_file__(self):
        # loading the file too quickly misses any changes
        time.sleep(0.1)
        font = self.__font__()
        self.reloadChange()
        self.__set_font__(font)

    def __remove_selected_text__(self):
        self.removeSelectedText()

    def __save__(self):
        self.save()

    def __selected_text__(self):
        return self.regex.split(self.selectedText())[0]

    def __text__(self, line=None, start=None, end=None):
        """Returns the text in this widget, possibly limited in scope.

        Note: Only pass line, or (start and end) to this method.

        Args:
            line (int, optional): Limit the returned scope to just this line number.
            start (int, optional): Limit the scope to text between this and end.
            end (int, optional): Limit the scope to text between start and this.

        Returns:
            str: The requested text.
        """
        if line:
            return self.text(line)
        elif (start is None) != (end is None):
            raise ValueError('You must pass start and end if you pass either.')
        elif start is not None:
            self.text(start, end)
        return self.text()

    def __set_text__(self, txt):
        """Replace all of the current text with txt."""
        self.setText(txt)

    def findLeadingWhitespace(self, lines):
        # Find the first line that has text that isn't a comment
        # We will then remove the leading whitespace from that line
        # from all subsequent lines
        for s in lines:
            m = re.match(r'(\s*)([^#])', s)
            # Only use leading whitespace if the match has text
            if m and m.group(2).strip():
                return m.group(1)
        return ''

    def stripLeadingWhitespace(self, lines, rep):
        newLines = []
        for line in lines:
            if not line:
                newLines.append(line)
                continue

            if line.startswith(rep):
                nl = line.replace(rep, '', 1)
                newLines.append(nl)
            else:
                raise IndentationError("Prefix Stripping Failed")
        return newLines

    def truncate_middle(self, s, n, sep=' ... '):
        # https://www.xormedia.com/string-truncate-middle-with-ellipsis/
        if len(s) <= n:
            # string is already short-enough
            return s
        # half of the size, minus the seperator
        n_2 = int(n) // 2 - len(sep)
        # whatever's left
        n_1 = n - n_2 - len(sep)
        return '{0}{1}{2}'.format(s[:n_1], sep, s[-n_2:])

    def keyPressEvent(self, event):
        if self._software == 'softimage':
            DocumentEditor.keyPressEvent(self, event)
        else:
            if event.key() == Qt.Key_Enter or (
                event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier
            ):
                self.__exec_selected__()

                if self.window().uiAutoPromptACT.isChecked():
                    self.__console__().startInputLine()
            else:
                DocumentEditor.keyPressEvent(self, event)

    def initShortcuts(self):
        """Use this to set up shortcuts when the DocumentEditor"""
        icon = QIcon(resourcePath('img/text-search-variant.png'))
        self.uiFindACT = QAction(icon, 'Find...', self)
        self.uiFindACT.setShortcut("Ctrl+F")
        self.addAction(self.uiFindACT)

        icon = QIcon(resourcePath('img/skip-previous.png'))
        self.uiFindPrevACT = QAction(icon, 'Find Prev', self)
        self.uiFindPrevACT.setShortcut("Ctrl+F3")
        self.addAction(self.uiFindPrevACT)

        icon = QIcon(resourcePath('img/skip-next.png'))
        self.uiFindNextACT = QAction(icon, 'Find Next', self)
        self.uiFindNextACT.setShortcut("F3")
        self.addAction(self.uiFindNextACT)

        self.uiSelectCurrentLineACT = QAction(icon, 'Select Line', self)
        self.uiSelectCurrentLineACT.triggered.connect(self.expandCursorToLineSelection)
        self.uiSelectCurrentLineACT.setShortcut('Ctrl+L')
        self.addAction(self.uiSelectCurrentLineACT)

        # create the search dialog and connect actions
        self._searchDialog = FindDialog(self)
        self._searchDialog.setAttribute(Qt.WA_DeleteOnClose, False)
        self.uiFindACT.triggered.connect(
            lambda: self._searchDialog.search(self.searchText())
        )
        self.uiFindPrevACT.triggered.connect(
            lambda: self.findPrev(self.searchText(), self.searchFlags())
        )
        self.uiFindNextACT.triggered.connect(
            lambda: self.findNext(self.searchText(), self.searchFlags())
        )

    def searchFlags(self):
        return self._searchFlags

    def searchText(self):
        if not self._searchDialog:
            return ''
        # refresh the search text unless we are using regular expressions
        if (
            not self._searchDialog.isVisible()
            and not self._searchFlags & SearchOptions.QRegExp
        ):
            txt = self.__selected_text__()
            if txt:
                self._searchText = txt
        return self._searchText

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def setSearchText(self, txt):
        self._searchText = txt

    @classmethod
    def toUnixLineEndings(cls, txt):
        """Replaces all windows and then mac line endings with unix line endings."""
        return txt.replace('\r\n', '\n').replace('\r', '\n')
