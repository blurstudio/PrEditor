##
#   \namespace  waitbar
#
#   \remarks    This is a simple progress bar with undefined progress.
#
#   \author     douglas@blur.com
#   \author     Blur Studio
#   \date       12/01/11
#

import trax
import blurdev
from PyQt4.QtGui import QMovie, QLabel, QDialog, QHBoxLayout


class WaitBar(QDialog):
    def __init__(self, windowTitle='Please wait...', parent=None):
        super(self.__class__, self).__init__(parent)
        self.setWindowTitle(windowTitle)
        self.uiBarLBL = QLabel(self)
        self.uiBarMOV = QMovie(blurdev.resourcePath('img/bar.gif'))
        self.uiBarLBL.setMovie(self.uiBarMOV)
        self.uiBarMOV.start()
        self.uiMainLYT = QHBoxLayout(self)
        self.setLayout(self.uiMainLYT)
        self.uiMainLYT.addWidget(self.uiBarLBL)

    def show(self):
        super(self.__class__, self).show()
        self.makeSizeFixed()

    def makeSizeFixed(self):
        geometry = self.geometry()
        width = geometry.width()
        height = geometry.height()
        self.setMinimumWidth(width)
        self.setMinimumHeight(height)
        self.setMaximumWidth(width)
        self.setMaximumHeight(height)
