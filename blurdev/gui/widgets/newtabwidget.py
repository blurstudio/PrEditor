from PyQt4.QtCore import QSize, pyqtSignal
from PyQt4.QtGui import QTabBar, QTabWidget, QPushButton

# This class is pulled from this example
# http://stackoverflow.com/a/20098415
class TabBarPlus(QTabBar):
    plusClicked = pyqtSignal()

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
    addTabClicked = pyqtSignal()

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

    @staticmethod
    def _qDesignerDomXML():
        """
        Explicitly specify the xml so designer understands how to handle this as a container.
        """
        # Note: This doesn't work yet
        xml = []
        xml.append('<ui>')
        xml.append(' <widget class="QTabWidget">')
        xml.append('   <widget class="NewTabWidget" name="NewTabWidget"/>')
        xml.append(' </widget>')
        xml.append(' <customwidgets>')
        xml.append('  <customwidget>')
        xml.append('   <class>NewTabWidget</class>')
        xml.append('   <extends>QTabWidget</extends>')
        xml.append('   <container>1</container>')
        xml.append('  </customwidget>')
        xml.append(' </customwidgets>')
        xml.append('</ui>')
        return '\n'.join(xml)
