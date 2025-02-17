from __future__ import absolute_import

from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QMessageBox, QToolButton

from ... import resourcePath
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
        self.uiCornerBTN.setIcon(QIcon(resourcePath('img/file-plus.png')))
        self.uiCornerBTN.released.connect(lambda: self.add_new_editor())
        self.setCornerWidget(self.uiCornerBTN, Qt.Corner.TopRightCorner)

        self.default_title = "Workbox01"

    def add_new_editor(self, title=None, prefs=None):
        title = title or self.default_title

        title = self.get_next_available_tab_name(title)
        editor, title = self.default_tab(title)
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
            editor = self.widget(index)
            editor.__remove_tempfile__()

            super(GroupedTabWidget, self).close_tab(index)

    def default_tab(self, title=None, prefs=None):
        title = title or self.default_title
        kwargs = self.editor_kwargs if self.editor_kwargs else {}
        editor = self.editor_cls(parent=self, core_name=self.core_name, **kwargs)
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
