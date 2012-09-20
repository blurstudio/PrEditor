##
#   :namespace  blurdev.gui.widgets.clearabledateedit
#
#   :remarks
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       05/24/12
#

import blurdev
from PyQt4.QtCore import Qt, QDate
from PyQt4.QtGui import (
    QDateEdit,
    QToolButton,
    QStyle,
    QStyleOptionSpinBox,
    QIcon,
    QPixmap,
    QLineEdit,
)


class ClearableDateEdit(QDateEdit):
    def __init__(self, parent):
        super(ClearableDateEdit, self).__init__(parent)
        self.uiClearBTN = QToolButton(self)
        self.uiClearBTN.setText('No')
        icon = QIcon()
        icon.addPixmap(
            QPixmap(blurdev.resourcePath('img/calendar_disabled.png')),
            QIcon.Normal,
            QIcon.Off,
        )
        icon.addPixmap(
            QPixmap(blurdev.resourcePath('img/calendar_enabled.png')),
            QIcon.Normal,
            QIcon.On,
        )
        self.uiClearBTN.setIcon(icon)

        self.uiClearBTN.resize(20, 20)
        self.uiClearBTN.setCheckable(True)
        self.uiClearBTN.setChecked(True)
        self.uiClearBTN.setToolTip('Remove date')
        self.uiClearBTN.clicked.connect(self.clearClicked)
        self.uiNoDateLBL = QLineEdit(self)
        self.uiNoDateLBL.setText('No Date')
        self.uiNoDateLBL.setReadOnly(False)
        self.uiNoDateLBL.setVisible(False)
        self.uiNoDateLBL.setFocusPolicy(Qt.NoFocus)
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)

    def clear(self):
        self.uiClearBTN.setChecked(False)
        self.clearClicked(False)

    def clearClicked(self, state):
        self.lineEdit().setEnabled(state)
        self.lineEdit().setVisible(state)
        self.uiNoDateLBL.setVisible(not state)

    def date(self):
        if self.uiClearBTN.isChecked():
            return super(ClearableDateEdit, self).date()
        return QDate()

    def keyPressEvent(self, event):
        if self.uiClearBTN.isChecked():
            super(ClearableDateEdit, self).keyPressEvent(event)

    def isCleared(self):
        return self.uiClearBTN.isChecked()

    def mousePressEvent(self, event):
        if self.uiClearBTN.isChecked():
            super(ClearableDateEdit, self).mousePressEvent(event)

    def resizeEvent(self, event):
        opt = QStyleOptionSpinBox()
        opt.rect = self.rect()
        cbWidth = self.uiClearBTN.size().width()
        self.uiClearBTN.resize(cbWidth, opt.rect.height())
        opt.rect.setX(cbWidth)
        combo = self.style().subControlRect(
            QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxEditField, self
        )
        self.lineEdit().setGeometry(combo)
        self.uiNoDateLBL.setGeometry(combo)

    def setDate(self, date):
        super(ClearableDateEdit, self).setDate(date)
        self.uiClearBTN.setChecked(date.isValid())
        self.clearClicked(date.isValid())

    def wheelEvent(self, event):
        if self.uiClearBTN.isChecked():
            super(ClearableDateEdit, self).wheelEvent(event)
