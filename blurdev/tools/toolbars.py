import os
import webbrowser

import blurdev

from Qt.QtGui import QCursor, QIcon, QPixmap
from Qt.QtWidgets import QAction, QHBoxLayout, QMenu, QToolBar
from Qt.QtCore import QRect, QSize, Qt

from blurdev.tools.tool import Tool

from .icons import iconFactory
from ..gui import Dialog


class ToolbarAction(QAction):
    def __init__(self, parent, tool):
        self._tool = tool
        self._toolID = tool.objectName()
        if isinstance(tool, str):
            self._tool = blurdev.findTool(self._toolID)

        if not isinstance(self._tool, Tool):
            raise ValueError('{} could not resolve to a valid tool')

        self._toolWikiName = tool.displayName().replace(' ', '_')
        self._toolDsiplayName = tool.displayName()

        QAction.__init__(self, parent)
        self.setIcon(QIcon(QPixmap(tool.image())))
        self.setText(tool.displayName())
        self.setToolTip(tool.toolTip())

    def tool(self):
        return self._tool

    def exec_(self):
        blurdev.runTool(self._toolID)

    def remove(self):
        self.parent().removeAction(self)

    def documentation(self):
        url_template = os.environ.get('BDEV_USER_GUIDE_URL')
        if url_template:
            webbrowser.open(url_template % self._tool.displayName().replace(' ', '_'))

    def explore(self):
        os.startfile(self._tool._path)


