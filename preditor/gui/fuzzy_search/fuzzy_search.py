from __future__ import absolute_import

from functools import partial

from Qt.QtCore import QModelIndex, QPoint, Qt, Signal
from Qt.QtWidgets import QFrame, QLineEdit, QListView, QShortcut, QVBoxLayout

from ..group_tab_widget.grouped_tab_models import GroupTabFuzzyFilterProxyModel


class FuzzySearch(QFrame):
    canceled = Signal("QModelIndex")
    """Passes the original QModelIndex for the tab that was selected when the
    widget was first shown. This lets you reset back to the orignal state."""
    highlighted = Signal("QModelIndex")
    """Emitted when the user navitages to the given index, but hasn't selected."""
    selected = Signal("QModelIndex")
    """Emitted when the user selects a item."""

    def __init__(self, model, parent=None, **kwargs):
        super(FuzzySearch, self).__init__(parent=parent, **kwargs)
        self.y_offset = 100
        self.setMinimumSize(400, 200)
        self.uiCloseSCT = QShortcut(
            Qt.Key_Escape, self, context=Qt.WidgetWithChildrenShortcut
        )
        self.uiCloseSCT.activated.connect(self._canceled)

        self.uiUpSCT = QShortcut(Qt.Key_Up, self, context=Qt.WidgetWithChildrenShortcut)
        self.uiUpSCT.activated.connect(partial(self.increment_selection, -1))
        self.uiDownSCT = QShortcut(
            Qt.Key_Down, self, context=Qt.WidgetWithChildrenShortcut
        )
        self.uiDownSCT.activated.connect(partial(self.increment_selection, 1))

        lyt = QVBoxLayout(self)
        self.uiLineEDIT = QLineEdit(parent=self)
        self.uiLineEDIT.textChanged.connect(self.update_completer)
        self.uiLineEDIT.returnPressed.connect(self.activated)
        lyt.addWidget(self.uiLineEDIT)
        self.uiResultsLIST = QListView(self)
        self.uiResultsLIST.activated.connect(self.activated)
        self.proxy_model = GroupTabFuzzyFilterProxyModel(self)
        self.proxy_model.setSourceModel(model)
        self.uiResultsLIST.setModel(self.proxy_model)
        lyt.addWidget(self.uiResultsLIST)

        self.original_model_index = model.original_model_index

    def activated(self):
        current = self.uiResultsLIST.currentIndex()
        self.selected.emit(current)
        self.hide()

    def increment_selection(self, direction):
        current = self.uiResultsLIST.currentIndex()
        col = 0
        row = 0
        if current.isValid():
            col = current.column()
            row = current.row() + direction
        new = self.uiResultsLIST.model().index(row, col)
        self.uiResultsLIST.setCurrentIndex(new)
        self.highlighted.emit(new)

    def update_completer(self, wildcard):
        if wildcard:
            if not self.uiResultsLIST.currentIndex().isValid():
                new = self.uiResultsLIST.model().index(0, 0)
                self.uiResultsLIST.setCurrentIndex(new)
        else:
            self.uiResultsLIST.clearSelection()
            self.uiResultsLIST.setCurrentIndex(QModelIndex())
        self.proxy_model.setFuzzySearch(wildcard)
        self.highlighted.emit(self.uiResultsLIST.currentIndex())

    def _canceled(self):
        # Restore the original tab as the user didn't choose the new tab
        self.canceled.emit(self.original_model_index)
        self.hide()

    def reposition(self):
        pgeo = self.parent().geometry()
        geo = self.geometry()
        center = QPoint(pgeo.width() // 2, 0)
        geo.moveCenter(center)
        geo.setY(self.y_offset)
        self.setGeometry(geo)

    def popup(self):
        self.show()
        self.reposition()
        self.uiLineEDIT.setFocus(Qt.PopupFocusReason)
