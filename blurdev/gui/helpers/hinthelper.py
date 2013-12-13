"""
The HintHelper class helps provide a constant tool tip to widgets

"""

from PyQt4.QtGui import (
    QLabel,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QTreeWidget,
)
from PyQt4.QtCore import Qt


class HintHelper(QLabel):
    def __init__(self, parent, hint):
        QLabel.__init__(self, parent)

        # connect to a combobox
        if isinstance(parent, QComboBox):
            if not parent.isEditable():
                parent.setEditable(True)
                parent.setInsertPolicy(QComboBox.NoInsert)
            # connect to the line edit method
            if parent.isEditable():
                lineEdit = parent.lineEdit()
                lineEdit.textChanged.connect(self.toggleVisibility)
                self.setAlignment(lineEdit.alignment())
            self.setCursor(Qt.IBeamCursor)

        # connect to a lineedit
        elif isinstance(parent, (QLineEdit, QTextEdit, QPlainTextEdit)):
            parent.textChanged.connect(self.toggleVisibility)
            self.setAlignment(Qt.AlignTop)
            self.setCursor(Qt.IBeamCursor)

        elif isinstance(parent, QTreeWidget):
            model = parent.model()
            model.rowsInserted.connect(self.toggleVisibility)
            model.rowsRemoved.connect(self.toggleVisibility)
            self.setAlignment(Qt.AlignCenter)

        # update the information
        self.setText(hint)

        # show the palette in gray
        palette = self.palette()
        color = palette.color(palette.AlternateBase).darker(125)

        # set the color for all the roles
        palette.setColor(palette.WindowText, color)
        palette.setColor(palette.Text, color)
        self.setPalette(palette)
        parent.installEventFilter(self)
        self.move(6, 4)

        self.raise_()

    def enabled(self):
        return self._enabled

    def eventFilter(self, object, event):
        if event.type() == event.Resize:
            self.resizeHintHelper()
        return False

    def hint(self):
        return self.text()

    def resizeHintHelper(self):
        parent = self.parent()
        if isinstance(parent, QComboBox) and parent.isEditable():
            geo = parent.lineEdit().geometry()
            self.setGeometry(geo.x() + 6, geo.y(), geo.width() - 6, geo.height())
        else:
            geo = parent.geometry()
            self.resize(geo.width() - 6, geo.height() - 4)

    def setEnabled(self, state):
        self._enabled = state
        super(HintHelper, self).setVisible(state)

    def setHint(self, text):
        self.setText(text)
        self.adjustSize()

    def setVisible(self, state):
        self.toggleVisibility()

    def toggleVisibility(self):
        """ Toggles the visibility of the hint based on the state of the widget """
        if not self.isEnabled():
            QLabel.setVisible(self, False)
        parent = self.parent()
        state = parent.isVisible()
        # check a combobox
        if isinstance(parent, QComboBox):
            state = parent.isEditable() and parent.lineEdit().text() == ''
        # check a lineedit
        elif isinstance(parent, QLineEdit):
            state = parent.text() == ''
        # check a textedit
        elif isinstance(parent, (QTextEdit, QPlainTextEdit)):
            state = parent.toPlainText() == ''
        if isinstance(parent, QTreeWidget):
            state = not bool(parent.topLevelItemCount())
        QLabel.setVisible(self, state)
        self.resizeHintHelper()
