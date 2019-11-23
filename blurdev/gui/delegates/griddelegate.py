##
# 	\namespace	python.blurdev.gui.delegates.blurgriddelegate
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

from Qt.QtCore import Qt, QRectF, QLineF
from Qt.QtGui import QColor, QPen, QTextDocument, QLinearGradient, QBrush
from Qt.QtWidgets import (
    QStyledItemDelegate,
    QApplication,
    QStyleOptionButton,
    QLineEdit,
)


class GridDelegate(QStyledItemDelegate):
    def __init__(self, parent, gridColor=None):
        super(GridDelegate, self).__init__(parent)
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
        self._identifier = ''
        self.destroyed.connect(self.aboutToBeDestroyed)

    def __call_delegate__(self, name, *args, **kwargs):
        """ Attempt to call a delegate override method if implemented.

        Args:
            name (str): The name of the function being called. This does
                not include the identifierName.

        Returns:
            Returns the return of the delegate or super call or None.
        """
        identifier = self.identifierName(name)
        if self._delegate and hasattr(self._delegate, identifier):
            funct = getattr(self._delegate, identifier)
            if 'tree' in funct.func_code.co_varnames:
                kwargs['tree'] = self.parent()
            return funct(*args, **kwargs)
        superclass = super(GridDelegate, self)
        if hasattr(superclass, name):
            return getattr(superclass, name)(*args, **kwargs)

    def aboutToBeDestroyed(self):
        """ Prevent crashes due to "delete loops" """
        self._delegate = None

    def checkboxRect(self, option, index):
        if self.parent():
            style = self.parent().style()
            widget = self.parent()
        else:
            style = QApplication.style()
            widget = None
        checkboxStyle = QStyleOptionButton()
        checkboxStyle.rect = option.rect
        rect = style.subElementRect(style.SE_CheckBoxIndicator, checkboxStyle, widget)
        state = index.model().data(index, Qt.CheckStateRole)
        return rect, state

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
        """ Creates a new editor for the provided widget

        Args:
            parent (Qt.QtWidgets.QWidget): The parent of the new widget.
            option (Qt.QtWidgets.QStyleOptionViewItem):
            index (Qt.QtCore.QModelIndex):

        Returns:
            Qt.QtWidgets.QWidget: The editor widget to show or None.

        See Also:
            This is a :py:meth:`blurdev.gui.widgets.blurtreewidget.blurtreewidget.BlurTreeWidget.setDelegate` method.
        """
        self.clearEditor()
        self._editor = self.__call_delegate__('createEditor', parent, option, index)

        if self._editor != None:
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
            super(GridDelegate, self).drawDisplay(painter, option, rect, text)

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
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self.pen())
        # draw the lines
        lines = []
        # add the column line
        if self.showColumnBorders():
            lines.append(
                QLineF(
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
            lines.append(QLineF(x, style.rect.y(), x, style.rect.bottom()))
        # add the bottom line
        if self.showBottomBorder():
            lines.append(
                QLineF(x, style.rect.bottom(), style.rect.right(), style.rect.bottom())
            )
        painter.drawLines(lines)

    def identifier(self):
        return self._identifier

    def identifierName(self, name):
        """
            \Remarks	Returns the name. If self._identifier is set it will return place the identifier before name and capitalize the first 
                        letter of name.
            \param		name		<str>
            \Return		<str>		"identifierName" || 'name'
        """
        if self._identifier:
            name = self._identifier + name[0].upper() + name[1:]
        return name

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
        # Note: calling initStyleOption, results in the super paint call drawing what ever is
        # in its cache where it should draw nothing.
        # draw the gradiation
        if self._gradiated:
            self.drawGradient(painter, option, index)
        super(GridDelegate, self).paint(painter, option, index)
        self.drawGrid(painter, option, index)

    def pen(self):
        """ returns this delegates pen """
        return self._pen

    def setDelegate(self, delegate):
        self._delegate = delegate

    def setEditorData(self, editor, index):
        """
        See Also:
            This is a :py:meth:`blurdev.gui.widgets.blurtreewidget.blurtreewidget.BlurTreeWidget.setDelegate` method.
        """
        self.__call_delegate__('setEditorData', editor, index)

    def setGradiated(self, state):
        self._gradiated = state

    def setGridColor(self, color):
        """ sets the pen color for this delegate """

        self._pen.setColor(QColor(color))

    def setIdentifier(self, identifier):
        self._identifier = identifier

    def setPen(self, pen):
        """ sets the current grid delegate pen """

        self._pen = QPen(pen)

    def setGradientEndColor(self, clr):
        self._gradientEndColor = clr

    def setGradientStartColor(self, clr):
        self._gradientStartColor = clr

    def setModelData(self, editor, model, index):
        """
        See Also:
            This is a :py:meth:`blurdev.gui.widgets.blurtreewidget.blurtreewidget.BlurTreeWidget.setDelegate` method.
        """
        self.__call_delegate__('setModelData', editor, model, index)

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
