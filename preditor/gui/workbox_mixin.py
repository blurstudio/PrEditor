from __future__ import absolute_import

import os
import tempfile
import textwrap

from ..prefs import prefs_path


class WorkboxMixin(object):
    def __init__(self, tempfile=None, filename=None):
        self._filename_pref = filename
        self._is_loaded = False
        self._tempdir = None
        self._tempfile = tempfile

    def __auto_complete_enabled__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_auto_complete_enabled__(self, state):
        raise NotImplementedError("Mixin method not overridden.")

    def __clear__(self):
        raise NotImplementedError("Mixin method not overridden.")

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

    def __exec_selected__(self):
        txt = self.__selected_text__()

        # Remove any leading white space shared across all lines
        txt = textwrap.dedent(txt)

        # Get rid of pesky \r's
        txt = self.__unix_end_lines__(txt)

        # Make workbox line numbers match the workbox line numbers.
        line, _ = self.__cursor_position__()
        txt = '\n' * line + txt

        # execute the code
        idx = self.parent().indexOf(self)
        filename = '<WorkboxSelection>:{}'.format(idx)
        ret, was_eval = self.__console__().executeString(txt, filename=filename)
        if was_eval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(ret)
            self.__console__().startOutputLine()
            print(self.truncate_middle(ret, 100))

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

    def __selected_text__(self, start_of_line=False):
        """Returns selected text or the current line of text.

        If text is selected, it is returned. If nothing is selected, returns the
        entire line of text the cursor is currently on.

        Args:
            start_of_line (bool, optional): If text is selected, include any
                leading text from the first line of the selection.
        """
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
            self._tempdir = prefs_path('workboxes')

        if create and not os.path.exists(self._tempdir):
            os.makedirs(self._tempdir)

        return self._tempdir

    def __tempfile__(self, create=False):
        if self._tempfile:
            return os.path.join(self.__tempdir__(create=create), self._tempfile)

    def __create_tempfile__(self):
        with tempfile.NamedTemporaryFile(
            prefix='workbox_',
            suffix='.py',
            dir=self.__tempdir__(create=True),
            delete=False,
        ) as fle:
            name = fle.name

        return os.path.basename(name)

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
