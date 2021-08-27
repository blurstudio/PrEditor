from __future__ import absolute_import
import os
import webbrowser
from Qt.QtCore import Qt
from Qt.QtGui import QCursor, QIcon, QPixmap
from Qt.QtWidgets import QAction, QMenu, QWidgetAction
import blurdev
from blurdev.gui.toolbars.blurdevtoolbar import BlurdevToolbar
from blurdev.gui import IconFactory
from blurdev.tools.tool import Tool
import six


class ToolbarAction(QAction):
    def __init__(self, parent, tool):
        if isinstance(tool, six.string_types):
            self._tool = blurdev.findTool(tool)
            self._toolID = tool
        else:
            self._tool = tool
            self._toolID = tool.objectName()

        self._toolWikiName = self._tool.displayName().replace(' ', '_')
        self._toolDsiplayName = self._tool.displayName()

        super(ToolbarAction, self).__init__(parent)
        self.setIcon(QIcon(QPixmap(self._tool.image())))
        self.setText(self._tool.displayName())
        self.setToolTip(self._tool.toolTip(info=True))

        if not isinstance(self._tool, Tool):
            msg = 'Could not resolve to a valid tool for {}'
            raise ValueError(msg.format(self._tool))
        elif self._tool.isNull():
            # Hide tools that are not valid for the active treegrunt environment.
            # This tool may be used in other treegrunt environments
            self.setVisible(False)
            self._tool.setObjectName(self._toolID)

    def tool(self):
        return self._tool

    def toolID(self):
        return self._toolID

    def exec_(self):
        blurdev.runTool(self._toolID)

    def documentation(self):
        url_template = os.environ.get('BDEV_USER_GUIDE_URL')
        if url_template:
            webbrowser.open(url_template % self._tool.displayName().replace(' ', '_'))

    def explore(self):
        os.startfile(self._tool._path)


