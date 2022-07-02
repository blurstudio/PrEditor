from __future__ import print_function
from __future__ import absolute_import
import re

from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction

from .. import core, resourcePath
from ..scintilla.documenteditor import DocumentEditor
from ..scintilla.finddialog import FindDialog


class WorkboxWidget(DocumentEditor):
    def __init__(self, parent, console=None, delayable_engine='default'):
        self._console = console
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

    def console(self):
        return self._console

    def execAll(self):
        """re-implement the DocumentEditor.exec_ method to run this code without saving"""
        txt = self.toUnixLineEndings(self.text()).rstrip()
        idx = self.parent().indexOf(self)
        filename = '<WorkboxWidget>:{}'.format(idx)
        self.console().executeString(txt, filename=filename)

    def execSelected(self):
        # Get the first line number of the selection so we can report correct line
        # numbers. If text is selected use it, otherwise use the text of the current
        # line.
        txt = self.selectedText()
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
        ret, wasEval = self.console().executeString(txt, filename=filename)
        if wasEval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(ret)
            self.console().startOutputLine()
            print(self.truncate_middle(ret, 100))

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
        n_2 = int(n) / 2 - len(sep)
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
                self.execSelected()

                if self.window().uiAutoPromptACT.isChecked():
                    self.console().startInputLine()
            else:
                DocumentEditor.keyPressEvent(self, event)

    def initShortcuts(self):
        """Use this to set up shortcuts when the DocumentEditor"""
        icon = QIcon(resourcePath('img/logger/find.png'))
        self.uiFindACT = QAction(icon, 'Find...', self)
        self.uiFindACT.setShortcut("Ctrl+F")
        self.addAction(self.uiFindACT)

        icon = QIcon(resourcePath('img/logger/previous.png'))
        self.uiFindPrevACT = QAction(icon, 'Find Prev', self)
        self.uiFindPrevACT.setShortcut("Ctrl+F3")
        self.addAction(self.uiFindPrevACT)

        icon = QIcon(resourcePath('img/logger/next.png'))
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
            and not self._searchFlags & self.SearchOptions.QRegExp
        ):
            txt = self.selectedText()
            if txt:
                self._searchText = txt
        return self._searchText

    def selectedText(self):
        return self.regex.split(super(WorkboxWidget, self).selectedText())[0]

    def setConsole(self, console):
        self._console = console

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def setSearchText(self, txt):
        self._searchText = txt

    def setWorkboxFont(self, font):
        if self.lexer():
            self.lexer().setFont(font)
        else:
            self.setFont(font)

    @classmethod
    def toUnixLineEndings(cls, txt):
        """Replaces all windows and then mac line endings with unix line endings."""
        return txt.replace('\r\n', '\n').replace('\r', '\n')
