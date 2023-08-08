from __future__ import absolute_import

import logging

from pyqode.core import api, modes, panels
from pyqode.core.api.utils import TextHelper
from pyqode.core.backend import server
from Qt.QtGui import QFont, QTextCursor

from ..workbox_mixin import WorkboxMixin

logger = logging.getLogger(__name__)


class WorkboxQode(WorkboxMixin, api.CodeEdit):
    """A multi-line code editor based on pyQode.

    TODO: Implement a CommentsMode that properly indents comments
    """

    def __init__(
        self, parent=None, console=None, delayable_engine='default', core_name=None
    ):
        # super(WorkboxQode, self).__init__(parent=parent, core_name=core_name)
        WorkboxMixin.__init__(self, core_name=core_name)
        api.CodeEdit.__init__(self, parent=parent)
        self._filename = None
        self.__set_console__(console)

        # Start the qode backend
        # TODO: Figure out how to close the backends when LoggerWindow is closed
        # TODO: Figure out if we can reuse(share) backends
        self.backend.start(server.__file__)

        # append some modes and panels
        # self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.CommentsMode())
        self.modes.append(modes.PygmentsSyntaxHighlighter(self.document()))
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        self.modes.append(modes.IndenterMode())
        self.modes.append(modes.ExtendedSelectionMode())
        # TODO: This should be enabled/disabled based on the LoggerWindow's setting
        self.__set_auto_complete_enabled__(True)

        # Add panels
        self.panels.append(panels.SearchAndReplacePanel(), api.Panel.Position.BOTTOM)
        self._line_num = panels.LineNumberPanel()
        self.panels.append(self._line_num, api.Panel.Position.LEFT)

        # Create a rule on the right side at 80 characters
        margin = self.modes.append(modes.RightMarginMode())
        margin.position = 80

    def _mode(self, name, default=None, create=False):
        """Get mode from pyQode, if mode is not installed, returns default.

        Args:
            name: Class of a mode module, or its name to return. If crate is True
                you should only pass a mode class.
            default (optional): If the mode has not been installed and create
                is False, return this value.
            create (bool, optional):
        """
        # Attempt to get the mode, this raises an exception if its not installed
        try:
            return self.modes.get(name)
        except (NameError, KeyError):
            # If the mode is not installed but the user wants to create it, do so
            if create:
                mode = name()
                self.modes.append(mode)
                return mode
        # Otherwise return the default value.
        return default

    def __auto_complete_enabled__(self):
        mode = self._mode(modes.CodeCompletionMode)
        if mode:
            return mode.enabled
        return False

    def __set_auto_complete_enabled__(self, state):
        mode = self._mode(modes.CodeCompletionMode, create=state)
        if mode:
            mode.enabled = state

    def __clear__(self):
        self.clear()

    def __comment_toggle__(self):
        mode = self._mode(modes.CommentsMode)
        if mode:
            mode.comment()

    def __copy_indents_as_spaces__(self):
        """When copying code, should it convert leading tabs to spaces?"""
        return False

    def __set_copy_indents_as_spaces__(self, state):
        logger.debug(
            "WorkboxQode does not support converting indents to spaces on copy."
        )

    def __cursor_position__(self):
        """Returns the line and index of the cursor."""
        cursor = self.textCursor()
        sc = QTextCursor(self.document())
        sc.setPosition(cursor.selectionStart())
        return sc.blockNumber(), sc.positionInBlock()

    def __set_cursor_position__(self, line, index):
        """Set the cursor to this line number and index"""
        cursor = self.textCursor()
        text_block = cursor.document().findBlockByLineNumber(line)
        # TODO: This generates warnings like this(May be due to __cursor_position__):
        # `QTextCursor::setPosition: Position '10' out of range`
        cursor.setPosition(text_block.position() + index, QTextCursor.MoveAnchor)

    def __exec_all__(self):
        txt = self.__text__().rstrip()
        filename = self.__workbox_filename__()
        self.__console__().executeString(txt, filename=filename)

    def __filename__(self):
        return self.file.path

    def __font__(self):
        font = self.font()
        # Note: pyQode keeps track of the family and size values independent
        # of the QFont object, so make sure the return uses the correct values
        font.setFamily(self.font_name)
        font.setPointSize(self.font_size)
        return font

    def __set_font__(self, font):
        # Set the font settings that pyQode doesn't track independent of font
        super(WorkboxQode, self).setFont(font)
        # Note: Set the values pyQode tracks independently of font
        self.font_name = font.family()
        self.font_size = font.pointSize()

    def __goto_line__(self, line):
        helper = TextHelper(self)
        return helper.goto_line(line - 1, move=True)

    def __indentations_use_tabs__(self):
        return not self.use_spaces_instead_of_tabs

    def __set_indentations_use_tabs__(self, state):
        # TODO: Figure out why the tab length of actual tabs is so short
        self.use_spaces_instead_of_tabs = not state

    def __insert_text__(self, txt):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(txt)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def __load__(self, filename):
        self.file.open(filename)

    def __margins_font__(self):
        # This class doesn't support custom margin font's
        return QFont()

    def __set_margins_font__(self, font):
        # This class doesn't support custom margin font's
        pass

    def __remove_selected_text__(self):
        self.delete()

    def __save__(self):
        self.file.save()

    def __selected_text__(self, start_of_line=False):
        """Returns selected text or the current line of text.

        If text is selected, it is returned. If nothing is selected, returns the
        entire line of text the cursor is currently on.

        Args:
            start_of_line (bool, optional): If text is selected, include any
                leading text from the first line of the selection.
        """
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

    def __tab_width__(self):
        return self.tab_length

    def __set_tab_width__(self, width):
        self.tab_length = width

    def __text__(self, line=None, start=None, end=None):
        return self.toPlainText()

    def __set_text__(self, txt):
        super(WorkboxQode, self).__set_text__(txt)
        self.setPlainText(txt, "text/x-python", "cp1252")
