from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import QAction, QToolBar, QIcon, QMenu, QCursor, QHBoxLayout, QPixmap

import blurdev
from ..gui import Dialog


class ToolbarAction(QAction):
    """ Creates a toolbar that contains links to blurdev Tools
    """

    def __init__(self, parent, toolId):
        QAction.__init__(self, parent)
        self._toolId = toolId
        tool = blurdev.findTool(toolId)
        if tool:
            self.setIcon(QIcon(QPixmap(tool.image())))
            self.setText(tool.displayName())
            self.setToolTip(tool.toolTip())

    def exec_(self):
        blurdev.runTool(self._toolId)

    def remove(self):
        self.parent().removeAction(self)
        self.setParent(None)
        self.deleteLater()

    def toXml(self, xml):
        actionxml = xml.addNode('action')
        actionxml.setAttribute('type', 'default')
        actionxml.setAttribute('toolId', self._toolId)

    @staticmethod
    def fromXml(parent, xml):
        return ToolbarAction(parent, xml.attribute('toolId'))


class ToolsToolBar(QToolBar):
    """ QToolBar sub-class to contain actions for Tools """

    _instance = None

    def __init__(self, parent, title):
        QToolBar.__init__(self, parent)
        self.setWindowTitle(title)
        self.setAcceptDrops(True)
        self.setObjectName(title)
        self.setToolTip('Drag & Drop Scripts and Tools')
        self.setIconSize(QSize(16, 16))

        # create connections
        self.actionTriggered.connect(self.runAction)

    def clear(self):
        for act in self.findChildren(ToolbarAction):
            self.removeAction(act)
            act.setParent(None)
            act.deleteLater()

    def dragEnterEvent(self, event):
        """ filter drag events for specific items, treegrunt tools or script files """
        data = event.mimeData()

        # accept tool item drag/drop events
        if str(data.text()).startswith('Tool'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """ handle the drop event for this item """
        data = event.mimeData()
        text = str(data.text())

        # add a tool item
        if text.startswith('Tool'):
            toolId = '::'.join(text.split('::')[1:])
            self.addAction(ToolbarAction(self, toolId))

    def fromXml(self, xml):
        """ loads a toolbar from an xml element """
        self.clear()

        bar = xml.findChild('toolbar')
        if not bar:
            return False

        for actionxml in bar.children():
            self.addAction(ToolbarAction.fromXml(self, actionxml))

    def mousePressEvent(self, event):
        """ overload the mouse press event to handle custom context menus clicked on toolbuttons """
        # on a right click, show the menu
        if event.button() == Qt.RightButton:
            widget = self.childAt(event.x(), event.y())

            # show menus for the toolbars
            if widget and isinstance(widget.defaultAction(), ToolbarAction):
                self.setContextMenuPolicy(Qt.CustomContextMenu)
                action = widget.defaultAction()

                menu = QMenu(self)
                act = menu.addAction('Run %s' % action.text())
                act.setIcon(QIcon(blurdev.resourcePath('img/ide/run.png')))
                act.triggered.connect(action.exec_)

                act = menu.addAction('Remove %s' % action.text())
                act.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))
                act.triggered.connect(action.remove)

                if not isinstance(self.parent(), ToolsToolBarDialog):
                    menu.addSeparator()
                    act = menu.addAction('Close')
                    act.setIcon(QIcon(blurdev.resourcePath('img/cancel.png')))
                    act.triggered.connect(self.close)

                menu.exec_(QCursor.pos())

                event.accept()
            else:
                self.setContextMenuPolicy(Qt.DefaultContextMenu)
                event.ignore()
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)
            event.ignore()

    def runAction(self, action):
        """ runs the tool or script action associated with the inputed action """
        action.exec_()

    def toXml(self, xml):
        """ saves this toolbar information to an xml element """
        # Remove the old data
        actionsxml = xml.findChild('toolbar')
        if actionsxml:
            actionsxml.remove()
        # store tool bar info
        actionsxml = xml.addNode('toolbar')
        for action in self.actions():
            action.toXml(actionsxml)

    def shutdown(self):
        """
        If this item is the class instance properly close it and remove it from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == ToolsToolBar._instance:
            ToolsToolBar._instance = None
            self.setAttribute(Qt.WA_DeleteOnClose, True)
        try:
            self.close()
        except RuntimeError:
            pass

    @classmethod
    def instance(cls, parent=None):
        if not cls._instance:
            inst = cls(parent, 'BlurBar')
            inst.setAttribute(Qt.WA_DeleteOnClose, False)
            cls._instance = inst
        return cls._instance

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolsToolBarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False


class ToolsToolBarDialog(Dialog):
    _instance = None

    def __init__(self, parent, title):
        Dialog.__init__(self, parent)
        self.aboutToClearPathsEnabled = False
        self.setWindowTitle(title)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._toolbar = ToolsToolBar(self, title)
        layout.addWidget(self._toolbar)
        self.setLayout(layout)
        self.setFixedHeight(30)
        self.setWindowFlags(Qt.Tool)

    def fromXml(self, xml):
        child = xml.findChild('toolbardialog')
        if not child:
            return False

        # restore the geometry
        rect = child.restoreProperty('geom')
        if rect and rect.isValid() and not rect.isNull() and not rect.isEmpty():
            self.setGeometry(rect)

        # restore the visibility
        if child.attribute('visible') == 'True':
            self.show()
        else:
            self.hide()

        # restore the actions
        self._toolbar.fromXml(child)

    def toXml(self, xml):
        child = xml.addNode('toolbardialog')
        child.setAttribute('visible', self.isVisible())
        child.recordProperty('geom', self.geometry())
        self._toolbar.toXml(child)

    @staticmethod
    def instance(parent=None):
        if not ToolsToolBarDialog._instance:
            inst = ToolsToolBarDialog(parent, 'Blur Tools')
            inst.setAttribute(Qt.WA_DeleteOnClose, False)
            ToolsToolBarDialog._instance = inst
        return ToolsToolBarDialog._instance

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolsToolBarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False
