##
#   :namespace  python.blurdev.gui.widgets.editabletabbar
#
#   :remarks    A tab bar that alows you to rename its tabs by double clicking on the
#               tab
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       09/24/12
#

from Qt.QtCore import Qt, Signal
from Qt.QtWidgets import QLineEdit, QTabBar


class EscapeLineEdit(QLineEdit):
    """
        :remarks    Subclass of QLineEdit that will emit editingCanceled if the escape
                    key is pressed.
        :param		text		<str>			Text shown in the widget. Default: ''
        :param		parent		<QWidget>||None	The parent of the widget. Default: None
        :param      selected    <QWidget>       If True the text will be selected.
                                                Default: True
    """

    editingCanceled = Signal()

    def __init__(self, text='', parent=None, selected=True):
        super(EscapeLineEdit, self).__init__(parent)
        self.setText(text)
        if selected:
            self.selectAll()
        self.setAlignment(Qt.AlignHCenter)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.editingCanceled.emit()
        else:
            super(EscapeLineEdit, self).keyPressEvent(event)


class EditableTabBar(QTabBar):
    """
        :remarks    This tab bar allows you to double click on a tab and rename it
                    without extra dialogs. Commit the change by pressing enter, discard
                    the change by pressing escape.
        :param		parent	<QWidget>||None
    """

    def __init__(self, parent=None):
        super(EditableTabBar, self).__init__(parent)
        self.lineEdit = None
        self.editingIndex = -1

    def editingCanceled(self):
        if self.lineEdit:
            # block signals because editingFinished gets emitted when closing the
            # lineEdit
            self.lineEdit.blockSignals(True)
            self.lineEdit.close()
            self.lineEdit.blockSignals(False)

    def editingFinished(self):
        if self.lineEdit:
            self.setTabText(self.editingIndex, self.lineEdit.text())
            self.lineEdit.close()

    def mouseDoubleClickEvent(self, event):
        for index in range(self.count()):
            rect = self.tabRect(index)
            if rect.contains(event.pos()):
                self.editingIndex = index
                self.lineEdit = EscapeLineEdit(self.tabText(index), self)
                self.lineEdit.setGeometry(rect)
                self.lineEdit.editingFinished.connect(
                    self.editingFinished
                )  # enter pressed
                self.lineEdit.editingCanceled.connect(
                    self.editingCanceled
                )  # escape pressed
                self.lineEdit.show()
                self.lineEdit.setFocus()
                break
        else:
            self.editingIndex = -1
            super(EditableTabBar, self).mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super(EditableTabBar, self).resizeEvent(event)
        if self.lineEdit and self.lineEdit.isVisible():
            self.lineEdit.setGeometry(self.tabRect(self.editingIndex))
