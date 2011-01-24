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


def test():
    from blurdev.gui import Dialog
    from PyQt4.QtGui import QVBoxLayout

    dlg = Dialog()
    dlg.setWindowTitle('testing')
    layout = QVBoxLayout()
    layout.addWidget(PreviewWidget(dlg))
    dlg.setLayout(layout)
    dlg.show()
    return dlg


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication

    app = QApplication([])
    app.setStyle('Plastique')
    dlg = test()
    app.exec_()
