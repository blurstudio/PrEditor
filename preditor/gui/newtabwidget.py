from __future__ import absolute_import

from Qt.QtCore import QSize, Signal
from Qt.QtWidgets import QPushButton, QTabBar, QTabWidget

# This class is pulled from this example
# http://stackoverflow.com/a/20098415


class TabBarPlus(QTabBar):
    plusClicked = Signal()

    def __init__(self, parent=None):
        super(TabBarPlus, self).__init__(parent)
        # Plus Button
        self.uiPlusBTN = QPushButton("+")
        self.uiPlusBTN.setParent(self)
        self.uiPlusBTN.setObjectName('uiPlusBTN')
        self.uiPlusBTN.clicked.connect(self.plusClicked.emit)
        self.movePlusButton()

    def sizeHint(self):
        sizeHint = QTabBar.sizeHint(self)
        width = sizeHint.width()
        height = sizeHint.height()
        return QSize(width + 25, height)

    def resizeEvent(self, event):
        super(TabBarPlus, self).resizeEvent(event)
        self.movePlusButton()

    def tabLayoutChange(self):
        super(TabBarPlus, self).tabLayoutChange()

        self.movePlusButton()

    def movePlusButton(self):
        size = 0
        for i in range(self.count()):
            size += self.tabRect(i).width()

        h = self.geometry().top()
        w = self.width()
        if size > w:  # Show just to the left of the scroll buttons
            self.uiPlusBTN.move(w - 54, h)
        else:
            self.uiPlusBTN.move(size, h)
        # Resize the button to fit the height of the tab bar
        hint = self.sizeHint().height()
        self.uiPlusBTN.setMaximumSize(hint, hint)
        self.uiPlusBTN.setMinimumSize(hint, hint)


class NewTabWidget(QTabWidget):
    addTabClicked = Signal()

    def __init__(self, parent=None):
        super(NewTabWidget, self).__init__(parent)

        # Tab Bar
        self._tab = TabBarPlus()
        self.setTabBar(self._tab)

        # Properties
        self.setMovable(True)
        self.setTabsClosable(True)

        # Signals
        self._tab.plusClicked.connect(self.addTabClicked.emit)
