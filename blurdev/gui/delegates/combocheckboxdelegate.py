##
# 	\namespace	trax.gui.delegates.combocheckboxdelegate
#
# 	\remarks	The ComboCheckboxDelegate class is designed to let a programmer turn any Combobox into a multi-selection
# 				list that will let a user checkoff multiple options from the drop down list and use them
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/22/09
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class ComboCheckBoxDelegate(QItemDelegate):
    def __init__(self, combobox):
        QItemDelegate.__init__(self, combobox)
        self._hint = 'nothing selected'
        self._multiHint = ''
        self._changed = False
        combobox.setContextMenuPolicy(Qt.CustomContextMenu)
        combobox.connect(combobox, SIGNAL('activated(int)'), self.toggleCheckState)
        combobox.connect(combobox, SIGNAL('currentIndexChanged(int)'), self.updateText)
        combobox.connect(
            combobox,
            SIGNAL('customContextMenuRequested(const QPoint &)'),
            self.showMenu,
        )
        combobox.setEditable(True)
        combobox.setInsertPolicy(QComboBox.NoInsert)

    def checkAll(self):
        combobox = self.parent()
        for index in range(combobox.count()):
            combobox.setItemData(index, QVariant(Qt.Checked))
        self.updateText()

    def checkInvert(self):
        combobox = self.parent()
        for index in range(combobox.count()):
            if combobox.itemData(index) == QVariant(Qt.Checked):
                combobox.setItemData(index, QVariant(Qt.Unchecked))
            else:
                combobox.setItemData(index, QVariant(Qt.Checked))
        self.updateText()

    def checkNone(self):
        combobox = self.parent()
        for index in range(combobox.count()):
            combobox.setItemData(index, QVariant(Qt.Unchecked))
        self.updateText()

    def checkedIndexes(self):
        indexes = []
        for index in range(self.parent().count()):
            if self.itemCheckState(index) == Qt.Checked:
                indexes.append(index)
        return indexes

    def itemCheckState(self, index):
        return self.parent().itemData(index).toInt()[0]

    def paint(self, painter, option, index):
        state, success = index.model().data(index, Qt.UserRole).toInt()
        text = index.model().data(index, Qt.DisplayRole).toString()
        rect = option.rect
        self.drawDisplay(
            painter,
            option,
            QRect(
                rect.x() + rect.height(), rect.y() + 1, rect.width() - 5, rect.height()
            ),
            text,
        )
        self.drawCheck(
            painter,
            option,
            QRect(rect.x(), rect.y() + 1, rect.height() - 2, rect.height() - 2),
            Qt.CheckState(state),
        )

    def setCheckedIndexes(self, indexes):
        indexes.sort()
        combobox = self.parent()
        for index in range(combobox.count()):
            if index in indexes:
                combobox.setItemData(index, QVariant(Qt.Checked))
            else:
                combobox.setItemData(index, QVariant(Qt.Unchecked))
        combobox.blockSignals(True)
        if indexes:
            combobox.setCurrentIndex(indexes[-1])
        else:
            combobox.setCurrentIndex(0)
        combobox.blockSignals(False)
        self.updateText()

    def setHint(self, hint):
        self._hint = hint

    def setItemCheckState(self, index, state):
        self.parent().setItemData(index, QVariant(state))

    def setMultiHint(self, multiHint):
        self._multiHint = multiHint

    def showMenu(self):
        menu = QMenu(self.parent())
        menu.connect(menu.addAction('Check All'), SIGNAL('triggered()'), self.checkAll)
        menu.connect(
            menu.addAction('Check Invert'), SIGNAL('triggered()'), self.checkInvert
        )
        menu.connect(
            menu.addAction('Check None'), SIGNAL('triggered()'), self.checkNone
        )
        menu.popup(QCursor.pos())

    def toggleCheckState(self, index):
        if self.itemCheckState(index) == Qt.Unchecked:
            self.setItemCheckState(index, Qt.Checked)
        else:
            self.setItemCheckState(index, Qt.Unchecked)
        # Keep the pop up visible after toggling a state
        self.parent().showPopup()
        self._changed = True
        self.parent().emit(SIGNAL('currentIndexesChanged()'))
        self.updateText()

    def updateText(self):
        # update the line text
        combobox = self.parent()
        lineEdit = combobox.lineEdit()
        lineEdit.setUpdatesEnabled(False)
        lineEdit.blockSignals(True)
        palette = lineEdit.palette()
        text = lineEdit.text()
        color = combobox.palette().color(QPalette.Text)
        indexes = self.checkedIndexes()
        if len(indexes) == 0:
            color = palette.color(QPalette.AlternateBase).darker(125)
            text = self._hint
        elif len(indexes) > 1:
            texts = []
            for index in indexes:
                texts.append(str(combobox.itemText(index)))
            text = ','.join(texts)
        else:
            text = combobox.itemText(indexes[0])
        palette.setColor(QPalette.Text, color)
        lineEdit.setPalette(palette)
        lineEdit.setText(text)
        lineEdit.setUpdatesEnabled(True)
        lineEdit.blockSignals(False)


# --------------------------------------------------------------------------------
#                          SAMPLE USAGE
# --------------------------------------------------------------------------------
# from blurdev.gui.delegates.combocheckboxdelegate import ComboCheckBoxDelegate
# from PyQt4.QtGui import QDialog, QComboBox, QVBoxLayout, QPushButton, QHBoxLayout
#
# class MyDialog( QDialog ):
#    def __init__( self, parent ):
#        super(MyDialog,self).__init__(parent)
#
#        # create a combobox
#        combobox = QComboBox(self)
#        combobox.addItems( [ 'Item %02i' % (i+1) for i in range(20) ] )
#
#        # create a checkbox delegate
#        combobox.setItemDelegate(ComboCheckBoxDelegate(combobox))
#
#        # store the pointer
#        self.combobox = combobox
#
#        # create example buttons
#        selectall       = QPushButton( 'Select All', self )
#        selectnone      = QPushButton( 'Select None', self )
#        selectinvert    = QPushButton( 'Select Invert', self )
#
#        printindexes    = QPushButton( 'Print Checked', self )
#
#        # create the button layout
#        hlayout = QHBoxLayout()
#        hlayout.addWidget(selectall)
#        hlayout.addWidget(selectnone)
#        hlayout.addWidget(selectinvert)
#        hlayout.addStretch()
#        hlayout.addWidget(printindexes)
#
#        # create the main layout
#        vlayout = QVBoxLayout()
#        vlayout.addWidget(combobox)
#        vlayout.addLayout(hlayout)
#
#        # set as the main
#        self.setLayout(vlayout)
#
#        # create the connections
#        selectall.clicked.connect(      combobox.itemDelegate().checkAll )
#        selectnone.clicked.connect(     combobox.itemDelegate().checkNone )
#        selectinvert.clicked.connect(   combobox.itemDelegate().checkInvert )
#        printindexes.clicked.connect(   self.printItems )
#
#    def printItems( self ):
#        for index in self.combobox.itemDelegate().checkedIndexes():
#            print self.combobox.itemText(index)
#
# import blurdev
# MyDialog(blurdev.core.rootWindow()).show()
