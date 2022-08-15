import logging

from Qt.QtCore import Qt
from Qt.QtGui import QFont, QFontMetrics, QTextCursor
from Qt.QtWidgets import QTextEdit

from .codehighlighter import CodeHighlighter
from .workbox_mixin import WorkboxMixin

logger = logging.getLogger(__name__)


class WorkboxTextEdit(QTextEdit, WorkboxMixin):
    """A very simple multi-line text editor without any bells and whistles.

    It's better than nothing, but not by much.
    """

    def __init__(self, console, parent=None, delayable_engine='default'):
        super(WorkboxTextEdit, self).__init__(parent=parent)
        self.__set_console__(console)
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')
        self.uiCodeHighlighter = highlight

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

    def __exec_all__(self, idx=None):
        txt = self.__text__().rstrip()
        filename = '<Workbox>:{}'.format(idx)
        self.__console__().executeString(txt, filename=filename)

    def __font__(self):
        return self.font()

    def __set_font__(self, font):
        metrics = QFontMetrics(font)
        self.setTabStopDistance(metrics.width(" ") * 4)
        super(WorkboxTextEdit, self).setFont(font)

    def __indentations_use_tabs__(self):
        return True

    def __set_indentations_use_tabs__(self, state):
        logger.info("WorkboxTextEdit does not support using spaces for tabs.")

    def __margins_font__(self):
        return QFont()

    def __set_margins_font__(self, font):
        pass

    def __text__(self):
        return self.toPlainText()

    def __set_text__(self, text):
        self.setPlainText(text)

    def __selected_text__(self, start_of_line=False):
        cursor = self.textCursor()

        # If no selection, return the current line
        if cursor.selection().isEmpty():
            return cursor.block().text()

        # Otherwise return the selected text
        if start_of_line:
            sc = QTextCursor(self.document())
            sc.setPosition(cursor.selectionStart())
            sc.movePosition(cursor.StartOfLine, sc.MoveAnchor)
            sc.setPosition(cursor.selectionEnd(), sc.KeepAnchor)
            return sc.selection().toPlainText()

        return self.textCursor().selection().toPlainText()

    def keyPressEvent(self, event):
        # If number pad enter key or Shift and keyboard return key
        # are used run selected text.
        if event.key() == Qt.Key_Enter or (
            event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier
        ):
            self.__exec_selected__()
        else:
            super(WorkboxTextEdit, self).keyPressEvent(event)