class Toolbar(QToolBar):
    _instance = None
    _instanceDialog = None
    _title = 'Toolbar'
    _affectFavorites = False

    def __init__(self, parent=None):
        super(Toolbar, self).__init__(parent)

        self.setWindowTitle(self._title)
        self.setAcceptDrops(True)
        components = self._title.lower().replace(' ', '_').split('_')
        self.setObjectName(components[0] + ''.join(x.title() for x in components[1:]))
        self.setToolTip('Drag and drop Treegrunt tools.')

        # Create connections.
        self.actionTriggered.connect(self.runAction)
        blurdev.core.environmentActivated.connect(self.refresh)
        self.populate()

    @classmethod
    def preferences(cls, coreName=''):
        name = cls._title.lower().replace(' ', '_')
        return blurdev.prefs.find('tools/{}'.format(name), coreName=coreName)

    @classmethod
    def title(cls):
        return cls._title

    @classmethod
    def dialog(cls, parent):
        instance = cls.instance()
        if not cls._instanceDialogs:
            cls._instanceDialog = ToolbarDialog(instance, parent=parent)
        return cls._instanceDialogs

    def setIconsSize(self, size):
        self.setIconSize(QSize(size, size))
        self.setFixedHeight(size)
        self.setMinimumHeight(size)

    def mousePressEvent(self, event):
        """ Overload the mouse press event to handle custom context menus clicked on toolbuttons. """
        # On a right click, show the menu.
        position = QCursor.pos()
        if event.button() == Qt.RightButton:
            widget = self.childAt(event.x(), event.y())

            # Show menus for the toolbars.
            menu = QMenu(self)
            menu.setMinimumHeight(32)

            if widget and isinstance(widget.defaultAction(), ToolbarAction):
                self.setContextMenuPolicy(Qt.CustomContextMenu)

                action = widget.defaultAction()

                act = menu.addAction('View User Guide...')
                act.setIcon(iconFactory.getIcon('user-guide'))
                act.triggered.connect(action.documentation)

                act = menu.addAction('Explore...')
                act.setIcon(iconFactory.getIcon('explore'))
                act.triggered.connect(action.explore)

                menu.addSeparator()

                act = menu.addAction('Remove')
                act.setIcon(iconFactory.getIcon('remove'))
                act.triggered.connect(action.remove)

                menu.addSeparator()
                event.accept()

            mnu = menu.addMenu('View')
            mnu.setIcon(iconFactory.getIcon('view'))
            act = mnu.addAction('Small Icons')
            act.triggered.connect(lambda: self.setIconsSize(16))
            act.setCheckable(True)
            act = mnu.addAction('Large Icons')
            act.triggered.connect(lambda: self.setIconsSize(32))
            act.setCheckable(True)

            menu.addSeparator()

            act = menu.addAction('Reload')
            act.setIcon(iconFactory.getIcon('reload'))
            act.triggered.connect(self.refresh)

            if not isinstance(self.parent(), ToolbarDialog):
                menu.addSeparator()
                act = menu.addAction('Close')
                act.setIcon(iconFactory.getIcon('close'))
                act.triggered.connect(self.close)

            menu.popup(position)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)
            event.ignore()

    def populate(self):
        return False

    def runAction(self, action):
        """ runs the tool or script action associated with the inputed action """
        action.exec_()

    def clear(self):
        for action in self.findChildren(ToolbarAction):
            super(Toolbar, self).removeAction(action)
            action.setParent(None)

    def toolIDs(self):
        toolIDs = []
        for action in self.actions():
            toolIDs.append(action._toolID)
        return toolIDs

    def refresh(self):
        self.clear()
        self.populate()
        return True

    def shutdown(self):
        """
        If this item is the class instance properly close it and remove it from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == self._instance:
            self._instance = None
            if self == self._instanceDialog:
                self._instanceDialog = None
                self._instanceDialog.setAttribute(Qt.WA_DeleteOnClose, True)
                self._instanceDialog.close()
            else:
                self.setAttribute(Qt.WA_DeleteOnClose, True)
                self.close()

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolbarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        instance = cls._instance
        if instance:
            instance.shutdown()
            return True
        return False

    @classmethod
    def instance(cls, parent=None):
        if not cls._instance:
            instance = cls(parent=parent)
            instance.setAttribute(Qt.WA_DeleteOnClose, False)
            cls._instance = instance
        return cls._instance

    def addTool(self, tool):
        if isinstance(tool, basestring):
            index = blurdev.activeEnvironment().index()
            tool = index.findTool(tool)
        if isinstance(tool, Tool):
            action = ToolbarAction(self, tool)
            return self.addAction(action)
        raise ValueError('Argument "tool" should be a valid tool')

    def tools(self):
        tools = []
        for action in self.actions():
            tools.append(action.tool())
        return tools

    def addAction(self, action):
        super(Toolbar, self).addAction(action)
        if self._affectFavorites:
            action._tool.setFavorite(True)
        return action

    def removeAction(self, action):
        super(Toolbar, self).removeAction(action)
        action.setParent(None)
        if self._affectFavorites:
            action._tool.setFavorite(False)
        action.deleteLater()

    def dragEnterEvent(self, event):
        """ filter drag events for specific items, treegrunt tools or script files """
        data = event.mimeData()

        # accept tool item drag/drop events
        if data.text().startswith('Tool'):
            event.acceptProposedAction()

    def recordSettings(self):
        """ records settings to be used for another session
        """
        pref = self.preferences()
        pref.recordProperty('isVisible', self.isVisible())
        tools = []
        for tool in self._toolbar.tools():
            tools.append(tool.objectName())
        pref.recordProperty('tools', tools)
        pref.recordProperty('size', self.fixedHeight())
        pref.save()

    def dropEvent(self, event):
        """ Handle the drop event for this item. """
        data = event.mimeData()
        text = data.text()

        # Add a tool item.
        if text.startswith('Tool'):
            toolID = text.strip('Tool::')
            toolIDs = self.toolIDs()
            if toolID not in toolIDs:
                tool = blurdev.activeEnvironment().index().findTool(toolID)
                action = ToolbarAction(self, tool)
                self.addAction(action)


class UserToolbar(Toolbar):
    _title = 'User Toolbar'

    def populate(self):
        pref = blurdev.prefs.find('tools/{}'.format(self.objectName()))
        for tool in pref.restoreProperty('tools', []):
            self._toolbar.addTool(tool)


class FavoritesToolbar(Toolbar):
    """ Creates a toolbar that contains favorite Treegrunt tools.
    """

    _title = 'Favorites Toolbar'
    _affectFavorites = True

    def populate(self):
        for tool in self.favoriteTools():
            if self.objectName() != tool.objectName():
                self.addTool(tool)

    def favoriteTools(self):
        index = blurdev.activeEnvironment().index()
        return sorted(index.favoriteTools(), key=lambda i: i.displayName())


class DepartmentToolbar(Toolbar):
    """ Creates a toolbar that contains tools for a detected department.
    """

    _title = 'Department Toolbar'

    def populate(self):
        from trax.api.data import Employee

        index = blurdev.activeEnvironment().index()
        # TODO: Trax should not be a dependency here.
        employee = Employee.currentUser()
        if isinstance(employee, Employee):
            department = employee.primaryDepartment().name()
            for tool in index.findCategory(department):
                self.addTool(tool)


class ToolbarDialog(Dialog):
    def __init__(self, toolbar, parent=None):
        Dialog.__init__(self, parent)
        self.aboutToClearPathsEnabled = False
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._toolbar = toolbar
        self._title = toolbar.title()
        self.setWindowTitle(toolbar.title())
        layout.addWidget(toolbar)
        self.setLayout(layout)
        self.setFixedHeight(32)
        self.setWindowFlags(Qt.Tool)
        self.restoreSettings()

    def recordSettings(self):
        """ records settings to be used for another session
        """
        pref = self._toolbar.preferences()
        pref.recordProperty('geometry', self.geometry())
        pref.recordProperty('isVisible', self.isVisible())
        pref.save()

    def restoreSettings(self):
        """ restores settings that were saved by a previous session
        """
        pref = self._toolbar.preferences()
        geometry = pref.restoreProperty('geometry', QRect())
        if geometry and not geometry.isNull():
            self.setGeometry(geometry)
        self.setIconsSize(pref.restoreProperty('icons_size', 32))

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolbarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        cls._toolbar.instanceShutdown()
