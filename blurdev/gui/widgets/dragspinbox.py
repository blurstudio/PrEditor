from PyQt4.QtCore import QPoint, Qt, QEvent, pyqtProperty
from PyQt4.QtGui import QSpinBox, QDoubleSpinBox, QCursor, QMouseEvent, QApplication


class _DragSpin(object):
    DRAG_NONE = 0
    DRAG_HORIZONTAL = 1
    DRAG_VERTICAL = 2

    CURSOR_NONE = 0
    CURSOR_BLANK = 1
    CURSOR_ARROWS = 2

    def __init__(self, *args, **kwargs):
        self._dragSensitivity = 5  # pixels for one step
        self._startSensitivity = 10  # pixel move to start the dragging
        self._cursorLock = False
        self._wrapBoundary = 10  # wrap when within boundary of screen edge
        self._dragCursor = self.CURSOR_ARROWS

        self._fastModifier = Qt.ControlModifier
        self._slowModifier = Qt.ShiftModifier

        self._fastMultiplier = 5
        self._slowDivisor = 5

        # private vars
        self._lastPos = QPoint()
        self._leftover = 0
        self._dragStart = None
        self._firstDrag = False
        self._dragType = self.DRAG_NONE

    def eFilter(self, cls, o, e):
        if e.type() == QEvent.MouseButtonPress:
            if e.button() & Qt.RightButton:  # reset-on-right-click a-la 3dsMax
                self.setValue(self._defaultValue)
                return True

        elif e.type() == QEvent.ContextMenu:
            return True  # Kill the context menu

        elif e.type() == QEvent.MouseMove:
            stepHolder = self.singleStep()

            if e.modifiers() & self._fastModifier:
                self.setSingleStep(stepHolder * self._fastMultiplier)
            elif e.modifiers() & self._slowModifier:
                self.setSingleStep(stepHolder / self._slowDivisor)

            if self._dragType:
                if self._dragType == self.DRAG_HORIZONTAL:
                    delta = e.pos().x() - self._lastPos.x()
                else:
                    delta = self._lastPos.y() - e.pos().y()

                self._leftover += delta
                self._lastPos = e.pos()
                val = self.value()

                self.stepBy(int(self._leftover / self._dragSensitivity))
                self._leftover %= self._dragSensitivity

                if self._cursorLock:
                    QCursor.setPos(self.mapToGlobal(self._dragStart))
                    self._lastPos = self._dragStart

                else:
                    dtop = QApplication.desktop()
                    p = e.globalPos()
                    screen = dtop.screenNumber(p)
                    r = dtop.availableGeometry(screen)
                    b = self._wrapBoundary

                    # when wrapping move to the other side in by 2*boundary
                    # so we don't loop the wrapping
                    if p.x() > r.right() - b:
                        p.setX(r.left() + 2 * b)

                    if p.x() < r.left() + b:
                        p.setX(r.right() - 2 * b)

                    if p.y() > r.bottom() - b:
                        p.setY(r.top() + 2 * b)

                    if p.y() < r.top() + b:
                        p.setY(r.bottom() - 2 * b)

                    if p != e.globalPos():
                        QCursor.setPos(p)
                        self._lastPos = self.mapFromGlobal(p)
                        self._leftover = 0

            else:
                if e.buttons() & Qt.LeftButton:  # only allow left-click dragging
                    if self._dragStart is None:
                        self._dragStart = e.pos()

                    if abs(e.x() - self._dragStart.x()) > self._startSensitivity:
                        self._dragType = self.DRAG_HORIZONTAL
                        arrowCursor = Qt.SizeHorCursor
                    if abs(e.y() - self._dragStart.y()) > self._startSensitivity:
                        self._dragType = self.DRAG_VERTICAL
                        arrowCursor = Qt.SizeVerCursor

                    if self._dragType:
                        self._leftover = 0
                        self._lastPos = e.pos()
                        self._firstDrag = True
                        self.interpretText()

                        if self._dragCursor == self.CURSOR_BLANK:
                            QApplication.setOverrideCursor(Qt.BlankCursor)
                        elif self._dragCursor == self.CURSOR_ARROWS:
                            QApplication.setOverrideCursor(arrowCursor)

                        if e.buttons() & Qt.LeftButton:
                            # Send mouseRelease to spin buttons when dragging
                            # otherwise the spinbox will keep ticking
                            mouseup = QMouseEvent(
                                QEvent.MouseButtonRelease,
                                e.pos(),
                                Qt.LeftButton,
                                e.buttons(),
                                e.modifiers(),
                            )
                            QApplication.sendEvent(o, mouseup)

            self.setSingleStep(stepHolder)

        elif e.type() == QEvent.MouseButtonRelease:
            # Only reset the dragType if it's *not* the first drag event release
            if self._firstDrag:
                self._firstDrag = False
            elif self._dragType:
                self._dragType = self.DRAG_NONE
                self._lastPos = QPoint()
                self._dragStart = None
                if self._dragCursor:
                    QApplication.restoreOverrideCursor()

        return cls.eventFilter(self, o, e)

    def setDragSensitivity(self, dragSensitivity):
        self._dragSensitivity = dragSensitivity

    def getDragSensitivity(self):
        return self._dragSensitivity

    def setStartSensitivity(self, val):
        self._startSensitivity = val

    def getStartSensitivity(self):
        return self._startSensitivity

    def setCursorLock(self, val):
        self._cursorLock = val

    def getCursorLock(self):
        return self._cursorLock

    def setWrapBoundary(self, val):
        self._wrapBoundary = val

    def getWrapBoundary(self):
        return self._wrapBoundary

    def setDragCursor(self, val):
        self._dragCursor = val

    def getDragCursor(self):
        return self._dragCursor

    def setFastModifier(self, val):
        self._fastModifier = val

    def getFastModifier(self):
        return self._fastModifier

    def setFastMultiplier(self, val):
        self._fastMultiplier = val

    def getFastMultiplier(self):
        return self._fastMultiplier

    def setSlowModifier(self, val):
        self._slowModifier = val

    def getSlowModifier(self):
        return self._slowModifier

    def setSlowDivisor(self, val):
        self._slowDivisor = val

    def getSlowDivisor(self):
        return self._slowDivisor

    dragSensitivity = pyqtProperty('int', getDragSensitivity, setDragSensitivity)
    startSensitivity = pyqtProperty('int', getStartSensitivity, setStartSensitivity)
    cursorLock = pyqtProperty('bool', getCursorLock, setCursorLock)
    wrapBoundary = pyqtProperty('int', getWrapBoundary, setWrapBoundary)
    dragCursor = pyqtProperty('int', getDragCursor, setDragCursor)
    fastModifier = pyqtProperty(Qt.KeyboardModifier, getFastModifier, setFastModifier)
    slowModifier = pyqtProperty(Qt.KeyboardModifier, getSlowModifier, setSlowModifier)
    fastMultiplier = pyqtProperty('int', getFastMultiplier, setFastMultiplier)
    slowDivisor = pyqtProperty('int', getSlowDivisor, setSlowDivisor)


