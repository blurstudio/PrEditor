##
# 	\namespace	trax.gui.delegates.blurgriddelegate
#
# 	\remarks	This module provides a simple way to draw grids for trees
# 				If you need to make complex editing controlled by a diffrent class you can use setDelegate.
# 				If you set delegate the delegate should impliment any of the folowing functions, they are optional.
# 					def createEditor( self, parent, option, index ):
# 					def setEditorData( self, editor, index ):
# 					def setModelData( self, editor, model, index ):
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/18/09
#

from PyQt4.QtCore import Qt, QRectF, QLine
from PyQt4.QtGui import (
    QColor,
    QItemDelegate,
    QPen,
    QLineEdit,
    QTextDocument,
    QLinearGradient,
    QBrush,
)


class GridDelegate(QItemDelegate):
    def __init__(self, parent, gridColor=None):
        QItemDelegate.__init__(self, parent)
        if not gridColor:
            gridColor = QColor(122, 126, 134)
        # store the pen for the grid
        self._editor = None
        self._pen = QPen(Qt.SolidLine)
        self._pen.setColor(gridColor)
        self._showRichText = False
        # store the custom properties
        self._gradientStartColor = QColor(230, 230, 230)
        self._gradientEndColor = QColor(209, 209, 209)
        self._gradiated = False
        self._showColumnBorders = True
        self._showBottomBorder = True
        self._showTree = True
        self._delegate = None
        self.destroyed.connect(self.aboutToBeDestroyed)

    def aboutToBeDestroyed(self):
        """ Prevent crashes due to "delete loops" """
        self._delegate = None

    def clearEditor(self):
        """
            \remarks	clears the reference to this editor
        """
        try:
            self._editor.close()
            self._editor.deleteLater()
        # TODO: Bare "except" clauses are bad, specify an exception.  At the
        # bare minimum use "except Exception" (brendana 4/4/11)
        except:
            pass
        self._editor = None

    def createEditor(self, parent, option, index):
        """
            \remarks	overloaded from QItemDelegate, creates a new editor for the inputed widget
            \param		parent	<QWidget>
            \param		option	<QStyleOptionViewItem>
            \param		index	<QModelIndex>
            \return		<QWidget> editor
        """
        self.clearEditor()
        if self._delegate and hasattr(self._delegate, 'createEditor'):
            self._editor = self._delegate.createEditor(parent, option, index)
            if not self._editor:
                return None
        else:
            self._editor = QLineEdit(parent)
        self._editor.setFocus()
        self._editor.setFocusPolicy(Qt.StrongFocus)
        return self._editor

    def delegate(self):
        return self._delegate

    def drawDisplay(self, painter, option, rect, text):
        if self._showRichText:
            # create the document
            doc = QTextDocument()
            doc.setTextWidth(float(rect.width()))
            doc.setHtml(text)
            # draw the contents
            painter.translate(rect.x(), rect.y())
            doc.drawContents(
                painter, QRectF(0, 0, float(rect.width()), float(rect.height()))
            )
            painter.translate(-rect.x(), -rect.y())
        else:
            QItemDelegate.drawDisplay(self, painter, option, rect, text)

    def drawGradient(self, painter, option, index):
        gradient = QLinearGradient()
        gradient.setColorAt(0.0, self.gradientStartColor())
        gradient.setColorAt(1.0, self.gradientEndColor())
        gradient.setStart(option.rect.left(), option.rect.top())
        gradient.setFinalStop(option.rect.left(), option.rect.bottom())
        brush = QBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.setBrush(brush)
        painter.drawRect(option.rect)

    def drawGrid(self, painter, style, index):
        """ draw gridlines for this item """
        data = index.model().data(index, Qt.UserRole)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self.pen())
        # draw the lines
        lines = []
        # add the column line
        if self.showColumnBorders():
            lines.append(
                QLine(
                    style.rect.right(),
                    style.rect.y(),
                    style.rect.right(),
                    style.rect.bottom(),
                )
            )
        # determine if this line should be drawn to the 0 mark
        x = style.rect.x()
        if not ((self.showTree() and self.showColumnBorders()) or index.column()):
            x = 0
        elif not index.column() and x:
            lines.append(QLine(x, style.rect.y(), x, style.rect.bottom()))
        # add the bottom line
        if self.showBottomBorder():
            lines.append(
                QLine(x, style.rect.bottom(), style.rect.right(), style.rect.bottom())
            )
        painter.drawLines(lines)

    def isGradiated(self):
        return self._gradiated

    def editor(self):
        """
            \remarks	returns the current editor for this delegate
            \return		<QWidget> || None
        """
        return self._editor

    def gradientStartColor(self):
        return self._gradientStartColor

    def gradientEndColor(self):
        return self._gradientEndColor

    def gridColor(self):
        """ returns the color for the current pen """
        return self._pen.color()

    def paint(self, painter, option, index):
        """ draw the delegate and the grid """
        # draw the gradiation
        if self._gradiated:
            self.drawGradient(painter, option, index)
        QItemDelegate.paint(self, painter, option, index)
        self.drawGrid(painter, option, index)

    def pen(self):
        """ returns this delegates pen """
        return self._pen

    def setDelegate(self, delegate):
        self._delegate = delegate

    def setEditorData(self, editor, index):
        if self._delegate and hasattr(self._delegate, 'setEditorData'):
            self._delegate.setEditorData(editor, index)
        else:
            QItemDelegate.setEditorData(self, editor, index)

    def setGradiated(self, state):
        self._gradiated = state

    def setGridColor(self, color):
        """ sets the pen color for this delegate """

        self._pen.setColor(QColor(color))

    def setPen(self, pen):
        """ sets the current grid delegate pen """

        self._pen = QPen(pen)

    def setGradientEndColor(self, clr):
        self._gradientEndColor = clr

    def setGradientStartColor(self, clr):
        self._gradientStartColor = clr

    def setModelData(self, editor, model, index):
        if self._delegate and hasattr(self._delegate, 'setModelData'):
            self._delegate.setModelData(editor, model, index)
        else:
            QItemDelegate.setModelData(self, editor, model, index)

    def setShowBottomBorder(self, state=True):
        """ sets whether or not bottom borders are drawn """
        self._showBottomBorder = state

    def setShowColumnBorders(self, state=True):
        """ sets whether or not column borders are drawn """
        self._showColumnBorders = state

    def setShowTree(self, state=True):
        """ sets whether or not the delegate show a tree """
        self._showTree = state

    def setShowRichText(self, state=True):
        self._showRichText = state

    def showBottomBorder(self):
        """ returns if this item shows the bottom divider """
        return self._showBottomBorder

    def showColumnBorders(self):
        """ returns if this item shows the column divider """
        return self._showColumnBorders

    def showRichText(self):
        return self._showRichText

    def showTree(self):
        """ returns if this item shows a tree """
        return self._showTree