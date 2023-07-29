from __future__ import absolute_import

import os
import re

import six
from Qt.QtCore import Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QHBoxLayout, QMessageBox, QToolButton, QWidget

from ... import resourcePath
from ...prefs import prefs_path
from ..drag_tab_bar import DragTabBar
from ..workbox_text_edit import WorkboxTextEdit
from .grouped_tab_menu import GroupTabMenu
from .grouped_tab_widget import GroupedTabWidget
from .one_tab_widget import OneTabWidget

DEFAULT_STYLE_SHEET = """
/* Make the two buttons in the GroupTabWidget take up the
   same horizontal space as the GroupedTabWidget's buttons. */
GroupTabWidget>QTabBar::tab{
    max-height: 1.5em;
}
/* We have an icon, no need to show the menu indicator */
#group_tab_widget_menu_btn::menu-indicator{
    width: 0px;
}
/* The GroupedTabWidget has a single button, make it take
   the same space as the GroupTabWidget buttons. */
GroupedTabWidget>QToolButton,GroupTabWidget>QWidget{
    width: 3em;
}
"""


class GroupTabWidget(OneTabWidget):
    """A QTabWidget where each tab contains another tab widget, allowing users
    to group code editors. It has a corner button to add a new tab, and a menu
    allowing users to quickly focus on any tab in the entire group.
    """

    def __init__(self, editor_kwargs=None, core_name=None, *args, **kwargs):
        super(GroupTabWidget, self).__init__(*args, **kwargs)
        DragTabBar.install_tab_widget(self, 'group_tab_widget')
        self.editor_kwargs = editor_kwargs
        self.editor_cls = WorkboxTextEdit
        self.core_name = core_name
        self.setStyleSheet(DEFAULT_STYLE_SHEET)
        corner = QWidget(self)
        lyt = QHBoxLayout(corner)
        lyt.setSpacing(0)
        lyt.setContentsMargins(0, 0, 0, 0)

        corner.uiNewTabBTN = QToolButton(corner)
        corner.uiNewTabBTN.setObjectName('group_tab_widget_new_btn')
        corner.uiNewTabBTN.setText('+')
        corner.uiNewTabBTN.setIcon(QIcon(resourcePath('img/file-plus.png')))
        corner.uiNewTabBTN.released.connect(lambda: self.add_new_tab(None))
        lyt.addWidget(corner.uiNewTabBTN)

        corner.uiMenuBTN = QToolButton(corner)
        corner.uiMenuBTN.setIcon(QIcon(resourcePath('img/chevron-down.png')))
        corner.uiMenuBTN.setObjectName('group_tab_widget_menu_btn')
        corner.uiMenuBTN.setPopupMode(QToolButton.InstantPopup)
        corner.uiCornerMENU = GroupTabMenu(self, parent=corner.uiMenuBTN)
        corner.uiMenuBTN.setMenu(corner.uiCornerMENU)
        lyt.addWidget(corner.uiMenuBTN)

        self.uiCornerBTN = corner
        self.setCornerWidget(self.uiCornerBTN, Qt.TopRightCorner)

    def add_new_tab(self, group, title="Workbox"):
        """Adds a new tab to the requested group, creating the group if the group
        doesn't exist.

        Args:
            group: The group to add a new tab to. This can be an int index of an
                existing tab, or the name of the group and it will create the group
                if needed. If None is passed it will add a new tab `Group {last+1}`.
                If True is passed, then the current group tab is used.

        Returns:
            GroupedTabWidget: The tab group for this group.
            WorkboxMixin: The new text editor.
        """
        parent = None
        if not group:
            last = 0
            for i in range(self.count()):
                match = re.match(r'Group (\d+)', self.tabText(i))
                if match:
                    last = max(last, int(match.group(1)))
            group = "Group {}".format(last + 1)
        elif group is True:
            group = self.currentIndex()
        if isinstance(group, int):
            group_title = self.tabText(group)
            parent = self.widget(group)
        elif isinstance(group, six.string_types):
            group_title = group
            index = self.index_for_text(group)
            if index != -1:
                parent = self.widget(index)

        if not parent:
            parent, group_title = self.default_tab(group_title)
            self.addTab(parent, group_title)

        # Create the first editor tab and make it visible
        editor = parent.add_new_editor(title)
        self.setCurrentIndex(self.indexOf(parent))

        return parent, editor

    def all_widgets(self):
        """Returns every widget under every group."""
        for i in range(self.count()):
            tab_widget = self.widget(i)
            for j in range(tab_widget.count()):
                yield tab_widget.widget(j)

    def close_current_tab(self):
        """Convenient method to close the currently open editor tab prompting
        the user to confirm closing."""
        editor_tab = self.currentWidget()
        editor_tab.close_tab(editor_tab.currentIndex())

    def close_tab(self, index):
        ret = QMessageBox.question(
            self,
            'Close all editors under this tab?',
            'Are you sure you want to close all tabs under the "{}" tab?'.format(
                self.tabText(self.currentIndex())
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if ret == QMessageBox.Yes:
            # Clean up all temp files created by this group's editors if they
            # are not using actual saved files.
            tab_widget = self.widget(self.currentIndex())
            for index in range(tab_widget.count()):
                editor = tab_widget.widget(index)
                editor.__remove_tempfile__()

            super(GroupTabWidget, self).close_tab(self.currentIndex())

    def current_groups_widget(self):
        """Returns the current widget of the currently selected group or None."""
        editor_tab = self.currentWidget()
        if editor_tab:
            return editor_tab.currentWidget()

    def default_tab(self, title='Group 1'):
        widget = GroupedTabWidget(
            parent=self,
            editor_kwargs=self.editor_kwargs,
            editor_cls=self.editor_cls,
            core_name=self.core_name,
        )
        return widget, title

    def restore_prefs(self, prefs):
        """Adds tab groups and tabs, restoring the selected tabs. If a tab is
        linked to a file that no longer exists, will not be added. Restores the
        current tab for each group and the current group of tabs. If a current
        tab is no longer valid, it will default to the first tab.

        Preference schema:
        ```json
        {
            "groups": [
                {
                    // Name of the group tab. [Required]
                    "name": "My Group",
                    // This group should be the active group. First in list wins.
                    "current": true,
                    "tabs": [
                        {
                            // If filename is not null, this file is loaded
                            "filename": "C:\\temp\\invalid_asdfdfd.py",
                            // Name of the editor's tab [Optional]
                            "name": "invalid_asdfdfd.py",
                            "tempfile": null
                        },
                        {
                            // This tab should be active for the group.
                            "current": true,
                            "filename": null,
                            "name": "Workbox",
                            // If tempfile is not null, this file is loaded.
                            // Ignored if filename is not null.
                            "tempfile": "workbox_2yrwctco_a.py"
                        }
                    ]
                }
            ]
        }
        ```
        """

        self.clear()

        workbox_dir = prefs_path('workboxes', core_name=self.core_name)
        current_group = None
        for group in prefs.get('groups', []):
            current_tab = None
            group_name = group['name']
            tab_widget = None

            for tab in group.get('tabs', []):
                # Only add this tab if, there is data on disk to load. The user can
                # open multiple instances of PrEditor using the same prefs. The
                # json pref data represents the last time the prefs were saved.
                # Each editor's contents are saved to individual files on disk.
                # When a editor tab is closed, the temp file is removed, not on
                # preferences save.
                # By not restoring tabs for deleted files we prevent accidentally
                # restoring a tab with empty text.
                filename = tab.get('filename')
                temp_name = tab.get('tempfile')
                if filename:
                    if not os.path.exists(filename):
                        continue
                if not temp_name:
                    continue
                temp_name = os.path.join(workbox_dir, temp_name)
                if not os.path.exists(temp_name):
                    continue

                # There is a file on disk, add the tab, creating the group
                # tab if it hasn't already been created.
                name = tab['name']
                tab_widget, editor = self.add_new_tab(group_name, name)
                editor.__restore_prefs__(tab)

                # If more than one tab in this group is listed as current, only
                # respect the first
                if current_tab is None and tab.get('current'):
                    current_tab = tab_widget.indexOf(editor)

            # If there were no files to load, this tab was not added and there
            # we don't need to restore the current tab for this group
            if tab_widget is None:
                continue

            # Restore the current tab for this group
            if current_tab is None:
                # If there is no longer a current tab, default to the first tab
                current_tab = 0
            tab_widget.setCurrentIndex(current_tab)

            # Which tab group is the active one? If more than one tab in this
            # group is listed as current, only respect the first.
            if current_group is None and group.get('current'):
                current_group = self.indexOf(tab_widget)

        # Restore the current group for this widget
        if current_group is None:
            # If there is no longer a current tab, default to the first tab
            current_group = 0
        self.setCurrentIndex(current_group)

    def save_prefs(self, prefs=None):
        groups = []
        if prefs is None:
            prefs = {}

        prefs['groups'] = groups
        current_group = self.currentIndex()
        for i in range(self.count()):
            tabs = []
            group = {}
            # Hopefully the alphabetical sorting of this dict is preserved in py3
            # to make it easy to diff the json pref file if ever required.
            if i == current_group:
                group['current'] = True
            group['name'] = self.tabText(i)
            group['tabs'] = tabs

            tab_widget = self.widget(i)
            current_editor = tab_widget.currentIndex()
            for j in range(tab_widget.count()):
                current = True if j == current_editor else None
                tabs.append(
                    tab_widget.widget(j).__save_prefs__(
                        name=tab_widget.tabText(j), current=current
                    )
                )

            groups.append(group)

        return prefs

    def set_current_groups_from_index(self, group, editor):
        """Make the specified indexes the current widget and return it. If the
        indexes are out of range the current widget is not changed.

        Args:
            group (int): The index of the group tab to make current.
            editor (int): The index of the editor under the group tab to
                make current.

        Returns:
            QWidget: The current widget after applying.
        """
        self.setCurrentIndex(group)
        tab_widget = self.currentWidget()
        tab_widget.setCurrentIndex(editor)
        return tab_widget.currentWidget()
