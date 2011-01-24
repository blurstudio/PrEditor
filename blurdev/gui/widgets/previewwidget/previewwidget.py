##
# 	\namespace	python.blurdev.gui.widgetspreviewgraphicsview
#
# 	\remarks	Creates a previewing system for media files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/21/11
#

from PyQt4.QtGui import QGraphicsView


class PreviewWidget(QGraphicsView):
    def __init__(self, parent):
        # initialize the super class
        QGraphicsView.__init__(self, parent)

        # create the scene
        from previewscene import PreviewScene

        self.setScene(PreviewScene(self))

        # create the tools widget
        from toolswidget import ToolsWidget

        self._toolsWidget = ToolsWidget(self)

        # update the geometry
        self.updateGeometry()

    def resizeEvent(self, event):
        QGraphicsView.resizeEvent(self, event)
        self.updateGeometry()

    def updateGeometry(self):
        # update the tools widget
        self._toolsWidget.move(5, 5)
        self._toolsWidget.resize(self._toolsWidget.width(), self.height() - 10)
