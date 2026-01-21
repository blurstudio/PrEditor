from __future__ import absolute_import

from pathlib import Path

from Qt.QtCore import Qt
from Qt.QtWidgets import QHBoxLayout, QMessageBox, QSizePolicy, QToolButton, QWidget

from ...prefs import VersionTypes, get_backup_version_info
from ..drag_tab_bar import DragTabBar
from ..workbox_text_edit import WorkboxTextEdit
from .grouped_tab_menu import GroupTabMenu
from .grouped_tab_widget import GroupedTabWidget
from .one_tab_widget import OneTabWidget

DEFAULT_STYLE_SHEET = """
/* Make the two buttons in the GroupTabWidget take up the
   same horizontal space as the GroupedTabWidget's buttons.
GroupTabWidget>QTabBar::tab{
    max-height: 1.5em;
}*/
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

        self.default_title = 'Group01'

        corner = QWidget(self)
        lyt = QHBoxLayout(corner)
        lyt.setSpacing(0)
        lyt.setContentsMargins(0, 5, 0, 0)

        corner.uiNewTabBTN = QToolButton(corner)
        corner.uiNewTabBTN.setObjectName('group_tab_widget_new_btn')
        corner.uiNewTabBTN.setText('+')
        corner.uiNewTabBTN.released.connect(lambda: self.add_new_tab(None))

        lyt.addWidget(corner.uiNewTabBTN)

        corner.uiMenuBTN = QToolButton(corner)
        corner.uiMenuBTN.setText('\u2630')
        corner.uiMenuBTN.setObjectName('group_tab_widget_menu_btn')
        corner.uiMenuBTN.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        corner.uiCornerMENU = GroupTabMenu(self, parent=corner.uiMenuBTN)
        corner.uiMenuBTN.setMenu(corner.uiCornerMENU)

        self.adjustSizePolicy(corner)
        self.adjustSizePolicy(corner.uiNewTabBTN)
        self.adjustSizePolicy(corner.uiMenuBTN)
        self.adjustSizePolicy(corner.uiCornerMENU)

        lyt.addWidget(corner.uiMenuBTN)

        self.uiCornerBTN = corner
        self.setCornerWidget(self.uiCornerBTN, Qt.Corner.TopRightCorner)

    def adjustSizePolicy(self, button):
        sp = button.sizePolicy()
        sp.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        button.setSizePolicy(sp)

    def add_new_tab(self, group, title=None, prefs=None):
        """Adds a new tab to the requested group, creating the group if the group
        doesn't exist.

        Args:
            group: The group to add a new tab to. This can be an int index of an
                existing tab, or the name of the group and it will create the group
                if needed. If None is passed it will add a new tab `Group {last+1}`.
                If True is passed, then the current group tab is used.
            title (str, optional): The name to give the newly created tab inside
                the group.

        Returns:
            GroupedTabWidget: The tab group for this group.
            WorkboxMixin: The new text editor.
        """
        if not group:
            group = self.get_next_available_tab_name()
        elif group is True:
            group = self.currentIndex()

        parent = None
        if isinstance(group, int):
            group_title = self.tabText(group)
            parent = self.widget(group)
        elif isinstance(group, str):
            group_title = group
            index = self.index_for_text(group)
            if index != -1:
                parent = self.widget(index)

        if not parent:
            parent, group_title = self.default_tab(group_title, prefs)
            self.addTab(parent, group_title)

        # Create the first editor tab and make it visible
        editor = parent.add_new_editor(title, prefs)
        self.setCurrentIndex(self.indexOf(parent))
        self.window().focusToWorkbox()
        self.tabBar().setFont(self.window().font())
        return parent, editor

    def all_widgets(self):
        """A generator yielding information about every widget under every group.

        Yields:
            widget, group tab name, widget tab name, group tab index, widget tab index
        """
        for group_index in range(self.count()):
            group_name = self.tabText(group_index)

            tab_widget = self.widget(group_index)
            for tab_index in range(tab_widget.count()):
                tab_name = tab_widget.tabText(tab_index)
                yield tab_widget.widget(
                    tab_index
                ), group_name, tab_name, group_index, tab_index

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
                self.tabText(index)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.store_closed_workboxes(index)
            super(GroupTabWidget, self).close_tab(index)

    def store_closed_workboxes(self, index):
        """Store all the workbox names in group tab being closed.

        Args:
            index (int): The index of the group being closed
        """
        group = self.widget(index)

        for idx in range(group.count()):
            workbox = group.widget(idx)

            # Save the workbox first, so we can possibly restore it later.
            workbox.__save_prefs__(saveLinkedFile=False)

            self.parent().window().addRecentlyClosedWorkbox(workbox)

    def current_groups_widget(self):
        """Returns the current widget of the currently selected group or None."""
        editor_tab = self.currentWidget()
        if editor_tab:
            return editor_tab.currentWidget()

    def default_tab(self, title=None, prefs=None):
        title = title or self.default_title
        widget = GroupedTabWidget(
            parent=self,
            editor_kwargs=self.editor_kwargs,
            editor_cls=self.editor_cls,
            core_name=self.core_name,
        )
        return widget, title

    def get_next_available_tab_name(self, name=None):
        """Get the next available tab name, providing a default if needed.

        Args:
            name (str, optional): The name for which to get the next available
                name.

        Returns:
            str: The determined next available tab name
        """
        if name is None:
            name = self.default_title
        return super().get_next_available_tab_name(name)

    def append_orphan_workboxes_to_prefs(self, prefs, existing_by_group):
        """If prefs are saved in a different PrEditor instance (in this same core)
        there may be a workbox which is either:
            - new in this instance
            - removed in the saved other instance
        Any of these workboxes are 'orphaned'. Rather than just deleting it, we
        alert the user, so that work can be saved.

        We also add any orphan workboxes to the window's boxesOrphanedViaInstance
        dict, in the form `workbox_id: workbox`.

        Args:
            prefs (dict): The 'workboxes' section of the PrEditor prefs
            existing_by_group (dict): The existing workbox's info (as returned
                by self.all_widgets(), by group.

        Returns:
            prefs (dict): The 'workboxes' section of the PrEditor prefs, updated
        """
        groups = prefs.get("groups")
        for group_name, workbox_infos in existing_by_group.items():
            prefs_group = None
            for temp_group in groups:
                temp_name = temp_group.get("name")
                if temp_name == group_name:
                    prefs_group = temp_group
                    break

            # If the orphan's group doesn't yet exist, we prepare to make it
            new_group = None
            if not prefs_group:
                new_group = dict(name=group_name, tabs=[])

            cur_group = prefs_group or new_group
            cur_tabs = cur_group.get("tabs")

            for workbox_info in workbox_infos:
                # Create workbox_dict
                workbox = workbox_info[0]
                name = workbox_info[2]

                workbox_id = workbox.__workbox_id__()

                workbox_dict = dict(
                    name=name,
                    workbox_id=workbox_id,
                    filename=workbox.__filename__(),
                    backup_file=workbox.__backup_file__(),
                    orphaned_by_instance=True,
                )

                self.window().boxesOrphanedViaInstance[workbox_id] = workbox

                cur_tabs.append(workbox_dict)
            if new_group:
                groups.append(cur_group)
        return prefs

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
                            "workbox_id": null
                        },
                        {
                            // This tab should be active for the group.
                            "current": true,
                            "filename": null,
                            "name": "Workbox",
                            // If workbox_id is not null, this file is loaded.
                            // Ignored if filename is not null.
                            "workbox_id": "workbox_2yrwctco_a.py"
                        }
                    ]
                }
            ]
        }
        ```
        """
        selected_workbox_id = None
        current_workbox = self.window().current_workbox()
        if current_workbox:
            selected_workbox_id = current_workbox.__workbox_id__()

        # When re-running restore_prefs (ie after another instance saved
        # workboxes, and we are reloading them here, get the workbox_ids of all
        # workboxes defined in prefs
        pref_workbox_ids = []
        for group in prefs.get('groups', []):
            for tab in group.get('tabs', []):
                pref_workbox_ids.append(tab.get("workbox_id", None))

        # Collect data about workboxes which already exist (if we are re-running
        # this method after workboxes exist, ie another PrEditor instance has
        # changed contents and we are now matching those changes.
        existing_by_id = {}
        existing_by_group = {}
        for workbox_info in list(self.all_widgets()):
            workbox = workbox_info[0]
            workbox_id = workbox.__workbox_id__()
            group_name = workbox_info[1]
            existing_by_id[workbox.__workbox_id__()] = workbox_info

            # If we had a workbox, but what we are about to load doesn't include
            # it, add it back in so it will be shown.
            if workbox_id not in pref_workbox_ids:
                existing_by_group.setdefault(group_name, []).append(workbox_info)

        prefs = self.append_orphan_workboxes_to_prefs(prefs, existing_by_group)

        self.clear()

        current_group = None
        workboxes_missing_id = []
        for group in prefs.get('groups', []):
            current_tab = None
            tab_widget = None

            group_name = group['name']
            group_name = self.get_next_available_tab_name(group_name)

            for tab in group.get('tabs', []):
                # Only add this tab if, there is data on disk to load. The user can
                # open multiple instances of PrEditor using the same prefs. The
                # json pref data represents the last time the prefs were saved.
                # Each editor's contents are saved to individual files on disk.
                # When a editor tab is closed, the temp file is removed, not on
                # preferences save.
                # By not restoring tabs for deleted files we prevent accidentally
                # restoring a tab with empty text.

                loadable = False
                name = tab['name']

                # Support legacy arg for emergency backwards compatibility
                tempfile = tab.get('tempfile', None)
                # Get various possible saved filepaths.
                filename = tab.get('filename', "")
                if filename:
                    if Path(filename).is_file():
                        loadable = True

                workbox_id = tab.get('workbox_id', None)
                # If user went back to before PrEditor used workbox_id, and
                # back, the workbox may not be loadable. First, try to recover
                # it from the backup_file. If not recoverable, collect and
                # notify user.
                if workbox_id is None:
                    bak_file = tab.get('backup_file', None)
                    if bak_file:
                        workbox_id = str(Path(bak_file).parent)
                    elif not tempfile:
                        missing_name = f"{group_name}/{name}"
                        workboxes_missing_id.append(missing_name)
                        continue
                    else:
                        # If only the tempfile is set, use it as the workbox_id
                        workbox_id = Path(tempfile).stem

                orphaned_by_instance = tab.get('orphaned_by_instance', False)

                # See if there are any  workbox backups available
                backup_file, _, count = get_backup_version_info(
                    self.window().name, workbox_id, VersionTypes.Last, ""
                )
                if count:
                    loadable = True
                if not loadable:
                    continue

                # There is a file on disk, add the tab, creating the group
                # tab if it hasn't already been created.
                prefs = dict(
                    workbox_id=workbox_id,
                    filename=filename,
                    backup_file=backup_file,
                    existing_editor_info=existing_by_id.pop(workbox_id, None),
                    orphaned_by_instance=orphaned_by_instance,
                    tempfile=tempfile,
                )
                tab_widget, editor = self.add_new_tab(
                    group_name, title=name, prefs=prefs
                )

                editor.__set_last_workbox_name__(editor.__workbox_name__())
                editor.__determine_been_changed_by_instance__()

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

        if selected_workbox_id:
            for widget_info in self.all_widgets():
                widget, _, _, group_idx, tab_idx = widget_info
                if widget.__workbox_id__() == selected_workbox_id:
                    self.setCurrentIndex(group_idx)
                    grouped = self.widget(group_idx)
                    grouped.setCurrentIndex(tab_idx)
                    break

        # If any workboxes could not be loaded because they had no stored
        # workbox_id, notify user. This likely only happens if user goes back
        # to older PrEditor, and back.
        if workboxes_missing_id:
            suffix = "" if len(workboxes_missing_id) == 1 else "es"
            workboxes_missing_id.insert(0, "")
            missing_names = "\n\t".join(workboxes_missing_id)
            msg = (
                f"The following workbox{suffix} somehow did not have a "
                f"workbox_id stored, and therefore could not be loaded:"
                f"{missing_names}"
            )
            print(msg)

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
                workbox = tab_widget.widget(j)
                tabs.append(workbox.__save_prefs__(current=current))

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

    def set_current_groups_from_workbox(self, workbox):
        """Make the specified workbox the current widget. If the workbox is not
        found, the current widget is not changed.

        Args:
            workbox (WorkboxMixin): The workbox to make current.

        Returns:
            success (bool): Whether the workbox was found and made the current
                widget
        """
        workbox_infos = self.all_widgets()
        found_info = None
        for workbox_info in workbox_infos:
            if workbox_info[0] == workbox:
                found_info = workbox_info
                break
        if found_info:
            workbox = workbox_info[0]
            group_idx = workbox_info[-2]
            editor_idx = workbox_info[-1]

            self.setCurrentIndex(group_idx)
            tab_widget = self.currentWidget()
            tab_widget.setCurrentIndex(editor_idx)

        return bool(found_info)
