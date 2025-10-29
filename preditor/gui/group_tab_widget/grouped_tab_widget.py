from __future__ import absolute_import

from Qt.QtCore import Qt
from Qt.QtWidgets import QMessageBox, QToolButton

from ...prefs import VersionTypes
from ..drag_tab_bar import DragTabBar
from ..workbox_text_edit import WorkboxTextEdit
from .one_tab_widget import OneTabWidget


class GroupedTabWidget(OneTabWidget):
    def __init__(self, editor_kwargs, editor_cls=None, core_name=None, *args, **kwargs):
        super(GroupedTabWidget, self).__init__(*args, **kwargs)
        DragTabBar.install_tab_widget(self, 'grouped_tab_widget')
        self.editor_kwargs = editor_kwargs
        if editor_cls is None:
            editor_cls = WorkboxTextEdit
        self.editor_cls = editor_cls
        self.core_name = core_name
        self.currentChanged.connect(self.tab_shown)

        self.uiCornerBTN = QToolButton(self)
        self.uiCornerBTN.setText('+')
        self.uiCornerBTN.released.connect(lambda: self.add_new_editor())
        self.setCornerWidget(self.uiCornerBTN, Qt.Corner.TopRightCorner)

        self.default_title = "Workbox01"

    def __tab_widget__(self):
        """Return the tab widget which contains this group

        Returns:
            GroupTabWidget: The tab widget which contains this group
        """
        return self.parent().parent()

    def __changed_by_instance__(self):
        """Returns if any of this groups editors have been changed by another
        PrEditor instance's prefs save.

        Returns:
            changed (bool)
        """
        changed = False
        for workbox_idx in range(self.count()):
            workbox = self.widget(workbox_idx)
            if workbox.__changed_by_instance__():
                changed = True
                break
        return changed

    def __orphaned_by_instance__(self):
        """Returns if any of this groups editors have been orphaned by another
        PrEditor instance's prefs save.

        Returns:
            orphaned (bool)
        """
        orphaned = False
        for workbox_idx in range(self.count()):
            workbox = self.widget(workbox_idx)
            if workbox.__orphaned_by_instance__():
                orphaned = True
                break
        return orphaned

    def __is_dirty__(self):
        """Returns if any of this groups editors are dirty.

        Returns:
            is_dirty (bool)
        """
        is_dirty = False
        for workbox_idx in range(self.count()):
            workbox = self.widget(workbox_idx)
            if workbox.__is_dirty__():
                is_dirty = True
                break
        return is_dirty

    def add_new_editor(self, title=None, prefs=None):
        title = title or self.default_title

        title = self.get_next_available_tab_name(title)
        editor, title = self.default_tab(title, prefs=prefs)
        index = self.addTab(editor, title)
        self.setCurrentIndex(index)
        return editor

    def addTab(self, *args, **kwargs):  # noqa: N802
        ret = super(GroupedTabWidget, self).addTab(*args, **kwargs)
        self.update_closable_tabs()
        return ret

    def close_tab(self, index):
        if self.count() == 1:
            msg = "You have to leave at least one tab open."
            QMessageBox.critical(
                self, 'Tab can not be closed.', msg, QMessageBox.StandardButton.Ok
            )
            return

        workbox = self.widget(index)
        name = workbox.__workbox_name__()
        msg = (
            f"Would you like to donate the contents of tab\n{name}\nto the "
            "/dev/null fund for wayward code?"
        )

        ret = QMessageBox.question(
            self,
            'Donate to the cause?',
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if ret == QMessageBox.StandardButton.Yes:
            # If the tab was saved to a temp file, remove it from disk
            _editor = self.widget(index)  # noqa: F841
            # Keep track of deleted tabs, make re-openable
            # Maybe also move workbox dir to a 'removed workboxes' dir

            super(GroupedTabWidget, self).close_tab(index)

    def default_tab(self, title=None, prefs=None):
        title = title or self.default_title
        kwargs = self.editor_kwargs if self.editor_kwargs else {}
        editor = None
        orphaned_by_instance = False
        if prefs:
            editor_info = prefs.pop("existing_editor_info", None)
            if editor_info:
                editor = editor_info[0]
            orphaned_by_instance = prefs.pop("orphaned_by_instance", False)
        else:
            prefs = {}

        if editor:
            editor.__load_workbox_version_text__(VersionTypes.Last)

            editor.__set_tab_widget__(self)
            editor.__set_last_saved_text__(editor.text())
            editor.__set_last_workbox_name__(editor.__workbox_name__())

            filename = prefs.get("filename", None)
            editor.__set_filename__(filename)

            editor.__determine_been_changed_by_instance__()
            self.window().setWorkboxFontBasedOnConsole(editor)
        else:
            editor = self.editor_cls(
                parent=self, core_name=self.core_name, **prefs, **kwargs
            )
        editor.__set_orphaned_by_instance__(orphaned_by_instance)
        return editor, title

    def showEvent(self, event):  # noqa: N802
        super(GroupedTabWidget, self).showEvent(event)
        self.tab_shown(self.currentIndex())

    def tab_shown(self, index):
        editor = self.widget(index)
        if editor and editor.isVisible():
            editor.__show__()

        if hasattr(self.window(), "setWorkboxFontBasedOnConsole"):
            self.window().setWorkboxFontBasedOnConsole()

    def tab_widget(self):
        """Return the tab widget which contains this group tab

        Returns:
            self._tab_widget (GroupTabWidget): The tab widget which contains
                this workbox
        """
        return self.parent().parent()

    def update_closable_tabs(self):
        self.setTabsClosable(self.count() != 1)
