from __future__ import absolute_import, print_function

import os
import tempfile
import textwrap

from Qt.QtCore import Qt
from Qt.QtWidgets import QStackedWidget

from ..prefs import prefs_path


class WorkboxMixin(object):
    _warning_text = None
    """When a user is picking this Workbox class, show a warning with this text."""

    def __init__(
        self, parent=None, tempfile=None, filename=None, core_name=None, **kwargs
    ):
        super(WorkboxMixin, self).__init__(parent=parent, **kwargs)
        self._filename_pref = filename
        self._is_loaded = False
        self._tempdir = None
        self._tempfile = tempfile
        self.core_name = core_name

    def __auto_complete_enabled__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_auto_complete_enabled__(self, state):
        raise NotImplementedError("Mixin method not overridden.")

    def __clear__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __close__(self):
        """Called just before the LoggerWindow is closed to allow for workbox cleanup"""

    def __comment_toggle__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __console__(self):
        """Returns the PrEditor console to code is executed in if set."""
        try:
            return self._console
        except AttributeError:
            self._console = None

    def __set_console__(self, console):
        self._console = console

    def __copy_indents_as_spaces__(self):
        """When copying code, should it convert leading tabs to spaces?"""
        raise NotImplementedError("Mixin method not overridden.")

    def __set_copy_indents_as_spaces__(self, state):
        raise NotImplementedError("Mixin method not overridden.")

    def __cursor_position__(self):
        """Returns the line and index of the cursor."""
        raise NotImplementedError("Mixin method not overridden.")

    def __set_cursor_position__(self, line, index):
        """Set the cursor to this line number and index"""
        raise NotImplementedError("Mixin method not overridden.")

    def __exec_all__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __exec_selected__(self, truncate=True):
        txt, line = self.__selected_text__()

        # Remove any leading white space shared across all lines
        txt = textwrap.dedent(txt)

        # Get rid of pesky \r's
        txt = self.__unix_end_lines__(txt)

        # Make workbox line numbers match the workbox line numbers, by adding
        # the appropriate number of newlines to mimic it's original position in
        # the workbox.
        txt = '\n' * line + txt

        # execute the code
        filename = self.__workbox_filename__(selection=True)
        ret, was_eval = self.__console__().executeString(txt, filename=filename)
        if was_eval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(ret)
            self.__console__().startOutputLine()
            if truncate:
                print(self.truncate_middle(ret, 100))
            else:
                print(ret)

    def __file_monitoring_enabled__(self):
        """Returns True if this workbox supports file monitoring.
        This allows the editor to update its text if the linked
        file is changed on disk."""
        return False

    def __set_file_monitoring_enabled__(self, state):
        pass

    def __filename__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __font__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_font__(self, font):
        raise NotImplementedError("Mixin method not overridden.")

    def __group_tab_index__(self):
        """Returns the group and editor indexes if this editor is being used in
        a GroupTabWidget.

        Returns:
            group, editor: The index of the group tab and the index of the
                editor's tab under the group tab. -1 is returned for both if
                this isn't parent to a GroupTabWidget.
        """
        group = editor = -1

        # This widget's parent should be a stacked widget and we can get the
        # editors index from that
        stack = self.parent()
        if stack and isinstance(stack, QStackedWidget):
            editor = stack.indexOf(self)
        else:
            return -1, -1

        # The parent of the stacked widget should be a tab widget, get its parent
        editor_tab = stack.parent()
        if not editor_tab:
            return -1, -1

        # This should be a stacked widget under a tab widget, we can get group
        # from it without needing to get its parent.
        stack = editor_tab.parent()
        if stack and isinstance(stack, QStackedWidget):
            group = stack.indexOf(editor_tab)

        return group, editor

    def __workbox_filename__(self, selection=False):
        title = "WorkboxSelection" if selection else "Workbox"
        group, editor = self.__group_tab_index__()
        if group == -1 or editor == -1:
            return '<{}>'.format(title)
        else:
            return '<{}>:{},{}'.format(title, group, editor)

    def __goto_line__(self, line):
        raise NotImplementedError("Mixin method not overridden.")

    def __indentations_use_tabs__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_indentations_use_tabs__(self, state):
        raise NotImplementedError("Mixin method not overridden.")

    def __insert_text__(self, txt):
        raise NotImplementedError("Mixin method not overridden.")

    def __load__(self, filename):
        raise NotImplementedError("Mixin method not overridden.")

    def __margins_font__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_margins_font__(self, font):
        raise NotImplementedError("Mixin method not overridden.")

    def __marker_add__(self, line):
        raise NotImplementedError("Mixin method not overridden.")

    def __marker_clear_all__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __reload_file__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __remove_selected_text__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __save__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __selected_text__(self, start_of_line=False, selectText=False):
        """Returns selected text or the current line of text, plus the line
        number of the begining of selection / cursor position.

        If text is selected, it is returned. If nothing is selected, returns the
        entire line of text the cursor is currently on.

        Args:
            start_of_line (bool, optional): If text is selected, include any
                leading text from the first line of the selection.
            selectText (bool): If expanding to the entire line from the cursor,
                indicates  whether to select that line of text

        Returns:
            str: The requested text
            line (int):  plus the line number of the beginning of selection / cursor
                position.
        """
        raise NotImplementedError("Mixin method not overridden.")

    def __tab_width__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_tab_width__(self, width):
        raise NotImplementedError("Mixin method not overridden.")

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
        raise NotImplementedError("Mixin method not overridden.")

    def __set_text__(self, txt):
        """Replace all of the current text with txt. This method should be overridden
        by sub-classes, and call super to mark the widget as having been loaded.
        If text is being set on the widget, it most likely should be marked as
        having been loaded.
        """
        self._is_loaded = True

    def truncate_middle(self, s, n, sep=' ... '):
        """Truncates the provided text to a fixed length, putting the sep in the middle.
        https://www.xormedia.com/string-truncate-middle-with-ellipsis/
        """
        if len(s) <= n:
            # string is already short-enough
            return s
        # half of the size, minus the seperator
        n_2 = int(n) // 2 - len(sep)
        # whatever's left
        n_1 = n - n_2 - len(sep)
        return '{0}{1}{2}'.format(s[:n_1], sep, s[-n_2:])

    @classmethod
    def __unix_end_lines__(cls, txt):
        """Replaces all windows and then mac line endings with unix line endings."""
        return txt.replace('\r\n', '\n').replace('\r', '\n')

    def __restore_prefs__(self, prefs):
        self._filename_pref = prefs.get('filename')
        self._tempfile = prefs.get('tempfile')

    def __save_prefs__(self, name, current=None):
        ret = {}
        # Hopefully the alphabetical sorting of this dict is preserved in py3
        # to make it easy to diff the json pref file if ever required.
        if current is not None:
            ret['current'] = current
        ret['filename'] = self._filename_pref
        ret['name'] = name
        ret['tempfile'] = self._tempfile

        if not self._is_loaded:
            return ret

        if self._filename_pref:
            self.__save__()
        else:
            if not self._tempfile:
                self._tempfile = self.__create_tempfile__()
                ret['tempfile'] = self._tempfile
            self.__write_file__(
                self.__tempfile__(create=True),
                self.__text__(),
            )

        return ret

    def __tempdir__(self, create=False):
        if self._tempdir is None:
            self._tempdir = prefs_path('workboxes', core_name=self.core_name)

        if create and not os.path.exists(self._tempdir):
            os.makedirs(self._tempdir)

        return self._tempdir

    def __tempfile__(self, create=False):
        if self._tempfile:
            return os.path.join(self.__tempdir__(create=create), self._tempfile)

    def __create_tempfile__(self):
        """Creates a temporary file to be used by `__tempfile__` to store this
        editors text contents stored in `__tempdir__`."""
        with tempfile.NamedTemporaryFile(
            prefix='workbox_',
            suffix='.py',
            dir=self.__tempdir__(create=True),
            delete=False,
        ) as fle:
            name = fle.name

        return os.path.basename(name)

    def __remove_tempfile__(self):
        """Removes `__tempfile__` if it is being used."""
        tempfile = self.__tempfile__()
        if tempfile and os.path.exists(tempfile):
            os.remove(tempfile)

    @classmethod
    def __open_file__(cls, filename):
        with open(filename) as fle:
            return fle.read()
        return ""

    @classmethod
    def __write_file__(cls, filename, txt):
        with open(filename, 'w') as fle:
            fle.write(txt)

    def __show__(self):
        if self._is_loaded:
            return

        self._is_loaded = True
        if self._filename_pref:
            self.__load__(self._filename_pref)
        elif self._tempfile:
            txt = self.__open_file__(self.__tempfile__())
            self.__set_text__(txt)

    def process_shortcut(self, event, run=True):
        """Check for workbox shortcuts and optionally call them.

        Args:
            event (QEvent): The keyPressEvent to process.
            run (bool, optional): Run the expected action if possible.

        Returns:
            str or False: Returns False if the key press was not handled, indicating
                that the subclass needs to handle it(or call super). If a known
                shortcut was detected, a string indicating the action is returned
                after running the action if enabled and supported.

        Known actions:
            __exec_selected__: If the user pressed Shift + Return or pressed the
                number pad enter key calling `__exec_selected__`.
        """

        # Number pad enter, or Shift + Return pressed, execute selected
        # Ctrl+ Shift+Return pressed, execute selected without truncating output
        if run:
            # self.__exec_selected__()
            # Collect what was pressed
            key = event.key()
            modifiers = event.modifiers()

            # Determine which relevant combos are pressed
            ret = key == Qt.Key_Return
            enter = key == Qt.Key_Enter
            shift = modifiers == Qt.ShiftModifier
            ctrlShift = modifiers == Qt.ControlModifier | Qt.ShiftModifier

            # Determine which actions to take
            evalTrunc = enter or (ret and shift)
            evalNoTrunc = ret and ctrlShift

            if evalTrunc:
                # Execute with truncation
                self.window().execSelected()
            elif evalNoTrunc:
                # Execute without truncation
                self.window().execSelected(truncate=False)

        if evalTrunc or evalNoTrunc:
            if self.window().uiAutoPromptACT.isChecked():
                self.__console__().startInputLine()
            return '__exec_selected__'
        else:
            return False
