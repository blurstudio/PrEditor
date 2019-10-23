import os
import webbrowser
from Qt.QtCore import Qt, QSize
from Qt.QtGui import QCursor, QIcon, QPixmap
from Qt.QtWidgets import QAction, QMenu
import blurdev
from blurdev.gui.toolbars.blurdevtoolbar import BlurdevToolbar
from blurdev.gui import IconFactory
from blurdev.tools.tool import Tool


class ToolbarAction(QAction):
    def __init__(self, parent, tool):
        self._tool = tool
        self._toolID = tool.objectName()
        if isinstance(tool, str):
            self._tool = blurdev.findTool(self._toolID)

        if not isinstance(self._tool, Tool) or self._tool.isNull():
            msg = 'Could not resolve to a valid tool for {}'
            raise ValueError(msg.format(tool))

        self._toolWikiName = tool.displayName().replace(' ', '_')
        self._toolDsiplayName = tool.displayName()

        super(ToolbarAction, self).__init__(parent)
        self.setIcon(QIcon(QPixmap(tool.image())))
        self.setText(tool.displayName())
        self.setToolTip(tool.toolTip(info=True))

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


class ToolsToolbar(BlurdevToolbar):
    """ Baseclass for creating a toolbar for treegrunt tools.

    In most cases when subclassing you only need to implement the ``_name``
    property and the ``populate()`` function.

    The ``_name`` property gives the toolbar the name that users will see
    and is used as the unique id to find the toolbar in the functions
    ``blurdev.core.toolbar([name])`` and ``blurdev.core.findToolbar([name])``
    
    Attributes:
        _name (str): The unique id and display name for the toolbar. This is
            used as the display name in blur menus and the Qt interface.
            It's name must be unique among all toolbars.
        _affect_favorites (bool): When addAction or removeAction is called
            add or remove the tool from the users favorites.
        
    """

    _name = 'Treegrunt Toolbar'
    _affect_favorites = False

    def __init__(self, parent=None):
        super(ToolsToolbar, self).__init__(parent)
        self._iconFactory = IconFactory().customize(icon_class='StyledIcon')
        self.setAcceptDrops(True)
        self.setIconSize(QSize(16, 16))
        self.setToolTip('Drag and drop Treegrunt tools.')

        # Create connections.
        self.actionTriggered.connect(self.runAction)
        blurdev.core.environmentActivated.connect(self.refresh)
        blurdev.core.selectedToolTypesChanged.connect(self.updateToolVisibility)
        self.populate()
        self.updateToolVisibility()

    def addAction(self, action):
        super(ToolsToolbar, self).addAction(action)
        if self._affect_favorites and isinstance(action, ToolbarAction):
            action._tool.setFavorite(True)
        return action

    def addTool(self, tool):
        if isinstance(tool, basestring):
            tool = blurdev.findTool(tool)
        if isinstance(tool, Tool) and not tool.isNull():
            action = ToolbarAction(self, tool)
            return self.addAction(action)
        raise ValueError('Argument "tool" should be a valid tool')

    def dragEnterEvent(self, event):
        """ filter drag events for specific items, treegrunt tools or script files """
        data = event.mimeData()

        # accept tool item drag/drop events
        if data.text().startswith('Tool'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """ Handle the drop event for this item. """
        data = event.mimeData()
        text = data.text()

        # Add a tool item.
        if text.startswith('Tool::'):
            toolID = text[6:]
            toolIDs = self.toolIDs()
            if toolID not in toolIDs:
                tool = blurdev.findTool(toolID)
                if not tool.isNull():
                    action = ToolbarAction(self, tool)
                    self.addAction(action)

    def mousePressEvent(self, event):
        """ Overload the mouse press event to handle custom context menus
        clicked on toolbuttons.
        """
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
                act.setIcon(self._iconFactory.getIcon('google', name='school'))
                act.triggered.connect(action.documentation)

                act = menu.addAction('Explore...')
                act.setIcon(self._iconFactory.getIcon('google', name='folder'))
                act.triggered.connect(action.explore)

                menu.addSeparator()

                act = menu.addAction('Remove')
                act.setIcon(self._iconFactory.getIcon('google', name='delete'))
                act.triggered.connect(action.remove)

                menu.addSeparator()
                event.accept()

            act = menu.addAction('Reload')
            act.setIcon(self._iconFactory.getIcon('google', name='refresh'))
            act.triggered.connect(self.refresh)

            menu.addSeparator()
            act = menu.addAction('Close')
            act.setIcon(self._iconFactory.getIcon('google', name='close'))
            act.triggered.connect(self.close)

            menu.popup(position)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)
            event.ignore()

    def populate(self):
        """ This function should be sub-classed to populate the toolbar.

        This function does not need to hide tools based on toolTypes, that
        is taken care of by updateToolVisibility.
        """
        return False

    def recordSettings(self, save=True):
        """ records settings to be used for another session
        """
        pref = super(ToolsToolbar, self).recordSettings(save=False)
        tools = []
        for tool in self.tools():
            tools.append(tool.objectName())
        pref.recordProperty('tools', tools)
        if save:
            pref.save()
        return pref

    def refresh(self):
        self.clear()
        self.populate()
        self.updateToolVisibility()
        return True

    def removeAction(self, action):
        super(ToolsToolbar, self).removeAction(action)
        action.setParent(None)
        if self._affect_favorites and isinstance(action, ToolbarAction):
            action._tool.setFavorite(False)
        action.deleteLater()

    def runAction(self, action):
        """ runs the tool or script action associated with the inputted action """
        action.exec_()

    def toolIDs(self):
        """ Returns a list of the tool ids used to find and launch the tools.
        """
        toolIDs = []
        for tool in self.tools():
            toolIDs.append(tool.objectName())
        return toolIDs

    def tools(self):
        """ Returns the tools shown by the toolbar.
        """
        tools = []
        for action in self.actions():
            if isinstance(action, ToolbarAction):
                tools.append(action.tool())
        return tools

    def updateToolVisibility(self):
        """ Hides tool buttons that should not be visible based on user settings.

        This hides the action but does not remove it. self.tools() will still return all
        of the tools populate added to the toolbar.
        """
        for action in self.actions():
            if hasattr(action, 'tool'):
                action.setVisible(action.tool().isVisible())


class FavoritesToolbar(ToolsToolbar):
    """ Creates a toolbar that contains favorite Treegrunt tools.
    """

    _name = 'Favorites'
    _affect_favorites = True

    def populate(self):
        for tool in self.favoriteTools():
            if self.objectName() != tool.objectName():
                self.addTool(tool)

    def favoriteTools(self):
        index = blurdev.activeEnvironment().index()
        return sorted(index.favoriteTools(), key=lambda i: i.displayName())


class UserToolbar(ToolsToolbar):
    _name = 'User'

    def populate(self):
        pref = self.preferences()
        for tool in pref.restoreProperty('tools', []):
            self.addTool(tool)