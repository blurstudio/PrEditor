from __future__ import absolute_import

from Qt.QtCore import QByteArray, QMimeData, QPoint, QRect, Qt
from Qt.QtGui import QCursor, QDrag, QPixmap, QRegion
from Qt.QtWidgets import QInputDialog, QMenu, QTabBar


class DragTabBar(QTabBar):
    """A QTabBar that allows you to drag and drop its tabs to other DragTabBar's
    while still allowing you to move tabs normally.

    In most cases you should use `install_tab_widget` to create and add this TabBar
    to a QTabWidget. It takes care of enabling usability features of QTabWidget's.

    Args:
        mime_type (str, optional): Only accepts dropped tabs that implement this
            Mime Type. Tabs dragged off of this TabBar will have this Mime Type
            implemented.

    Based on code by ARussel: https://forum.qt.io/post/420469
    """

    def __init__(self, parent=None, mime_type='DragTabBar'):
        super(DragTabBar, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._mime_data = None
        self._context_menu_tab = -1
        self.mime_type = mime_type

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
        cursor = QCursor(Qt.OpenHandCursor)
        drag.setDragCursor(cursor.pixmap(), Qt.MoveAction)
        action = drag.exec_(Qt.MoveAction)
        # If the user didn't successfully add this to a new tab widget, restore
        # the tab to the original location.
        if action == Qt.IgnoreAction:
            original_tab_index = self._mime_data.property('original_tab_index')
            self.parentWidget().insertTab(
                original_tab_index, widget, self._mime_data.text()
            )

        self._mime_data = None

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and not self._mime_data:
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

        event.setDropAction(Qt.MoveAction)
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
            msg = 'Rename the {} tab to:'.format(current)
            name, success = QInputDialog.getText(self, 'Rename Tab', msg, text=current)
            if success:
                self.setTabText(self._context_menu_tab, name)

    def tab_menu(self, pos, popup=True):
        """Creates the custom context menu for the tab bar. To customize the menu
        call super setting `popup=False`. This will return the menu for
        customization and you will then need to call popup on the menu.

        This method sets the tab index the user right clicked on in the variable
        `_context_menu_tab`. This can be used in the triggered QAction methods."""

        self._context_menu_tab = self.tabAt(pos)
        if self._context_menu_tab == -1:
            return
        menu = QMenu(self)
        act = menu.addAction('Rename')
        act.triggered.connect(self.rename_tab)

        if popup:
            menu.popup(self.mapToGlobal(pos))

        return menu

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

        if menu:
            bar.setContextMenuPolicy(Qt.CustomContextMenu)
            bar.customContextMenuRequested.connect(bar.tab_menu)

        return bar
