import os
import webbrowser

from PyQt4.QtGui import QIcon, QAction, QToolBar, QMenu, QCursor, QHBoxLayout
from PyQt4.QtCore import QSize, Qt, QRect

import blurdev
from ..gui import Dialog


class LovebarAction(QAction):
    def __init__(self, parent, tool):
        QAction.__init__(self, parent)
        self._tool = tool
        self._toolWikiName = tool.displayName().replace(' ', '_')
        self._toolDsiplayName = tool.displayName()
        self._toolID = tool.objectName()
        iconPath = tool.icon()
        if not os.path.exists(iconPath):
            iconPath = blurdev.resourcePath('img/blank.png')
        self.setIcon(QIcon(iconPath))
        self.setText(tool.displayName())
        self.setToolTip(tool.toolTip())

    def exec_(self):
        blurdev.runTool(self._toolID)

    def remove(self):
        self.parent().removeAction(self)

    def documentation(self):
        url_template = os.environ.get('BDEV_USER_GUIDE_URL')
        if url_template:
            webbrowser.open(
                url_template % str(self._tool.displayName().replace(' ', '_'))
            )

    def explore(self):
        os.startfile(self._tool._path)


class ToolsLoveBar(QToolBar):
    """ Creates a toolbar that contains favorite Treegrunt tools.
    """

    def __init__(self, parent, title):
        QToolBar.__init__(self, parent)
        self._actions = []
        self.setWindowTitle(title)
        self.setAcceptDrops(True)
        self.setObjectName(title)
        self.setToolTip('Drag & Drop Scripts and Tools')
        self.setIconSize(QSize(22, 22))

        # Create connections.
        self.actionTriggered.connect(self.runAction)
        blurdev.core.environmentActivated.connect(self.refresh)
        self.populate()

    def populate(self):
        for favorite in self.favoriteTools():
            if not 'Lovebar' in favorite.displayName():
                action = LovebarAction(self, favorite)
                self.addAction(action, False)

    def favoriteTools(self):
        index = blurdev.activeEnvironment().index()
        return sorted(index.favoriteTools(), key=lambda i: i.displayName())

    def runAction(self, action):
        """ Runs the tool or script action associated with the input action. """
        action.exec_()

    def clear(self):
        for action in self.findChildren(LovebarAction):
            self.removeAction(action, False)

    def addAction(self, action, setFavorite=True):
        super(ToolsLoveBar, self).addAction(action)
        self._actions.append(action)
        if setFavorite:
            action._tool.setFavorite(True)

    def removeAction(self, action, setFavorite=True):
        super(ToolsLoveBar, self).removeAction(action)
        action.setParent(None)
        if setFavorite:
            action._tool.setFavorite(False)
        action.deleteLater()

    def toolIDs(self):
        toolIDs = []
        for action in self._actions:
            toolIDs.append(action._toolID)
        return toolIDs

    def dragEnterEvent(self, event):
        """ Filter drag events for specific items, treegrunt tools or script files. """
        data = event.mimeData()

        # Accept tool item drag/drop events.
        if str(data.text()).startswith('Tool'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """ Handle the drop event for this item. """
        data = event.mimeData()
        text = str(data.text())

        # Add a tool item.
        if text.startswith('Tool'):
            toolID = text.strip('Tool::')
            toolIDs = self.toolIDs()
            if toolID not in toolIDs:
                tool = blurdev.activeEnvironment().index().findTool(toolID)
                action = LovebarAction(self, tool)
                self.addAction(action)

    def refresh(self):
        self.clear()
        self.populate()
        return True

    def mousePressEvent(self, event):
        """ Overload the mouse press event to handle custom context menus clicked on toolbuttons. """
        # On a right click, show the menu.
        if event.button() == Qt.RightButton:
            widget = self.childAt(event.x(), event.y())

            # Show menus for the toolbars.
            menu = QMenu(self)
            if widget and isinstance(widget.defaultAction(), LovebarAction):
                self.setContextMenuPolicy(Qt.CustomContextMenu)

                action = widget.defaultAction()

                act = menu.addAction('Documentation')
                act.setIcon(QIcon(blurdev.resourcePath('img/doc.png')))
                act.triggered.connect(action.documentation)

                act = menu.addAction('Explore')
                act.setIcon(QIcon(blurdev.resourcePath('img/explore.png')))
                act.triggered.connect(action.explore)

                menu.addSeparator()

                act = menu.addAction('Remove')
                act.setIcon(QIcon(blurdev.resourcePath('img/trash.png')))
                act.triggered.connect(action.remove)

                menu.addSeparator()

                event.accept()

            act = menu.addAction('Refesh')
            act.setIcon(QIcon(blurdev.resourcePath('img/refresh.png')))
            act.triggered.connect(self.refresh)
            menu.popup(QCursor.pos())
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)
            event.ignore()


class ToolsLoveBarDialog(Dialog):
    _instance = None

    def __init__(self, parent, title):
        Dialog.__init__(self, parent)
        self.aboutToClearPathsEnabled = False
        self.setWindowTitle(title)
        # Setting up the dialog.
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._toolbar = ToolsLoveBar(self, title)
        layout.addWidget(self._toolbar)
        self.setLayout(layout)
        self.setFixedHeight(36)
        self.setWindowFlags(Qt.Tool)
        # restoring settings.
        self.restoreSettings()

    def closeEvent(self, event):
        """ overload the close event to handle saving of preferences before shutting down
        """
        self.recordSettings()
        Dialog.closeEvent(self, event)

    def recordSettings(self):
        """ records settings to be used for another session
        """
        pref = blurdev.prefs.find('tools/Lovebar')
        # Record the geometry.
        pref.recordProperty('geom', self.geometry())
        # Save the settings.
        pref.save()

    def restoreSettings(self):
        """ restores settings that were saved by a previous session
        """
        pref = blurdev.prefs.find('tools/Lovebar')

        # reload the geometry
        geom = pref.restoreProperty('geom', QRect())
        if geom and not geom.isNull():
            self.setGeometry(geom)

    @staticmethod
    def instance(parent=None):
        if not ToolsLoveBarDialog._instance:
            inst = ToolsLoveBarDialog(parent, 'Lovebar')
            inst.setAttribute(Qt.WA_DeleteOnClose, False)
            ToolsLoveBarDialog._instance = inst
        return ToolsLoveBarDialog._instance
