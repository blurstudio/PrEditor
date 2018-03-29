import os
import webbrowser

from Qt.QtGui import QCursor, QIcon, QPixmap
from Qt.QtWidgets import QAction, QHBoxLayout, QMenu, QToolBar
from Qt.QtCore import QRect, QSize, Qt

import blurdev
from ..gui import Dialog


class LovebarAction(QAction):
    def __init__(self, parent, tool):
        QAction.__init__(self, parent)
        self._tool = tool
        self._toolWikiName = tool.displayName().replace(' ', '_')
        self._toolDsiplayName = tool.displayName()
        self._toolID = tool.objectName()
        self.setIcon(QIcon(QPixmap(tool.image())))
        self.setText(tool.displayName())
        self.setToolTip(tool.toolTip())

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


class ToolsLoveBar(QToolBar):
    """ Creates a toolbar that contains favorite Treegrunt tools.
    """

    _instance = None

    def __init__(self, parent, title):
        QToolBar.__init__(self, parent)
        self._actions = []
        self.setWindowTitle(title)
        self.setAcceptDrops(True)
        self.setObjectName(title)
        self.setIconSize(QSize(16, 16))
        self.setToolTip('Drag & Drop Scripts and Tools')

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
        if data.text().startswith('Tool'):
            event.acceptProposedAction()

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
                action = LovebarAction(self, tool)
                self.addAction(action)

    def recordSettings(self):
        """ records settings to be used for another session
        """
        pref = blurdev.prefs.find('tools/Lovebar')
        pref.recordProperty('isVisible', self.isVisible())
        # Save the settings.
        pref.save()

    def restoreSettings(self):
        """ restores settings that were saved by a previous session
        """
        pass
        # NOTE: toolbar geometry, floating etc should be restored by the QMainWindow's restoreState
        # In maya this is accomplished in the blur_maya plugin when it calls
        # cmds.windowPref(restoreMainWindowState="startupMainWindowState")

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

            if not isinstance(self.parent(), ToolsLoveBarDialog):
                menu.addSeparator()
                act = menu.addAction('Close')
                act.setIcon(QIcon(blurdev.resourcePath('img/cancel.png')))
                act.triggered.connect(self.close)

            menu.popup(QCursor.pos())
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)
            event.ignore()

    def shutdown(self):
        """
        If this item is the class instance properly close it and remove it from memory so it can be recreated.
        """
        # allow the global instance to be cleared
        if self == ToolsLoveBar._instance:
            ToolsLoveBar._instance = None
            self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.recordSettings()
        try:
            self.close()
        except RuntimeError:
            pass

    @classmethod
    def instance(cls, parent=None):
        if not cls._instance:
            inst = cls(parent, 'Lovebar')
            inst.setAttribute(Qt.WA_DeleteOnClose, False)
            cls._instance = inst
        return cls._instance

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolsLoveBarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False


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
        self.setFixedHeight(28)
        self.setWindowFlags(Qt.Tool)
        # restoring settings.
        self.restoreSettings()

    def recordSettings(self):
        """ records settings to be used for another session
        """
        pref = blurdev.prefs.find('tools/Lovebar')
        # Record the geometry.
        pref.recordProperty('geom', self.geometry())
        pref.recordProperty('isVisible', self.isVisible())
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

    @classmethod
    def instanceShutdown(cls):
        """ Faster way to shutdown the instance of ToolsLoveBarDialog if it possibly was not used. Returns if shutdown was required.
            :return: Bool. Shutdown was requried
        """
        if cls._instance:
            cls._instance.shutdown()
            return True
        return False