class DragSpinBox(_DragSpin, QSpinBox):
    def __init__(self, *args, **kwargs):
        # Awww, can't just use super() to make this work :(
        QSpinBox.__init__(self, *args, **kwargs)
        _DragSpin.__init__(self)
        self._defaultValue = 0
        self.installEventFilter(self)

    def eventFilter(self, o, e):
        return self.eFilter(QSpinBox, o, e)

    def getDefaultValue(self):
        return self._defaultValue

    def setDefaultValue(self, val):
        self._defaultValue = val

    defaultValue = pyqtProperty('int', getDefaultValue, setDefaultValue)


class DragDoubleSpinBox(_DragSpin, QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        # Awww, can't just use super() to make this work :(
        QDoubleSpinBox.__init__(self, *args, **kwargs)
        _DragSpin.__init__(self)
        self._defaultValue = 0.0
        self.installEventFilter(self)

    def eventFilter(self, o, e):
        return self.eFilter(QDoubleSpinBox, o, e)

    def getDefaultValue(self):
        return self._defaultValue

    def setDefaultValue(self, val):
        self._defaultValue = val

    defaultValue = pyqtProperty('double', getDefaultValue, setDefaultValue)


if __name__ == "__main__":
    from PyQt4.QtGui import QWidget, QApplication, QHBoxLayout
    import sys

    app = QApplication(sys.argv)
    wid = QWidget()

    horizontalLayout = QHBoxLayout(wid)
    spinBox = DragSpinBox(wid)
    horizontalLayout.addWidget(spinBox)
    doubleSpinBox = DragDoubleSpinBox(wid)
    horizontalLayout.addWidget(doubleSpinBox)

    wid.show()
    sys.exit(app.exec_())
