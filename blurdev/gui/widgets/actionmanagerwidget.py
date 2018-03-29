##
#   :namespace  blurdev.gui.widgets.actionmanagerwidget
#
#   :remarks    Creates a widget for editing actions and hotkeys for any other widget
#
#   :author     eric.hulser@drdstudios.com
#   :author     Dr. D Studios
#   :date       06/22/11
#

from Qt import QtCompat
from Qt.QtCore import QSize, Qt, Signal
from Qt.QtGui import QKeySequence
from Qt.QtWidgets import QAction, QTreeWidget, QTreeWidgetItem


class ActionItem(QTreeWidgetItem):
    def __init__(self, action):
        # initialize the tree item
        super(ActionItem, self).__init__()

        # set default information
        text = action.text()
        if not text:
            text = action.objectName()

        self.setText(0, str(text).replace('&', ''))
        self.setText(1, action.shortcut().toString())
        self.setToolTip(0, action.toolTip())
        self.setSizeHint(0, QSize(0, 18))

        # create custom parameters
        self._action = action
        self._shortcut = QKeySequence(action.shortcut())

    def action(self):
        return self._action

    def shortcut(self):
        return self._shortcut


class ActionManagerWidget(QTreeWidget):
    committed = Signal()

    def __init__(self, parent):
        # initialize the super class
        super(ActionManagerWidget, self).__init__(parent)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.setColumnCount(2)
        self.setHeaderLabels(['Action', 'Shortcut'])

        # setup the resizing mode
        header = self.header()
        QtCompat.QHeaderView.setSectionResizeMode(header, 0, header.Stretch)
        QtCompat.QHeaderView.setSectionResizeMode(header, 1, header.ResizeToContents)
        header.setStretchLastSection(False)

    def commit(self):
        self.committed.emit()

    def reset(self):
        pass

    def setActions(self, actions):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)

        self.clear()

        for action in actions:
            item = ActionItem(action)
            if item.text(0):
                self.addTopLevelItem(item)

        self.blockSignals(False)
        self.setUpdatesEnabled(True)

    def setActionsWidget(self, widget, recursive=False):
        # edit the widgets actions
        actions = []
        if recursive:
            actions = widget.findChilren(QAction)
        else:
            actions = [
                action
                for action in widget.findChildren(QAction)
                if action.parent() == widget
            ]

        self.setActions(actions)

    @staticmethod
    def editActions(actions):
        from blurdev.gui import Dialog
        from Qt.QtWidgets import QDialogButtonBox, QVBoxLayout

        # create the main dialog
        dlg = Dialog()
        dlg.setWindowTitle('Action Manager')

        # create the widget
        widget = ActionManagerWidget(dlg)
        widget.setActions(actions)

        # create the buttons
        options = (
            QDialogButtonBox.Reset | QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        btns = QDialogButtonBox(options, Qt.Horizontal, dlg)

        # create the layout
        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.addWidget(btns)

        dlg.setLayout(layout)

        # create connections
        btns.accepted.connect(widget.commit)
        btns.rejected.connect(dlg.reject)
        widget.committed.connect(dlg.accept)

        # run the dialog
        if dlg.exec_():
            return True
        return False

    @staticmethod
    def editWidget(widget, recursive=False):
        # edit the widgets actions
        actions = []
        if recursive:
            actions = widget.findChilren(QAction)
        else:
            actions = [
                action
                for action in widget.findChildren(QAction)
                if action.parent() == widget
            ]

        ActionManagerWidget.editActions(widget.findChildren(QAction))
