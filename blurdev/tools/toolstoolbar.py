##
# 	\namespace	blurdev.tools.toolstoolbar
#
# 	\remarks	Creates a toolbar that contains links to blurdev Tools
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		10/13/09
#

from PyQt4.QtGui import QAction
from PyQt4.QtGui import QToolBar


class ToolbarAction(QAction):
    def __init__(self, parent, toolId):

        QAction.__init__(self, parent)

        self._toolId = toolId

        import blurdev

        tool = blurdev.findTool(toolId)

        if tool:

            from PyQt4.QtGui import QIcon

            self.setIcon(QIcon(tool.icon()))

            self.setText(tool.displayName())

            self.setToolTip(tool.toolTip())

    def exec_(self):

        import blurdev

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


# -------------------------------------------------------------------------------------------------------------


class ToolsToolBar(QToolBar):
    """ QToolBar sub-class to contain actions for Tools """

    def __init__(self, parent, title):
        QToolBar.__init__(self, parent)

        self.setWindowTitle(title)
        self.setAcceptDrops(True)
        self.setToolTip('Drag & Drop Scripts and Tools')

        from PyQt4.QtCore import QSize

        self.setIconSize(QSize(16, 16))

        from PyQt4.QtCore import Qt

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
        from PyQt4.QtCore import Qt

        # on a right click, show the menu
        if event.button() == Qt.RightButton:
            widget = self.childAt(event.x(), event.y())

            # show menus for the toolbars
            if widget and isinstance(widget.defaultAction(), ToolbarAction):
                self.setContextMenuPolicy(Qt.CustomContextMenu)

                from PyQt4.QtGui import QMenu, QCursor

                action = widget.defaultAction()

                menu = QMenu(self)

                act = menu.addAction('Run %s' % action.text())

                act.triggered.connect(action.exec_)

                act = menu.addAction('Remove %s' % action.text())

                act.triggered.connect(action.remove)

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

        # store tool bar info

        actionsxml = xml.addNode('toolbar')

        for action in self.actions():

            action.toXml(actionsxml)


from blurdev.gui import Dialog


class ToolsToolBarDialog(Dialog):

    _instances = {}

    def __init__(self, parent, title):

        Dialog.__init__(self, parent)

        self.setWindowTitle(title)

        from PyQt4.QtGui import QHBoxLayout

        layout = QHBoxLayout()

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        self._toolbar = ToolsToolBar(self, title)

        layout.addWidget(self._toolbar)

        self.setLayout(layout)

        self.setFixedHeight(30)

        from PyQt4.QtCore import Qt

        self.setWindowFlags(Qt.Tool)

    def closeEvent(self, event):

        from blurdev import prefs

        pref = prefs.find('toolbars')

        self.recordToolbars(pref.root())

        pref.save()

        Dialog.closeEvent(self, event)

    @staticmethod
    def recordToolbars(xml):

        for name, inst in ToolsToolBarDialog._instances.items():

            child = xml.addNode('toolbardialog')

            child.setAttribute('title', name)

            child.setAttribute('visible', inst.isVisible())

            child.recordProperty('geom', inst.geometry())

            inst._toolbar.toXml(child)

    @staticmethod
    def restoreToolbars(xml):

        count = 0

        for child in xml.children():

            inst = ToolsToolBarDialog.instance(None, title=child.attribute('title'))

            inst.setVisible(child.attribute('visible') == 'True')

            geom = child.restoreProperty('geom')

            if geom and geom.isValid():

                inst.setGeometry(geom)

            inst._toolbar.fromXml(child)

            count += 1

        return count

    @staticmethod
    def instance(parent, title='Blur Tools'):

        inst = ToolsToolBarDialog._instances.get(title)

        if not inst:

            inst = ToolsToolBarDialog(parent, title)

            from PyQt4.QtCore import Qt

            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            ToolsToolBarDialog._instances[title] = inst

        return inst
