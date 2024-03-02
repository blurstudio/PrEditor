from __future__ import absolute_import

import six
from Qt.QtCore import QPoint, Qt
from Qt.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QShortcut

from .workbox_completer import WorkboxCompleter


class CommandPalette(QFrame):
    def __init__(self, model, parent=None, **kwargs):
        super(CommandPalette, self).__init__(parent=parent, **kwargs)
        self.y_offset = 100
        lyt = QHBoxLayout(self)
        self.uiLineEDIT = QLineEdit(parent=self)
        lyt.addWidget(self.uiLineEDIT)
        self.setMinimumSize(400, self.sizeHint().height())
        self.uiCloseSCT = QShortcut(
            Qt.Key_Escape, self, context=Qt.WidgetWithChildrenShortcut
        )
        self.uiCloseSCT.activated.connect(self.hide)
        self.uiLineCOMPL = WorkboxCompleter()
        self.uiLineCOMPL.split_char = None
        self.uiLineCOMPL.setCaseSensitivity(False)
        self.uiLineCOMPL.setModel(model)
        self.uiLineEDIT.setCompleter(self.uiLineCOMPL)
        self.uiLineCOMPL.activated.connect(self.completed)
        self.uiLineCOMPL.highlighted.connect(self.completer_selected)
        # self.uiLineCOMPL.popup().clicked.connect(self.completed)
        self.uiLineEDIT.textChanged.connect(self.update_completer)
        self.current_name = parent.name_for_workbox(parent.current_workbox())

    def update_completer(self, wildcard):
        self.uiLineCOMPL.updatePattern(wildcard)

    def completed(self, name):
        if isinstance(name, six.string_types):
            self.current_name = name
        else:
            self.current_name = self.uiLineCOMPL.pathFromIndex(name)
        self.hide()

    def completer_selected(self, name):
        self.parent().workbox_for_name(name.rstrip("/"), visible=True)

    def hide(self):
        # Close the popup if its open
        self.uiLineCOMPL.popup().hide()
        # Restore the original tab as the user didn't choose the new tab
        self.completer_selected(self.current_name)
        super(CommandPalette, self).hide()

    def reposition(self):
        pgeo = self.parent().geometry()
        geo = self.geometry()
        center = QPoint(pgeo.width() // 2, self.y_offset)
        geo.moveCenter(center)
        self.setGeometry(geo)

    def popup(self):
        self.reposition()
        self.uiLineEDIT.setFocus(Qt.PopupFocusReason)
        self.show()
        self.uiLineCOMPL.complete()
