##
#   :namespace  python.blurdev.gui.delegates.htmlitemdelegate
#
#   :remarks    Render html inside of a QTreeWidget
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       05/07/15
#

from PyQt4.QtCore import Qt, QRectF, QSize
from PyQt4.QtGui import QTextDocument, QStyle, QAbstractTextDocumentLayout, QPalette
from griddelegate import GridDelegate


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
            # Simply Copying the palette doesn't
            color = ctx.palette.color(QPalette.HighlightedText)
            ctx.palette.setColor(QPalette.Text, color)
        ctx.clip = clip
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

        self.drawGrid(painter, option, index)

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)

        doc = QTextDocument()
        # Delegate system respects new lines even if displaying html
        doc.setHtml(option.text.replace('\n', ''))
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())
