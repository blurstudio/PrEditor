##
#   :namespace  python.blurdev.gui.delegates.htmlitemdelegate
#
#   :remarks    Render html inside of a QTreeWidget
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       05/07/15
#

from Qt.QtCore import QRectF, QSize
from Qt.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from Qt.QtWidgets import QStyle
from .griddelegate import GridDelegate
from blurdev.gui import QtPropertyInit


class HTMLItemDelegate(GridDelegate):
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        if self._gradiated:
            self.drawGradient(painter, option, index)
        # Draw Html
        painter.save()

        doc = QTextDocument(self.parent())
        doc.setHtml(option.text)

        option.text = ""
        option.widget.style().drawControl(QStyle.CE_ItemViewItem, option, painter)

        # shift text right to make icon visible
        iconSize = option.icon.actualSize(option.rect.size())
        painter.translate(option.rect.left() + iconSize.width(), option.rect.top())
        clip = QRectF(
            0, 0, option.rect.width() + iconSize.width(), option.rect.height()
        )

        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        # Copy the parent palette so colors get rendered correctly
        ctx.palette = self.parent().palette()
        if option.state & QStyle.State_Selected:
            # Simply Copying the palette doesn't adjust the highlight text color
            color = ctx.palette.color(QPalette.HighlightedText)
            ctx.palette.setColor(QPalette.Text, color)
        ctx.clip = clip
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

        self.drawGrid(painter, option, index)

    def sizeHint(self, option, index):
        if self.useStaticSizeHint:
            return self.staticSizeHint

        self.initStyleOption(option, index)

        doc = QTextDocument()
        # Delegate system respects new lines even if displaying html
        doc.setHtml(option.text.replace('\n', ''))
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())

    staticSizeHint = QtPropertyInit('_staticSizeHint', QSize())
    useStaticSizeHint = QtPropertyInit('_useStaticSizeHint', False)
