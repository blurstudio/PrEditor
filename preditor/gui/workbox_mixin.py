from __future__ import absolute_import, print_function

import io
import os
import tempfile
import textwrap
from pathlib import Path

import chardet
from Qt.QtCore import Qt
from Qt.QtWidgets import QStackedWidget

from ..prefs import (
    VersionTypes,
    create_stamped_path,
    get_backup_version_info,
    get_full_path,
    get_prefs_dir,
    get_relative_path,
)


class WorkboxName(str):
    """The joined name of a workbox `group/workbox` with access to its parts.

    You may pass the group, workbox, or the fully formed workbox name:
        examples:
            workboxName = WorkboxName("Group01", "Workbox05")
            workboxName = WorkboxName("Group01/Workbox05")
    This subclass provides properties for the group and workbox values separately.
    """

    def __new__(cls, name, sub_name=None):
        if sub_name is not None:
            txt = "/".join((name, sub_name))
        else:
            txt = name
            try:
                name, sub_name = txt.split("/")
            except ValueError:
                msg = "A fully formed name, or a group and name, must be passed in."
                raise ValueError(msg) from None

        ret = super().__new__(cls, txt)
        # Preserve the imitable nature of str's by using properties without setters.
        ret._group = name
        ret._workbox = sub_name
        return ret

    @property
    def group(self):
        """The tab name of the group tab that contains the workbox."""
        return self._group

    @property
    def workbox(self):
        """The workbox of the tab for this workbox inside of the group."""
        return self._workbox


