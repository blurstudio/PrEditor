##
# 	\namespace	blurdev.gui.scenes.thumbnailscene.thumbnailitem
#
# 	\remarks	The ThumbnailItem is a QGraphicsRectItem that will contain and cache thumbnails for an image, allowing
# 				for fast rendering within a ThumbnailScene
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		03/31/10
#

from PyQt4.QtGui import QGraphicsRectItem

# -------------------------------------------------------------------------------------------------------------


class ThumbnailItem(QGraphicsRectItem):
    def __init__(self, filename):
        QGraphicsRectItem.__init__(self)

        self._thumbnail = None
        self._filename = filename
        self._thumbGroup = None
        self._sortData = ''
        self._dragEnabled = False
        self._mimeText = ''

        # update the flag options
        self.setFlags(
            QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemIsFocusable
        )

    def clearThumbnail(self):
        self._thumbnail = None

    def dragEnabled(self):
        return self._dragEnabled

    def paint(self, painter, option, widget):
        from PyQt4.QtCore import Qt

        # draw the thumbnail
        scene = self.scene()
        padding = scene.cellPadding()
        thumbsize = scene.thumbnailSize()
        thumb = self.thumbnail()
        px = ((thumbsize.width() + padding.width()) - thumb.width()) / 2
        py = ((thumbsize.height() + padding.height()) - thumb.height()) / 2

        painter.drawPixmap(px, py, thumb)

        # draw highlight around the thumbnail
        if self.isSelected():
            painter.setBrush(Qt.NoBrush)
            pen = painter.pen()
            pen.setColor(scene.highlightBrush().color())
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(px - 2, py - 2, thumb.width() + 4, thumb.height() + 4)

    def mimeText(self):
        return self._mimeText

    def mouseDoubleClickEvent(self, event):
        from PyQt4.QtCore import Qt

        QGraphicsRectItem.mouseDoubleClickEvent(self, event)
        if event.button() == Qt.LeftButton:
            self.scene().itemDoubleClicked.emit(self)

    def mousePressEvent(self, event):
        from PyQt4.QtCore import Qt

        # emit the menu request signal
        if event.button() == Qt.RightButton:
            self.scene().itemMenuRequested.emit(self)
            self.setSelected(True)

        else:
            QGraphicsRectItem.mousePressEvent(self, event)

            if self.dragEnabled():
                from PyQt4.QtCore import QMimeData, QPoint
                from PyQt4.QtGui import QDrag
                import blurdev

                # create the mimedata
                mimeData = QMimeData()
                mimeData.setText(self.mimeText())

                # create the drag
                drag = QDrag(blurdev.core.activeWindow())
                drag.setMimeData(mimeData)
                drag.setPixmap(self.thumbnail())
                drag.setHotSpot(
                    QPoint(drag.pixmap().width() / 2, drag.pixmap().height() / 2)
                )

                drag.exec_()

    def setDragEnabled(self, state):
        self._dragEnabled = state

    def setMimeText(self, text):
        self._mimeText = text

    def setSortData(self, data):
        self._sortData = data

    def setThumbnail(self, pixmap):
        self._thumbnail = pixmap

    def setThumbGroup(self, thumbGroup):
        self._thumbGroup = thumbGroup

    def sortData(self):
        return self._sortData

    def thumbnail(self):
        if not (self._thumbnail):
            from PyQt4.QtCore import Qt
            from PyQt4.QtGui import QPixmap

            import blurdev

            self._thumbnail = blurdev.gui.findPixmap(
                self._filename, thumbSize=self.scene().thumbnailSize()
            )
        return self._thumbnail

    def thumbGroup(self):
        return self._thumbGroup
