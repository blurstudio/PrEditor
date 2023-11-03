from __future__ import absolute_import

from Qt.QtCore import Slot
from Qt.QtGui import QIcon
from Qt.QtWidgets import QWidget

from .. import plugins, resourcePath
from ..gui import loadUi


class EditorChooser(QWidget):
    """A widget that lets the user choose from a a list of available editors."""

    def __init__(self, parent=None, editor_name=None):
        super(EditorChooser, self).__init__(parent=parent)
        loadUi(__file__, self)
        icon = QIcon(resourcePath('img/warning-big.png'))
        self.uiWarningIconLBL.setPixmap(icon.pixmap(icon.availableSizes()[0]))
        if editor_name:
            self.set_editor_name(editor_name)

    def editor_name(self):
        return self.uiWorkboxEditorDDL.currentText()

    def set_editor_name(self, name):
        index = self.uiWorkboxEditorDDL.findText(name)
        if index == -1:
            self.uiWorkboxEditorDDL.addItem(name)
            index = self.uiWorkboxEditorDDL.findText(name)
        self.uiWorkboxEditorDDL.setCurrentIndex(index)

    @Slot()
    def refresh(self):
        warning = "Choose an editor to enable Workboxs."
        editor_name = self.editor_name()
        if editor_name:
            _, editor = plugins.editor(editor_name)
            warning = editor._warning_text
        self.uiWarningIconLBL.setVisible(bool(warning))
        self.uiWarningTextLBL.setVisible(bool(warning))
        self.uiWarningTextLBL.setText(warning)

    def refresh_editors(self):
        current = self.editor_name()
        self.uiWorkboxEditorDDL.blockSignals(True)
        self.uiWorkboxEditorDDL.clear()
        for name, _ in sorted(set(plugins.editors())):
            self.uiWorkboxEditorDDL.addItem(name)

        self.uiWorkboxEditorDDL.setCurrentIndex(
            self.uiWorkboxEditorDDL.findText(current)
        )
        self.uiWorkboxEditorDDL.blockSignals(False)

    def showEvent(self, event):  # noqa: N802
        super(EditorChooser, self).showEvent(event)
        self.refresh_editors()