class WorkboxMixin(object):
    _warning_text = None
    """When a user is picking this Workbox class, show a warning with this text."""

    def __init__(
        self,
        parent=None,
        console=None,
        workbox_id=None,
        filename=None,
        backup_file=None,
        tempfile=None,
        delayable_engine='default',
        core_name=None,
        **kwargs,
    ):
        super(WorkboxMixin, self).__init__(parent=parent, **kwargs)
        self._is_loaded = False
        self._show_blank = False
        self._tempdir = None

        self.core_name = core_name

        self._tab_widget = parent

        self.__set_last_saved_text__("")
        # You would think we should also __set_last_workbox_name_ here, but we
        # wait until __show__ so that we know the tab exists, and has tabText
        self._last_workbox_name = None

        self.__set_orphaned_by_instance__(False)
        self.__set_changed_by_instance__(False)
        self._changed_saved = False

    def __set_last_saved_text__(self, text):
        """Store text as last_saved_text on this workbox so checking if if_dirty
        is quick.

        Args:
            text (str): The text to define as last_saved_text
        """
        self._last_saved_text = text
        self.__tab_widget__().tabBar().update()

    def __last_saved_text__(self):
        """Returns the last_saved_text on this workbox

        Returns:
            last_saved_text (str): The _last_saved_text on this workbox
        """
        return self._last_saved_text

    def __set_last_workbox_name__(self, name=None):
        """Store text as last_workbox_name on this workbox so checking if
        if_dirty is quick.

        Args:
            name (str): The name to define as last_workbox_name
        """
        if name is None:
            name = self.__workbox_name__(workbox=self)
        self._last_workbox_name = name

    def __last_workbox_name__(self):
        """Returns the last_workbox_name on this workbox

        Returns:
            last_workbox_name (str): The last_workbox_name on this workbox
        """
        return self._last_workbox_name

    def __tab_widget__(self):
        """Return the tab widget which contains this workbox

        Returns:
            GroupedTabWidget: The tab widget which contains this workbox
        """
        return self._tab_widget

    def __set_tab_widget__(self, tab_widget):
        """Set this workbox's _tab_widget to the provided tab_widget"""
        self._tab_widget = tab_widget

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
        txt, lineNum = self.__selected_text__()

        # Remove any leading white space shared across all lines
        txt = textwrap.dedent(txt)

        # Get rid of pesky \r's
        txt = self.__unix_end_lines__(txt)

        # Make workbox line numbers match the workbox line numbers, by adding
        # the appropriate number of newlines to mimic it's original position in
        # the workbox.
        txt = '\n' * lineNum + txt

        # execute the code
        title = self.__workbox_trace_title__(selection=True)
        ret, was_eval = self.__console__().executeString(txt, filename=title)
        if was_eval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(ret)
            self.__console__().startOutputLine()
            if truncate:
                print(self.__truncate_middle__(ret, 100))
            else:
                print(ret)

    def __file_monitoring_enabled__(self):
        """Returns True if this workbox supports file monitoring.
        This allows the editor to update its text if the linked
        file is changed on disk."""
        raise NotImplementedError("Mixin method not overridden.")

    def __set_file_monitoring_enabled__(self, state):
        """Enables/Disables open file change monitoring. If enabled, A dialog will pop
        up when ever the open file is changed externally. If file monitoring is
        disabled in the IDE settings it will be ignored.

        Returns:
            bool:
        """
        # if file monitoring is enabled and we have a file name then set up the file
        # monitoring
        raise NotImplementedError("Mixin method not overridden.")

    def __filename__(self):
        raise NotImplementedError("Mixin method not overridden.")

    def __set_filename__(self, filename):
        """Set this workboxes linked filename to the provided filename

        Args:
            filename (str): The filename to link to
        """
        self._filename = filename
        self._filename_pref = filename

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

    def __workbox_trace_title__(self, selection=False):
        title = "WorkboxSelection" if selection else "Workbox"
        group, editor = self.__group_tab_index__()
        if group == -1 or editor == -1:
            return '<{}>'.format(title)
        else:
            name = self.__workbox_name__()
            return '<{}>:{}'.format(title, name)

    def __workbox_name__(self, workbox=None):
        """Returns the name for this workbox or a given workbox.
        The name is the group tab text and the workbox tab text joined by a `/`"""
        workboxTAB = self.window().uiWorkboxTAB
        group_name = None
        workbox_name = None

        if workbox:
            grouped_tab_widget = workbox.__tab_widget__()
            for group_idx in range(workboxTAB.count()):
                # If a previous iteration determine workbox_name, bust out
                if workbox_name:
                    break
                # Check if current group is the workboxes parent group
                cur_group_widget = workboxTAB.widget(group_idx)
                if cur_group_widget == grouped_tab_widget:
                    group_name = workboxTAB.tabText(group_idx)

                    # Found the group, now find workbox
                    for workbox_idx in range(cur_group_widget.count()):
                        cur_workbox_widget = cur_group_widget.widget(workbox_idx)
                        if cur_workbox_widget == workbox:
                            workbox_name = cur_group_widget.tabText(workbox_idx)
                            break
        else:
            grouped = self.__tab_widget__()
            groupedTabBar = grouped.tabBar()

            idx = -1
            for idx in range(grouped.count()):
                if grouped.widget(idx) == self:
                    break
            workbox_name = groupedTabBar.tabText(idx)

            group = grouped.tab_widget()
            groupTabBar = group.tabBar()
            idx = -1
            for idx in range(group.count()):
                if group.widget(idx) == grouped:
                    break
            group_name = groupTabBar.tabText(idx)

        # If both found, construct workbox name
        if group_name and workbox_name:
            name = WorkboxName(group_name, workbox_name)
        else:
            name = WorkboxName("", "")
        return name

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

    def __is_dirty__(self):
        """Returns if this workbox has unsaved changes, either to it's contents
        or it's name.

        Returns:
            is_dirty (bool): Whether or not this workbox has unsaved changes
        """
        is_dirty = (
            self.__text__() != self.__last_saved_text__()
            or self.__workbox_name__(workbox=self) != self.__last_workbox_name__()
        )
        return is_dirty

    def __truncate_middle__(self, s, n, sep=' ... '):
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
        self._workbox_id = prefs.get('workbox_id')

    def __save_prefs__(self, current=None, saveLinkedFile=True, force=False):
        ret = {}

        # Hopefully the alphabetical sorting of this dict is preserved in py3
        # to make it easy to diff the json pref file if ever required.
        if current is not None:
            ret['current'] = current
        ret['filename'] = self._filename_pref
        ret['name'] = self.__workbox_name__().workbox
        ret['workbox_id'] = self._workbox_id
        if self._tempfile:
            ret['tempfile'] = self._tempfile

        if self._backup_file:
            ret['backup_file'] = get_relative_path(self.core_name, self._backup_file)

        if not self._is_loaded:
            return ret

        fullpath = get_full_path(
            self.core_name, self._workbox_id, backup_file=self._backup_file
        )

        time_str = None
        if self._changed_by_instance:
            time_str = self.window().latestTimeStrsForBoxesChangedViaInstance.get(
                self._workbox_id, None
            )

        if self._changed_saved:
            self.window().latestTimeStrsForBoxesChangedViaInstance.pop(
                self._workbox_id, None
            )
            self._changed_saved = False

        backup_exists = self._backup_file and Path(fullpath).is_file()
        if self.__is_dirty__() or not backup_exists or force:
            full_path = create_stamped_path(
                self.core_name, self._workbox_id, time_str=time_str
            )

            full_path = str(full_path)
            self.__write_file__(full_path, self.__text__())

            self._backup_file = get_relative_path(self.core_name, full_path)
            ret['backup_file'] = self._backup_file

            if time_str:
                self._changed_saved = True

        if time_str:
            self.__set_changed_by_instance__(False)
        if self.window().boxesOrphanedViaInstance.pop(self._workbox_id, None):
            self.__set_orphaned_by_instance__(False)

        # If workbox is linked to file on disk, save it
        if self._filename_pref and saveLinkedFile:
            self._filename = self._filename_pref
            self.__save__()
            ret['workbox_id'] = self._workbox_id

        self.__set_last_workbox_name__(self.__workbox_name__())
        self.__set_last_saved_text__(self.__text__())

        return ret

    @classmethod
    def __create_workbox_id__(cls, core_name):
        """Creates a __workbox_id__ to store this editors text contents stored
        in workbox_dir."""
        with tempfile.NamedTemporaryFile(
            prefix="workbox_",
            dir=get_prefs_dir(core_name=core_name),
            delete=True,
        ) as fle:
            name = fle.name

        return os.path.basename(name)

    def __workbox_id__(self):
        """Returns this workbox's workbox_id

        Returns:
            workbox_id (str)
        """
        return self._workbox_id

    def __backup_file__(self):
        """Returns this workbox's backup file

        Returns:
            _backup_file (str)
        """
        return self._backup_file

    def __set_changed_by_instance__(self, state):
        """Set whether this workbox has been determined to have been changed by
        a secondary PrEditor instance (in the same core).

        Args:
            state (bool): Whether this workbox has been determined to have been
                changed by a secondary PrEditor instance being saved.
        """
        self._changed_by_instance = state

    def __changed_by_instance__(self):
        """Returns whether this workbox has been determined to have been changed by
        a secondary PrEditor instance (in the same core).

        Returns:
            changed_by_instance (bool): Whether this workbox has been determined
            to have been changed by a secondary PrEditor instance being saved.
        """
        return self._changed_by_instance

    def __set_orphaned_by_instance__(self, state):
        """Set whether this workbox has been determined to have been orphaned by
        a secondary PrEditor instance (in the same core).

        Args:
            state (bool): Whether this workbox has been determined to have been
                orphaned by a secondary PrEditor instance being saved.
        """
        self._orphaned_by_instance = state

    def __orphaned_by_instance__(self):
        """Returns whether this workbox has been determined to have been orphaned by
        a secondary PrEditor instance (in the same core).

        Returns:
            changed_by_instance (bool): Whether this workbox has been determined
            to have been orphaned by a secondary PrEditor instance being saved.
        """
        return self._orphaned_by_instance

    def __determine_been_changed_by_instance__(self):
        """Determine whether this workbox has been changed by a secondary PrEditor
        instance saving it's prefs. It sets the internal property
        self._changed_by_instance to indicate the result.
        """
        if not self._workbox_id:
            self._workbox_id = self.__create_workbox_id__(self.core_name)

        if self._workbox_id in self.window().latestTimeStrsForBoxesChangedViaInstance:
            self.window().latestTimeStrsForBoxesChangedViaInstance.get(self._workbox_id)
            self._changed_by_instance = True
        else:
            self._changed_by_instance = False

    def __get_workbox_version_text__(self, filename, versionType):
        """Get the text of this workboxes previously saved versions. It's based
        on versionType, which can be First, Previous, Next, SecondToLast, or Last

        Args:
            filename (str): Description
            versionType (prefs.VersionTypes): Enum describing which version to
                fetch

        Returns:
            txt, filepath, idx, count (str, str, int, int): The found files' text,
                it's filepath, the index of this file in the stack of files, and
                the total count of files for this workbox.
        """
        backup_file = get_full_path(
            self.core_name, self._workbox_id, backup_file=self._backup_file
        )

        filepath, idx, count = get_backup_version_info(
            self.core_name, filename, versionType, backup_file
        )
        txt = ""
        if filepath and Path(filepath).is_file():
            _encoding, txt = self.__open_file__(str(filepath))

        return txt, filepath, idx, count

    def __load_workbox_version_text__(self, versionType):
        """Get the text of this workboxes previously saved versions, and set it
        in the workbox. It's based on versionType, which can be First, Previous,
        Next, SecondToLast, or Last

        Args:
            versionType (prefs.VersionTypes): Enum describing which version to
                fetch

        Returns:
            filename, idx, count (str, int, int): The found files' filepath, the
                index of this file in the stack of files, and the total count of
                files for this workbox.
        """
        data = self.__get_workbox_version_text__(self._workbox_id, versionType)
        txt, filepath, idx, count = data

        if filepath:
            filepath = get_relative_path(self.core_name, filepath)

        self._backup_file = str(filepath)

        self.__set_text__(txt, update_last_saved_text=False)
        self.__tab_widget__().tabBar().update()

        filename = Path(filepath).name
        return filename, idx, count

    @classmethod
    def __open_file__(cls, filename, strict=True):
        """Open a file and try to detect the text encoding it was saved as.

        Returns:
            encoding(str): The detected encoding, Defaults to "utf-8" if unable
                to detect encoding.
            text(str): The contents of the file decoded to a str.
        """
        with open(filename, "rb") as f:
            text_bytes = f.read()

        # Open file, detect source encoding and convert to utf-8
        encoding = chardet.detect(text_bytes)['encoding'] or 'utf-8'
        try:
            text = text_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            if strict:
                raise UnicodeDecodeError(  # noqa: B904
                    e.encoding,
                    e.object,
                    e.start,
                    e.end,
                    f"{e.reason}, Filename: {filename}",
                )
            encoding = 'utf-8'
            text = text_bytes.decode(encoding, errors="ignore")
        return encoding, text

    @classmethod
    def __write_file__(cls, filename, txt, encoding=None):
        with io.open(filename, 'w', newline='\n', encoding=encoding) as fle:
            fle.write(txt)

    def __show__(self):
        if self._is_loaded:
            return

        self._is_loaded = True
        count = None
        if self._filename_pref and Path(self._filename_pref).is_file():
            self.__load__(self._filename_pref)
            return
        else:
            core_name = self.window().name
            versionType = VersionTypes.Last
            filepath, idx, count = get_backup_version_info(
                core_name, self._workbox_id, versionType, ""
            )

            if count:
                self.__load_workbox_version_text__(VersionTypes.Last)
                self.__set_last_saved_text__(self.__text__())

        self.__set_last_workbox_name__()

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
            # Collect what was pressed
            key = event.key()
            modifiers = event.modifiers()

            # Determine which relevant combos are pressed
            ret = key == Qt.Key.Key_Return
            enter = key == Qt.Key.Key_Enter
            shift = modifiers == Qt.KeyboardModifier.ShiftModifier
            ctrlShift = (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            )

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
