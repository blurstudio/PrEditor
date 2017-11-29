from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGraphicsView, QAction, QMenu, QApplication, QMouseEvent
from blurdev.gui import pyqtPropertyInit


class PanZoomGraphicsView(QGraphicsView):
    """ A QGraphicsView that enables panning and zooming.

    There are several properties that control enabling pan and zoom. You can override
    the panEnabled method to customize enabling pan mode, and zoomEnabled to customize
    the what is required to enable zooming while scrolling the mouse wheel.

    Attributes:
        panKeys (list): A list of Qt.Key's that enable panning while left clicking.
        panMouseButton (Qt.MouseButton): A mouse button that enables paning while pressed.
        uiActualPixelsACT (QAction): QAction that resets zoom to 100%.
        uiFitOnScreenACT (QAction): QAction that zooms out so the entire scene is visible.
        zoomModifiers (Qt.Modifier): A list of Qt.Modifier's that enables zooming by mouse scroll.
    """

    def __init__(self, *args, **kwargs):
        super(PanZoomGraphicsView, self).__init__(*args, **kwargs)
        self._lastDragMode = None

        # This action is used to set the scene scale to 100%
        self.uiActualPixelsACT = QAction('Actual Pixels', self)
        self.uiActualPixelsACT.triggered.connect(self.actualPixels)
        self.uiActualPixelsACT.setShortcut('Ctrl+1')
        self.uiActualPixelsACT.setToolTip('Actual Pixels')
        self.addAction(self.uiActualPixelsACT)

        # This action is used to zoom out so the entire scene fits the view
        self.uiFitOnScreenACT = QAction('Fit on Screen', self)
        self.uiFitOnScreenACT.triggered.connect(self.fitOnScreen)
        self.uiFitOnScreenACT.setShortcut('Ctrl+0')
        self.uiFitOnScreenACT.setToolTip('Fit on Screen')
        self.addAction(self.uiFitOnScreenACT)

    def _showContextMenu(self, pos):
        """ The default context menu.
        """
        menu = QMenu(self)
        menu.addAction(self.uiActualPixelsACT)
        menu.addAction(self.uiFitOnScreenACT)
        self.customizeContextMenu(menu)
        menu.popup(self.mapToGlobal(pos))

    def customizeContextMenu(self, menu):
        """ Allows customizing the right click menu.

        Override this method to customize the right click menu when
        not clicking on a item.

        Args:
            menu (QMenu): The menu that will be shown.
        """
        menu.addSeparator()
        act = menu.addAction('Load Background Image')

    def actualPixels(self):
        """ Set the scene scale to 100%.
        """
        transform = self.transform()
        self.scale(1 / transform.m11(), 1 / transform.m22())

    def contextMenuEvent(self, event):
        # Show the item menu if right clicking on a item
        super(PanZoomGraphicsView, self).contextMenuEvent(event)
        # Otherwise show the view menu instead.
        if not event.isAccepted():
            self._showContextMenu(event.pos())
            event.setAccepted(True)

    def fitOnScreen(self):
        """ Zoom the view to fit the scene without the need to scroll.
        """
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def keyPressEvent(self, event):
        """ Enable paning if the correct key button was pressed.
        """
        if self.panEnabled(key=event.key()) and not event.isAutoRepeat():
            if self._lastDragMode is None:
                # Prevent loosing lastDragMode if the user activates both the
                # keyboard and mouse modifiers
                self._lastDragMode = self.dragMode()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setInteractive(False)
            return
        super(PanZoomGraphicsView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """ Enable paning if the correct key button was released.
        """
        if self.panEnabled(key=event.key()) and not event.isAutoRepeat():
            if self._lastDragMode is not None:
                self.setDragMode(self._lastDragMode)
                self._lastDragMode = None
                self.setInteractive(True)
                return
        super(PanZoomGraphicsView, self).keyReleaseEvent(event)

    def mousePressEvent(self, event):
        """ Enable paning if the correct mouse button was pressed.
        """
        if self.panEnabled(mouse=event.button()):
            if self._lastDragMode is None:
                # Prevent loosing lastDragMode if the user activates both the
                # keyboard and mouse modifiers
                self._lastDragMode = self.dragMode()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setInteractive(False)
            if event.button() != Qt.LeftButton:
                # ScrollHandDrag mode only works with the left mouse button.
                # change the event to be a left mouse click so panning works.
                event = QMouseEvent(
                    event.type(),
                    event.pos(),
                    Qt.LeftButton,
                    Qt.LeftButton,
                    event.modifiers(),
                )
        super(PanZoomGraphicsView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """ Disable paning if the correct mouse button was released.
        """
        if self.panEnabled(mouse=event.button()):
            if self._lastDragMode is not None:
                self.setDragMode(self._lastDragMode)
                self._lastDragMode = None
                self.setInteractive(True)
                if event.button() != Qt.LeftButton:
                    # ScrollHandDrag mode only works with the left mouse button.
                    # change the event to be a left mouse click so panning works.
                    event = QMouseEvent(
                        event.type(),
                        event.pos(),
                        Qt.LeftButton,
                        Qt.LeftButton,
                        event.modifiers(),
                    )
        super(PanZoomGraphicsView, self).mouseReleaseEvent(event)

    def panEnabled(self, key=None, mouse=None):
        """ Override this method to customize when panning is enabled.

        Args:
            key (Qt.Key or None, optional): If not None(default), returns True if this
                key is in self.panKeys.
            mouse (Qt.MouseButton or None, optional): If not None(default), returns True
                if this button matches self.panMouseButton.

        Returns:
            bool: Returns if panning is enabled for the given inputs.
        """
        if key:
            return key in self.panKeys
        if mouse:
            return mouse == self.panMouseButton
        return False

    def wheelEvent(self, event):
        if self.zoomEnabled():
            # Zoom Factor
            zoomInFactor = 1.25
            zoomOutFactor = 1 / zoomInFactor

            # Set Anchors
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            # Save the scene pos
            oldPos = self.mapToScene(event.pos())

            # Zoom
            if event.delta() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            self.scale(zoomFactor, zoomFactor)

            # Get the new position
            newPos = self.mapToScene(event.pos())

            # Move scene to old position
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y())
        else:
            super(PanZoomGraphicsView, self).wheelEvent(event)

    def zoomEnabled(self):
        """ Override this method to customize when zooming is enabled

        Returns:
            bool: If QApplication's current keyboardModifiers is equal to self.zoomModifiers.
        """
        return QApplication.instance().keyboardModifiers() in self.zoomModifiers

    panKeys = pyqtPropertyInit('_panKey', [Qt.Key_Space])
    panMouseButton = pyqtPropertyInit('_panMouseButton', Qt.MidButton)
    zoomModifiers = pyqtPropertyInit('_zoomModifiers', [Qt.AltModifier])
