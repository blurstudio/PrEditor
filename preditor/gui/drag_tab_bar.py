from __future__ import absolute_import

from enum import IntEnum
from functools import partial
from pathlib import Path

from Qt.QtCore import QByteArray, QMimeData, QPoint, QRect, Qt
from Qt.QtGui import QColor, QCursor, QDrag, QPixmap, QRegion
from Qt.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMenu,
    QSizePolicy,
    QTabBar,
)

from preditor import osystem

from ..gui import handleMenuHovered
from ..utils import Truncate
from ..utils.cute import QtPropertyInit


class TabStates(IntEnum):
    """Nice names for the Tab states for coloring"""

    Normal = 0
    Linked = 1
    Changed = 2
    ChangedLinked = 3
    Orphaned = 4
    OrphanedLinked = 5
    Dirty = 6
    DirtyLinked = 7
    MissingLinked = 8


class DragTabBar(QTabBar):
    """A QTabBar that allows you to drag and drop its tabs to other DragTabBar's
    while still allowing you to move tabs normally.

    In most cases you should use `install_tab_widget` to create and add this TabBar
    to a QTabWidget. It takes care of enabling usability features of QTabWidget's.

    Based on code by ARussel: https://forum.qt.io/post/420469

    """

    # the normalColor is set to an invalid color name. When QTabBar.setTabTextColor
    # is called with an invalid color name, it reverts to the QTabBar foreground
    # role instead
    normalColor = QColor("invalidcolor")

    # These Qt Properties can be customized using style sheets.
    linkedColor = QtPropertyInit('_linkedColor', QColor("grey"))
    missingLinkedColor = QtPropertyInit('_missingLinkedColor', QColor("grey"))
    dirtyColor = QtPropertyInit('_dirtyColor', QColor("grey"))
    dirtyLinkedColor = QtPropertyInit('_dirtyLinkedColor', QColor("grey"))
    changedColor = QtPropertyInit('_changedColor', QColor("grey"))
    changedLinkedColor = QtPropertyInit('_changedLinkedColor', QColor("grey"))
    orphanedColor = QtPropertyInit('_orphanedColor', QColor("grey"))
    orphanedLinkedColor = QtPropertyInit('_orphanedLinkedColor', QColor("grey"))

    def __init__(self, parent=None, mime_type='DragTabBar'):
        super(DragTabBar, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._mime_data = None
        self._context_menu_tab = -1
        self.mime_type = mime_type

        self.fg_color_map = {}
        self.bg_color_map = {}

    def updateColorMap(self):
        """This cannot be called during __init__, otherwise all bg colors will
        be default, and not read from the style sheet. So instead, the first
        time we need self.bg_color_map, we check if it has values, and call this
        method if it doesn't.
        """
        self.bg_color_map = {
            TabStates.Normal: self.normalColor,
            TabStates.Changed: self.changedColor,
            TabStates.ChangedLinked: self.changedLinkedColor,
            TabStates.Orphaned: self.orphanedColor,
            TabStates.OrphanedLinked: self.orphanedLinkedColor,
            TabStates.Dirty: self.dirtyColor,
            TabStates.DirtyLinked: self.dirtyLinkedColor,
            TabStates.Linked: self.linkedColor,
            TabStates.MissingLinked: self.missingLinkedColor,
        }
        self.fg_color_map = {
            "0": "white",
            "1": "black",
        }

    def getColorAndToolTip(self, index):
        """Determine the color and tooltip based on the state of the workbox.

        Args:
            index (int): The index of the tab holding the workbox

        Returns:
            color, toolTip (QColor, str): The QColor and toolTip string to apply
                to the tab being painted
        """
        state = TabStates.Normal
        toolTip = ""
        if self.parent():
            widget = self.parent().widget(index)

            filename = None
            if hasattr(widget, "__filename__"):
                filename = widget.__filename__()

            if widget.__changed_by_instance__():
                if filename:
                    state = TabStates.ChangedLinked
                    toolTip = (
                        "Linked workbox has been updated by saving in another "
                        "PrEditor and has had unsaved changes auto-saved to a"
                        " previous version.\nAccess with Ctrl-Alt-[ shortcut."
                    )
                else:
                    state = TabStates.Changed
                    toolTip = (
                        "Workbox has been updated by saving in another PrEditor "
                        "instance, and has had it's unsaved changes auto-saved to "
                        "a previous version.\nAccess with Ctrl-Alt-[ shortcut."
                    )
            elif widget.__orphaned_by_instance__():
                if filename:
                    state = TabStates.OrphanedLinked
                    toolTip = (
                        "Linked workbox is either newly added, or orphaned by "
                        "being removed in another PrEditor instance and saved."
                    )
                else:
                    state = TabStates.Orphaned
                    toolTip = (
                        "Workbox is either newly added, or orphaned by "
                        "being removed in another PrEditor instance and saved."
                    )
            elif widget.__is_dirty__():
                if filename:
                    state = TabStates.DirtyLinked
                    toolTip = "Linked workbox has unsaved changes."
                else:
                    state = TabStates.Dirty
                    toolTip = "Workbox has unsaved changes, or it's name has changed."
            elif widget.__is_missing_linked_file__():
                state = TabStates.MissingLinked
                toolTip = "Linked file is missing"
            elif hasattr(widget, "__filename__") and widget.__filename__():
                state = TabStates.Linked
                toolTip = "Linked to file on disk"

            if hasattr(widget, "__filename__"):
                filename = widget.__filename__()
                if filename:
                    toolTip += "\nfilename: {}".format(filename)

            window = self.window()
            if window.uiExtraTooltipInfoCHK.isChecked():

                if hasattr(widget, "__workbox_id__"):
                    workbox_id = widget.__workbox_id__()
                    if toolTip:
                        toolTip += "\n\n"
                    toolTip += workbox_id

                toolTip += "\nis dirty: {}".format(widget.__is_dirty__())
                toolTip += "\nstate: {}".format(state.name)

                if hasattr(widget, "__backup_file__"):
                    backup_file = widget.__backup_file__()
                    toolTip += "\nBackup file: {}".format(backup_file)

                if hasattr(widget, "_changed_by_instance"):
                    _changed_by_instance = widget._changed_by_instance
                    toolTip += "\nHas been changed by instance: {}".format(
                        _changed_by_instance
                    )

                if hasattr(widget, "__orphaned_by_instance__"):
                    __orphaned_by_instance__ = widget.__orphaned_by_instance__()
                    toolTip += "\n __orphaned_by_instance__: {}".format(
                        __orphaned_by_instance__
                    )

                if hasattr(widget, "_changed_saved"):
                    _changed_saved = widget._changed_saved
                    toolTip += "\n _changed_saved: {}".format(_changed_saved)

                if hasattr(widget, "__last_workbox_name__"):
                    last_workbox_name = widget.__last_workbox_name__()
                    toolTip += "\nlast_workbox_name: {}".format(last_workbox_name)

                if hasattr(widget, "__last_saved_text__"):
                    last_saved_text = widget.__last_saved_text__()
                    last_saved_text = Truncate(last_saved_text).lines()
                    toolTip += "\nlast_saved_text: \n{}".format(last_saved_text)

        color = self.bg_color_map.get(state)
        return color, toolTip

    def updateColorAndToolTip(self, index):
        """Update the color and tooltip for the tab at index, based of various
        factors about the workbox.

        Args:
            index (int): The index of the tab to color, and possibly, set toolTip
        """
        self.updateColorMap()

        color, toolTip = self.getColorAndToolTip(index)
        self.setTabTextColor(index, color)
        self.setTabToolTip(index, toolTip)

    def updateColorsAndToolTips(self):
        """Update the color and tooltip for all the tabs in this tabBar. Also,
        update the tabBar above it.
        """
        for index in range(self.count()):
            self.updateColorAndToolTip(index)

        parentIdx = self.window().indexOfWorkboxOrTabGroup(self.parent())
        if parentIdx is not None:
            tabBar = self.parent().__tab_widget__().tabBar()
            tabBar.updateColorAndToolTip(parentIdx)

    def mouseMoveEvent(self, event):  # noqa: N802
        if not self._mime_data:
            return super(DragTabBar, self).mouseMoveEvent(event)

        # Check if the mouse has moved outside of the widget, if not, let
        # the QTabBar handle the internal tab movement.
        event_pos = event.pos()
        global_pos = self.mapToGlobal(event_pos)
        bar_geo = QRect(self.mapToGlobal(self.pos()), self.size())
        inside = bar_geo.contains(global_pos)
        if inside:
            return super(DragTabBar, self).mouseMoveEvent(event)

        # The user has moved the tab outside of the QTabBar, remove the tab from
        # this tab bar and store it in the MimeData, initiating a drag event.
        widget = self._mime_data.property('widget')
        tab_index = self.parentWidget().indexOf(widget)
        self.parentWidget().removeTab(tab_index)
        pos_in_tab = self.mapFromGlobal(global_pos)
        drag = QDrag(self)
        drag.setMimeData(self._mime_data)
        drag.setPixmap(self._mime_data.imageData())
        drag.setHotSpot(event_pos - pos_in_tab)
        cursor = QCursor(Qt.CursorShape.OpenHandCursor)
        drag.setDragCursor(cursor.pixmap(), Qt.DropAction.MoveAction)
        action = drag.exec(Qt.DropAction.MoveAction)
        # If the user didn't successfully add this to a new tab widget, restore
        # the tab to the original location.
        if action == Qt.DropAction.IgnoreAction:
            original_tab_index = self._mime_data.property('original_tab_index')
            self.parentWidget().insertTab(
                original_tab_index, widget, self._mime_data.text()
            )

        self._mime_data = None

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self._mime_data:
            tab_index = self.tabAt(event.pos())

            # While we don't remove the tab on mouse press, capture its tab image
            # and attach it to the mouse. This also stores info needed to handle
            # moving the tab to a new QTabWidget, and undoing the move if the
            # user cancels the drop.
            tab_rect = self.tabRect(tab_index)
            pixmap = QPixmap(tab_rect.size())
            self.render(pixmap, QPoint(), QRegion(tab_rect))

            self._mime_data = QMimeData()
            self._mime_data.setData(self.mime_type, QByteArray())
            self._mime_data.setText(self.tabText(tab_index))
            self._mime_data.setProperty('original_tab_index', tab_index)
            self._mime_data.setImageData(pixmap)
            widget = self.parentWidget().widget(tab_index)
            self._mime_data.setProperty('widget', widget)

            # By default if there are no tabs, the tab bar is hidden. This
            # prevents users from re-adding tabs to the tab bar as only it
            # accepts the tab drops. This preserves the tab bar height
            # after it was drawn with a tab so it should automatically stay
            # the same visual height.
            if not self.minimumHeight():
                self.setMinimumHeight(self.height())

        super(DragTabBar, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._mime_data = None
        super(DragTabBar, self).mouseReleaseEvent(event)

    def dragEnterEvent(self, event):  # noqa: N802
        # if event.mimeData().hasFormat(self.mime_type):
        event.accept()

    def dragLeaveEvent(self, event):  # noqa: N802
        event.accept()

    def dragMoveEvent(self, event):  # noqa: N802
        # If this is not a tab of the same mime type, make the tab under the mouse
        # the current tab so users can easily drop inside that tab.
        if not event.mimeData().hasFormat(self.mime_type):
            event.accept()
            tab_index = self.tabAt(event.pos())
            if tab_index == -1:
                tab_index = self.count() - 1
            if self.currentIndex() != tab_index:
                self.setCurrentIndex(tab_index)

    def dropEvent(self, event):  # noqa: N802
        if not event.mimeData().hasFormat(self.mime_type):
            return
        if event.source().parentWidget() == self:
            return

        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        counter = self.count()

        mime_data = event.mimeData()
        if counter == 0:
            self.parent().addTab(mime_data.property('widget'), mime_data.text())
        else:
            self.parent().insertTab(
                counter + 1, mime_data.property('widget'), mime_data.text()
            )

    def rename_tab(self):
        """Used by the tab_menu to rename the tab at index `_context_menu_tab`."""
        if self._context_menu_tab != -1:
            current = self.tabText(self._context_menu_tab)
            msg = 'Rename the {} tab to (new name must be unique):'.format(current)

            name, success = QInputDialog.getText(self, 'Rename Tab', msg, text=current)
            name = self.parent().get_next_available_tab_name(name)
            if not name.strip():
                return

            if success:
                self.setTabText(self._context_menu_tab, name)
                self.updateColorsAndToolTips()

    def tab_menu(self, pos, popup=True):
        """Creates the custom context menu for the tab bar. To customize the menu
        call super setting `popup=False`. This will return the menu for
        customization and you will then need to call popup on the menu.

        This method sets the tab index the user right clicked on in the variable
        `_context_menu_tab`. This can be used in the triggered QAction methods."""

        index = self.tabAt(pos)
        self._context_menu_tab = index
        if self._context_menu_tab == -1:
            return
        menu = QMenu(self)
        menu.setFont(self.window().font())
        menu.hovered.connect(handleMenuHovered)

        grouped_tab = self.parentWidget()
        workbox = grouped_tab.widget(self._context_menu_tab)

        # Show File-related actions depending if filename already set. Don't include
        # Rename if the workbox is linked to a file.
        if hasattr(workbox, '__filename__'):
            if not workbox.__filename__():
                act = menu.addAction('Rename')
                tip = "Rename this tab."
                act.setToolTip(tip)
                act.triggered.connect(self.rename_tab)

                act = menu.addAction('Link File')
                tip = (
                    "Choose an existing file on disk to link this workbox to.\n"
                    "The current workbox contents will be replaced, but will be "
                    "backed up, accessible with Ctrl+Alt+Left"
                )
                act.setToolTip(tip)
                act.triggered.connect(partial(self.link_file, workbox))

                act = menu.addAction('Save and Link File')
                tip = (
                    "Choose a filename to save the workbox contents to, and "
                    "link to that file."
                )
                act.setToolTip(tip)
                act.triggered.connect(partial(self.save_and_link_file, workbox))
            else:
                if Path(workbox.__filename__()).is_file():
                    act = menu.addAction('Explore File')
                    tip = "Open a file explorer at the linked file's location"
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.explore_file, workbox))

                    act = menu.addAction('Unlink File')
                    tip = (
                        "Disconnect the link to the file on disk. The workbox "
                        "contents will remain unchanged."
                    )
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.unlink_file, workbox))

                    act = menu.addAction('Save As')
                    tip = (
                        "Save contents as a new file and link to it. If you "
                        "choose an existing file, that file's contents will be "
                        "overwritten."
                    )
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.save_and_link_file, workbox))

                    act = menu.addAction('Copy Filename')
                    tip = "Copy this workbox's filename to the clipboard."
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.copyFilename, workbox))
                else:
                    act = menu.addAction('Explore File')
                    tip = "Open a file explorer at the linked file's location"
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.explore_file, workbox))

                    act = menu.addAction('Save As and Link File')
                    tip = (
                        "Save contents as a new file and link to it. If you "
                        "choose an existing file, that file's contents will be "
                        "overwritten."
                    )
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.save_and_link_file, workbox))

                    act = menu.addAction('Relink File')
                    tip = (
                        "Current linked file is not found. Choose a new file "
                        "to link to."
                    )
                    act.setToolTip(tip)
                    act.triggered.connect(
                        partial(self.link_file, workbox, saveLinkedFile=False)
                    )

                    act = menu.addAction('Unlink File')
                    tip = (
                        "Disconnect the link to the file on disk. The workbox "
                        "contents will remain unchanged."
                    )
                    act.setToolTip(tip)
                    act.triggered.connect(partial(self.unlink_file, workbox))
        else:
            act = menu.addAction('Rename')
            tip = "Rename this tab."
            act.setToolTip(tip)
            act.triggered.connect(self.rename_tab)

        act = menu.addAction('Copy Workbox Name')
        tip = "Copy this workbox's name to the clipboard."
        act.setToolTip(tip)
        act.triggered.connect(partial(self.copy_workbox_name, workbox, index))

        act = menu.addAction('Copy Workbox Id')
        tip = "Copy this workbox's id to the clipboard."
        act.setToolTip(tip)
        act.triggered.connect(partial(self.copy_workbox_id, workbox, index))

        if popup:
            menu.popup(self.mapToGlobal(pos))

        return menu

    def link_file(self, workbox, saveLinkedFile=True):
        """Link the given workbox to a file on disk.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
        """
        filename = workbox.__filename__()
        filename, _other = QFileDialog.getOpenFileName(directory=filename)
        if filename and Path(filename).is_file():
            workbox.__set_file_monitoring_enabled__(False)

            # First, save any unsaved text
            workbox.__save_prefs__(saveLinkedFile=saveLinkedFile)

            # Now, load file
            workbox.__load__(filename)
            workbox.__set_filename__(filename)
            workbox.__set_file_monitoring_enabled__(True)

            name = Path(filename).name
            self.setTabText(self._context_menu_tab, name)
            self.updateColorsAndToolTips()
            self.update()
            self.window().setWorkboxFontBasedOnConsole(workbox=workbox)

            workbox.__save_prefs__(saveLinkedFile=False, force=True)

    def save_and_link_file(self, workbox):
        """Save the given workbox as a file on disk, and link the workbox to it.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
        """
        filename = workbox.__filename__()
        if filename and Path(filename).is_file():
            workbox.__set_file_monitoring_enabled__(False)
        directory = str(Path(filename).parent) if filename else ""
        success = workbox.__save_as__(directory=directory)
        if not success:
            return

        # Workbox
        filename = workbox.__filename__()
        workbox.__set_last_saved_text__(workbox.__text__())
        workbox.__set_file_monitoring_enabled__(True)
        name = Path(filename).name

        self.setTabText(self._context_menu_tab, name)
        self.updateColorsAndToolTips()
        self.update()
        self.window().setWorkboxFontBasedOnConsole(workbox=workbox)
        workbox.__set_last_workbox_name__(workbox.__workbox_name__())

    def explore_file(self, workbox):
        """Open a system file explorer at the path of the linked file.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
        """
        path = Path(workbox.__filename__())
        if path.exists():
            osystem.explore(str(path))
        elif path.parent.exists():
            osystem.explore(str(path.parent))

    def unlink_file(self, workbox):
        """Disconnect a file link.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
        """
        workbox.__set_file_monitoring_enabled__(False)
        workbox.__set_filename__("")
        name = self.parent().default_title
        self.setTabText(self._context_menu_tab, name)
        self.updateColorsAndToolTips()

    def copyFilename(self, workbox):
        """Copy the given workbox's filename to the clipboard

        Args:
            workbox (WorkboxMixin): The workbox for which to provide the filename
        """
        filename = workbox.__filename__()
        QApplication.clipboard().setText(filename)

    def copy_workbox_name(self, workbox, index):
        """Copy the workbox name to clipboard.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
            index (index): The index of the clicked tab
        """
        try:
            name = workbox.__workbox_name__()
        except AttributeError:
            group = self.parent().widget(index)
            curIndex = group.currentIndex()
            workbox = group.widget(curIndex)
            name = workbox.__workbox_name__()
        QApplication.clipboard().setText(name)

    def copy_workbox_id(self, workbox, index):
        """Copy the workbox id to clipboard.

        Args:
            workbox (WorkboxMixin): The workbox contained in the clicked tab
            index (index): The index of the clicked tab
        """
        try:
            workbox_id = workbox.__workbox_id__()
        except AttributeError:
            group = self.parent().widget(index)
            curIndex = group.currentIndex()
            workbox = group.widget(curIndex)
            workbox_id = workbox.__workbox_id__()
        QApplication.clipboard().setText(workbox_id)

    @classmethod
    def install_tab_widget(cls, tab_widget, mime_type='DragTabBar', menu=True):
        """Creates and returns a instance of DragTabBar and installs it on the
        QTabWidget. This enables movable tabs, and enables document mode.
        Document mode makes the tab bar expand to the size of the QTabWidget so
        drag drop operations are more intuitive.

        Args:
            tab_widget (QTabWidget): The QTabWidget to install the tab bar on.
            mime_data (str, optional): This TabBar will only accept tab drop
                operations with this mime type.
            menu (bool, optional): Install a custom context menu on the bar bar.
                Override `tab_menu` to customize the menu.
        """
        bar = cls(tab_widget, mime_type=mime_type)
        tab_widget.setTabBar(bar)
        tab_widget.setMovable(True)
        tab_widget.setDocumentMode(True)

        sizePolicy = tab_widget.sizePolicy()
        sizePolicy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        tab_widget.setSizePolicy(sizePolicy)

        if menu:
            bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            bar.customContextMenuRequested.connect(bar.tab_menu)

        return bar
