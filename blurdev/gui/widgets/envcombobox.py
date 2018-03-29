from Qt.QtGui import QBrush, QColor
from Qt.QtWidgets import QComboBox, QStyledItemDelegate
from Qt.QtCore import Qt, Property
import blurdev


class EnvComboBoxDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        parent = self.parent()
        if parent and index.data(parent.DefaultEnvRole) == True:
            self.initStyleOption(option, index)
            brush = index.data(Qt.BackgroundRole)
            if not brush:
                brush = QBrush()
            brush.setColor(parent.defaultEnvBackground)
            brush.setStyle(Qt.SolidPattern)
            option.backgroundBrush = brush
            paletteColor = option.palette.color(option.palette.Text)
            option.palette.setColor(option.palette.Text, parent.defaultEnvColor)
            style = parent.style()  # QApplication.instance().style()
            style.drawControl(style.CE_ItemViewItem, option, painter)
            option.palette.setColor(option.palette.Text, paletteColor)
        else:
            super(EnvComboBoxDelegate, self).paint(painter, option, index)


class EnvComboBox(QComboBox):
    """ QComboBox that uses stylesheets to control its color and the color of its popup items.
    
    Here is a example stylesheet:
        QComboBox#uiEnvironmentDDL, QComboBox#uiEnvironmentDDL QListView::item {
            /* Default color of the default items in the popup via the "QComboBox#uiEnvironmentDDL" selector */
            qproperty-defaultEnvBackground: rgb(0, 200, 0, 150);
            qproperty-defaultEnvColor: black;
            /* All other popup items are styled via the "QComboBox#uiEnvironmentDDL QListView::item" 
            selector. It is also used to style the combo box via the "QComboBox#uiEnvironmentDDL" selector */
            background: rgb(200, 131, 0, 150);
        }
        QComboBox#uiEnvironmentDDL QListView::item:selected {
            /* Style the selected item in the popup */
            background: rgb(0, 0, 255);
        }
        /* Used to style the background color of the combo box when using the defaultEnv */
        QComboBox#uiEnvironmentDDL[defaultActive="true"] {
            background: rgb(0, 200, 0, 150);
        }
    
    Attributes:
        defaultEnvColor: The color to render the default environment item text with.
        defaultEnvBackground: The background color for the default environment item.
    """

    DefaultEnvRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        super(EnvComboBox, self).__init__(parent)
        self._defaultEnvColor = QColor(Qt.black)
        self._defaultEnvBackground = QColor(0, 200, 0, 50)
        self._defaultActive = False
        self.setItemDelegate(EnvComboBoxDelegate(self))
        self.currentIndexChanged.connect(self.updateColors)
        blurdev.core.styleSheetChanged.connect(self.updateColors)

    def defaultEnv(self):
        model = self.model()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(self.DefaultEnvRole) == True:
                return index.data(Qt.DisplayRole)
        return None

    def setDefaultEnv(self, name):
        """ Marks all items in the model using the provided text as defaultEnv
        
        This allows more than one environment to be marked as default as long as it has the same
        name. You take care to not provide two environments with the same name in the combo box as
        the defaultEnv method only returns the text of the first item marked as default.
        
        Args:
            name(str): The text of the item you want to mark as default
        """
        model = self.model()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(Qt.DisplayRole) == name:
                model.setData(index, True, self.DefaultEnvRole)
            else:
                model.setData(index, False, self.DefaultEnvRole)
        self.updateColors()

    def updateColors(self):
        """ Update the defaultActive property and force the stylesheet to refresh """
        self.defaultActive = self.defaultEnv() == self.currentText()
        # Force the styleSheet to re-evaluate so it sees the new defaultActive state.
        sheet = self.styleSheet()
        if not sheet:
            self.setStyleSheet('/**/')
        self.setStyleSheet(sheet)

    @Property(bool)
    def defaultActive(self):
        return self._defaultActive

    @defaultActive.setter
    def defaultActive(self, color):
        self._defaultActive = color

    @Property(QColor)
    def defaultEnvColor(self):
        return self._defaultEnvColor

    @defaultEnvColor.setter
    def defaultEnvColor(self, color):
        self._defaultEnvColor = color

    @Property(QColor)
    def defaultEnvBackground(self):
        return self._defaultEnvBackground

    @defaultEnvBackground.setter
    def defaultEnvBackground(self, color):
        self._defaultEnvBackground = color