class ToolsToolbar(BlurdevToolbar):
    """Baseclass for creating a toolbar for treegrunt tools.

    In most cases when subclassing you only need to implement the ``_name``
    property and the ``populate()`` function.

    The ``_name`` property gives the toolbar the name that users will see
    and is used as the unique id to find the toolbar in the functions
    ``blurdev.core.toolbar([name])`` and ``blurdev.core.findToolbar([name])``

    Attributes:
        _name (str): The unique id and display name for the toolbar. This is
            used as the display name in blur s and the Qt interface.
            It's name must be unique among all toolbars.
    """

    _name = 'Treegrunt Toolbar'

    def __init__(self, parent=None):
        super(ToolsToolbar, self).__init__(parent)
        self._editable = True
        self._iconFactory = IconFactory().customize(icon_class='StyledIcon')
        self.setAcceptDrops(True)
        self.setToolTip('Drag and drop Treegrunt tools.')
        self._protected_actions = []

        # Create connections.
        self.actionTriggered.connect(self.runAction)
        blurdev.core.environmentActivated.connect(self.refresh)
        blurdev.core.selectedToolTypesChanged.connect(self.updateToolVisibility)
        self.populate()
        self.updateToolVisibility()

    def addTool(self, tool):
        action = ToolbarAction(self, tool)
        return self.addAction(action)

    def dragEnterEvent(self, event):
        """filter drag events for specific items, treegrunt tools or script files"""
        data = event.mimeData()

        # accept tool item drag/drop events
        if data.text().startswith('Tool'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle the drop event for this item."""
        data = event.mimeData()
        text = data.text()

        # Add a tool item.
        if text.startswith('Tool::'):
            toolID = text[6:]
            toolIDs = self.toolIDs()
            if toolID not in toolIDs:
                tool = blurdev.findTool(toolID)
                # Only allow drag drop of valid tool ids
                if not tool.isNull():
                    self.addTool(tool)

    def mousePressEvent(self, event):
        """Overload the mouse press event to handle custom context menus
        clicked on toolbuttons.
        """
        # On a right click, show the menu.
        position = QCursor.pos()
        if event.button() == Qt.RightButton:
            # Show menus for the toolbars.
            menu = QMenu(self)

            # Create a simple header for the menu to easily identify the toolbar
            act = menu.addAction(self._name)
            # Make the action visually distinct, also it doesn't do anything.
            act.setEnabled(False)
            act.setObjectName('uiTitleACT')
            sep = menu.addSeparator()
            sep.setObjectName('uiTitleSEP')

            action = self.actionAt(event.x(), event.y())
            if (
                action
                and action not in self._protected_actions
                and not isinstance(action, QWidgetAction)
            ):
                if isinstance(action, ToolbarAction):

                    # Toolbar separators don't have defaultAction.
                    self.setContextMenuPolicy(Qt.CustomContextMenu)

                    act = menu.addAction('View User Guide...')
                    act.setIcon(self._iconFactory.getIcon('google', name='school'))
                    act.triggered.connect(action.documentation)

                    act = menu.addAction('Explore...')
                    act.setIcon(self._iconFactory.getIcon('google', name='folder'))
                    act.triggered.connect(action.explore)

                    menu.addSeparator()

                if self._editable:

                    act = menu.addAction('Move Back')
                    act.setIcon(
                        self._iconFactory.getIcon('google', name='chevron_left')
                    )
                    act.triggered.connect(lambda: self.moveActionBack(action))

                    act = menu.addAction('Move Forward')
                    act.setIcon(
                        self._iconFactory.getIcon('google', name='chevron_right')
                    )
                    act.triggered.connect(lambda: self.moveActionForward(action))

                    menu.addSeparator()
                    act = menu.addAction('Insert Separator')
                    act.setIcon(self._iconFactory.getIcon('google', name='space_bar'))
                    act.triggered.connect(lambda: self.insertSeparator(action))

                    act = menu.addAction('Remove')
                    act.setIcon(self._iconFactory.getIcon('google', name='delete'))
                    act.triggered.connect(lambda: self.removeAction(action))

                    menu.addSeparator()

            event.accept()

            if self._editable:
                act = menu.addAction('Save')
                act.setIcon(self._iconFactory.getIcon('google', name='save'))
                act.triggered.connect(lambda: self.recordSettings(save=True, gui=True))

                menu.addSeparator()

            viewMenu = menu.addMenu('View')
            viewMenu.setIcon(self._iconFactory.getIcon('view'))
            act = viewMenu.addAction('Small Icons')
            act.triggered.connect(lambda: self.setIconsSize(16))
            act.setCheckable(True)
            act.setChecked(self._iconsSize == 16)
            act = viewMenu.addAction('Medium Icons')
            act.triggered.connect(lambda: self.setIconsSize(24))
            act.setCheckable(True)
            act.setChecked(self._iconsSize == 24)
            act = viewMenu.addAction('Large Icons')
            act.triggered.connect(lambda: self.setIconsSize(32))
            act.setCheckable(True)
            act.setChecked(self._iconsSize == 32)

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

    def actionPositionIndex(self, action):
        actions = self.actions()
        for i in range(len(actions)):
            act = actions[i]
            if action == act:
                return i

    def previousVisibleAction(self, action):
        index = max(0, self.actionPositionIndex(action) - 1)
        previous = self.actions()[index]
        if previous.isVisible():
            return previous
        return self.previousVisibleAction(previous)

    def nextVisibleAction(self, action):
        actions = self.actions()
        index = min(len(actions) - 1, self.actionPositionIndex(action) + 1)
        nxt = actions[index]
        if nxt.isVisible():
            return nxt
        return self.nextVisibleAction(nxt)

    def moveActionBack(self, action, before=None):
        before = before or self.previousVisibleAction(action)
        if isinstance(before, QWidgetAction) or before in self._protected_actions:
            return False
        self.insertAction(before, action)

    def moveActionForward(self, action):
        before = self.nextVisibleAction(action)
        self.addAction(action)
        self.insertAction(self.nextVisibleAction(before), action)

    def populate(self):
        """This function should be sub-classed to populate the toolbar.

        This function does not need to hide tools based on toolTypes, that
        is taken care of by updateToolVisibility.
        """
        return False

    def recordSettings(self, save=True, gui=True):
        """Records settings to be used for another session.

        Args:
            save (bool, optional): Save the settings. This is mostly used by sub-classes
                that need to add extra properties to the preferences.
            gui (bool, optional): Used by some cores to prevent saving some prefs.
                See :py:meth:`blurdev.cores.nukecore.NukeCore.eventFilter`.

        Returns:
            blurdev.prefs.Pref: The preference object. If save is False, you will
                need to call save on it.
        """
        pref = super(ToolsToolbar, self).recordSettings(save=False, gui=gui)
        pref.recordProperty('tools', self.toolIDs())
        if save:
            pref.save()
        return pref

    def collapseSeparators(self):
        """Will only keep one separator visible when more than one are juxtaposed."""
        previousAction = None
        for action in self.actions():
            if previousAction and action.isSeparator() and previousAction.isSeparator():
                action.setVisible(False)

    def refresh(self):
        self.clear()
        self.populate()
        self.updateToolVisibility()
        return True

    def removeAction(self, action):
        super(ToolsToolbar, self).removeAction(action)
        action.setParent(None)
        action.deleteLater()

    def runAction(self, action):
        """runs the tool or script action associated with the inputted action"""
        action.exec_()

    def toolIDs(self):
        """Returns a list of the tool ids used to find and launch the tools."""
        toolIDs = []
        for tool in self.tools():
            if tool:
                toolIDs.append(tool.objectName())
            else:
                toolIDs.append('')
        return toolIDs

    def tools(self):
        """Returns the tools shown by the toolbar."""
        tools = []
        for action in self.actions():
            if action in self._protected_actions:
                continue
            elif isinstance(action, ToolbarAction):
                tools.append(action.tool())
            elif action.isSeparator():
                tools.append(None)
        return tools

    def updateToolVisibility(self):
        """Hides tool buttons that should not be visible based on user settings.

        This hides the action but does not remove it. self.tools() will still return all
        of the tools populate added to the toolbar.
        """
        for action in self.actions():
            if hasattr(action, 'tool'):
                action.setVisible(action.tool().isVisible())


class FavoritesToolbar(ToolsToolbar):
    """Creates a toolbar that contains favorite Treegrunt tools."""

    _name = 'Favorites'

    def addAction(self, action):
        super(FavoritesToolbar, self).addAction(action)
        if isinstance(action, ToolbarAction):
            action._tool.setFavorite(True)
        return action

    def removeAction(self, action):
        if isinstance(action, ToolbarAction):
            action._tool.setFavorite(False)
        super(FavoritesToolbar, self).removeAction(action)

    def populate(self):
        pref = self.preferences()
        tools = pref.restoreProperty('tools', [])
        favorites = [t.objectName() for t in self.favoriteTools()]
        extras = set(favorites).difference(tools)
        for tool in tools + list(extras):
            if not tool:
                self.addSeparator()
            if tool in favorites:
                # Ignoring the favorite toolbar tool itself.
                # It could be a favorite tool, but we don't it in the toolbar.
                if tool != self.objectName():
                    self.addTool(tool)
        self.collapseSeparators()

    def favoriteTools(self):
        index = blurdev.activeEnvironment().index()
        return sorted(index.favoriteTools(), key=lambda i: i.displayName())


class UserToolbar(ToolsToolbar):
    _name = 'User'

    def populate(self):
        pref = self.preferences()
        for tool in pref.restoreProperty('tools', []):
            self.addTool(tool)
        self.collapseSeparators()
