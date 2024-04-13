from __future__ import absolute_import

import logging

from Qt.QtGui import QFont, QFontMetrics, QTextCursor
from Qt.QtWidgets import QTextEdit

from .codehighlighter import CodeHighlighter
from .workbox_mixin import WorkboxMixin

logger = logging.getLogger(__name__)


class WorkboxTextEdit(WorkboxMixin, QTextEdit):
    """A very simple multi-line text editor without any bells and whistles.

    It's better than nothing, but not by much.
    """

    _warning_text = (
        "This is a bare bones workbox, if you have another option, it's probably"
        "a better option."
    )

    def __init__(
        self, parent=None, console=None, delayable_engine='default', core_name=None
    ):
        super(WorkboxTextEdit, self).__init__(parent=parent, core_name=core_name)
        self._filename = None
        self.__set_console__(console)
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')
        self.uiCodeHighlighter = highlight

    def __auto_complete_enabled__(self):
        pass

    def __set_auto_complete_enabled__(self, state):
        pass

    def __copy_indents_as_spaces__(self):
        """When copying code, should it convert leading tabs to spaces?"""
        return False

    def __set_copy_indents_as_spaces__(self, state):
        logger.info(
            "WorkboxTextEdit does not support converting indents to spaces on copy."
        )

    def __cursor_position__(self):
        """Returns the line and index of the cursor."""
        cursor = self.textCursor()
        sc = QTextCursor(self.document())
        sc.setPosition(cursor.selectionStart())
        return sc.blockNumber(), sc.positionInBlock()

    def __exec_all__(self):
        txt = self.__text__().rstrip()
        filename = self.__workbox_filename__()
        self.__console__().executeString(txt, filename=filename)

    def __font__(self):
        return self.font()

    def __set_font__(self, font):
        metrics = QFontMetrics(font)
        self.setTabStopDistance(metrics.width(" ") * 4)
        super(WorkboxTextEdit, self).setFont(font)

    def __goto_line__(self, line):
        cursor = QTextCursor(self.document().findBlockByLineNumber(line - 1))
        self.setTextCursor(cursor)

    def __indentations_use_tabs__(self):
        return True

    def __set_indentations_use_tabs__(self, state):
        logger.info("WorkboxTextEdit does not support using spaces for tabs.")

    def __load__(self, filename):
        self._filename = filename
        txt = self.__open_file__(self._filename)
        self.__set_text__(txt)

    def __margins_font__(self):
        return QFont()

    def __set_margins_font__(self, font):
        pass

    def __tab_width__(self):
        # TODO: Implement custom tab widths
        return 4

    def __text__(self, line=None, start=None, end=None):
        return self.toPlainText()

    def __set_text__(self, text):
        super(WorkboxTextEdit, self).__set_text__(text)
        self.setPlainText(text)

    def __selected_text__(self, start_of_line=False, selectText=False):
        cursor = self.textCursor()

        # Get starting line number. Must set the cursor's position to the start of the
        # selection, otherwise we may instead get the ending line number.
        tempCursor = self.textCursor()
        tempCursor.setPosition(tempCursor.selectionStart())
        line = tempCursor.block().firstLineNumber()

        # If no selection, return the current line
        if cursor.selection().isEmpty():
            text = cursor.block().text()

            selectText = self.window().uiSelectTextACT.isChecked() or selectText
            if selectText:
                cursor.select(QTextCursor.LineUnderCursor)
                self.setTextCursor(cursor)

            return text, line

        # Otherwise return the selected text
        if start_of_line:
            sc = QTextCursor(self.document())
            sc.setPosition(cursor.selectionStart())
            sc.movePosition(cursor.StartOfLine, sc.MoveAnchor)
            sc.setPosition(cursor.selectionEnd(), sc.KeepAnchor)

            return sc.selection().toPlainText(), line

        return self.textCursor().selection().toPlainText(), line

    def keyPressEvent(self, event):
        if self.process_shortcut(event):
            return
        else:
            super(WorkboxTextEdit, self).keyPressEvent(event)
