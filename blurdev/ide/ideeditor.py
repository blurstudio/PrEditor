##
# 	\namespace	blurdev.ide.templatebuilder
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtCore import pyqtSignal
from blurdev.gui import Window
from ideproject import IdeProject


class IdeEditor(Window):
    documentTitleChanged = pyqtSignal()
    currentProjectChanged = pyqtSignal(IdeProject)

    _instance = None

    Command = {'.ui': ('c:/blur/common/designer.exe', '', 'c:/blur/common')}

    def __init__(self, parent=None):
        Window.__init__(self, parent)

        # load the ui
        import blurdev
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        from PyQt4.QtGui import QIcon

        self.setWindowIcon(QIcon(blurdev.relativePath(__file__, '/img/icon.png')))

        # create custom properties
        self._closing = False
        self._project = None
        self._searchText = ''
        self._searchFlags = 0
        self._searchDialog = None
        self.setAcceptDrops(True)

        from PyQt4.QtCore import QDir
        from ideproject import IdeProject

        QDir.setCurrent(IdeProject.DefaultPath)

        from finddialog import FindDialog

        self._searchDialog = FindDialog(self)

        # create the filesystem model for the explorer tree
        from PyQt4.QtGui import QFileSystemModel

        # create the system model
        model = QFileSystemModel()
        model.setRootPath('')
        self.uiExplorerTREE.setModel(model)
        for i in range(1, 4):
            self.uiExplorerTREE.setColumnHidden(i, True)

        self.restoreSettings()

        # create connections
        self.uiProjectTREE.clicked.connect(self.updatePath)
        self.uiProjectTREE.doubleClicked.connect(self.editItem)
        self.uiProjectTREE.customContextMenuRequested.connect(self.showProjectMenu)
        self.uiOpenTREE.itemClicked.connect(self.editItem)
        self.uiExplorerTREE.doubleClicked.connect(self.editItem)
        self.uiExplorerTREE.clicked.connect(self.updatePath)
        self.uiWindowsAREA.subWindowActivated.connect(self.updateTitle)
        self.uiWindowsAREA.subWindowActivated.connect(self.checkOpen)
        self.documentTitleChanged.connect(self.refreshOpen)
        self.uiCommandLineDDL.lineEdit().returnPressed.connect(self.runCommand)

        # connect file menu
        from blurdev.ide.idetemplatebrowser import IdeTemplateBrowser

        self.uiNewACT.triggered.connect(self.documentNew)
        self.uiNewFromTemplateACT.triggered.connect(
            IdeTemplateBrowser.createFromTemplate
        )
        self.uiOpenACT.triggered.connect(self.documentOpen)
        self.uiCloseACT.triggered.connect(self.documentClose)
        self.uiCloseAllACT.triggered.connect(self.documentCloseAll)
        self.uiCloseAllExceptACT.triggered.connect(self.documentCloseAllExcept)
        self.uiSaveACT.triggered.connect(self.documentSave)
        self.uiSaveAsACT.triggered.connect(self.documentSaveAs)
        self.uiSaveAllACT.triggered.connect(self.documentSaveAll)
        self.uiExitACT.triggered.connect(self.close)

        # project menus
        self.uiNewProjectACT.triggered.connect(self.projectNew)
        self.uiOpenProjectACT.triggered.connect(self.projectOpen)
        self.uiOpenFavoritesACT.triggered.connect(self.projectFavorites)
        self.uiEditProjectACT.triggered.connect(self.projectEdit)
        self.uiCloseProjectACT.triggered.connect(self.projectClose)

        # connect edit menu
        self.uiUndoACT.triggered.connect(self.documentUndo)
        self.uiRedoACT.triggered.connect(self.documentRedo)
        self.uiCutACT.triggered.connect(self.documentCut)
        self.uiCopyACT.triggered.connect(self.documentCopy)
        self.uiPasteACT.triggered.connect(self.documentPaste)
        self.uiSelectAllACT.triggered.connect(self.documentSelectAll)

        # connect search menu
        self.uiFindNextACT.triggered.connect(self.documentFindNext)
        self.uiFindPrevACT.triggered.connect(self.documentFindPrev)
        self.uiGotoACT.triggered.connect(self.documentGoTo)
        self.uiFindACT.triggered.connect(self._searchDialog.show)
        self.uiAddRemoveMarkerACT.triggered.connect(self.documentMarkerToggle)
        self.uiNextMarkerACT.triggered.connect(self.documentMarkerNext)
        self.uiClearMarkersACT.triggered.connect(self.documentMarkerClear)

        # connect run menu
        self.uiRunScriptACT.triggered.connect(self.documentExec)
        self.uiRunStandaloneACT.triggered.connect(self.documentExecStandalone)

        # connect view menu
        self.uiDisplayWindowsACT.triggered.connect(self.displayWindows)
        self.uiDisplayTabsACT.triggered.connect(self.displayTabs)
        self.uiDisplayTileACT.triggered.connect(self.uiWindowsAREA.tileSubWindows)
        self.uiDisplayCascadeACT.triggered.connect(self.uiWindowsAREA.cascadeSubWindows)

        # connect tools menu
        self.uiAssistantACT.triggered.connect(self.showAssistant)
        self.uiDesignerACT.triggered.connect(self.showDesigner)
        self.uiTreegruntACT.triggered.connect(blurdev.core.showTreegrunt)
        self.uiShowLoggerACT.triggered.connect(blurdev.core.showLogger)

        # connect advanced menu
        self.uiConfigurationACT.triggered.connect(self.showConfig)

        # connect help menu
        self.uiHelpAssistantACT.triggered.connect(self.showAssistant)
        self.uiSdkBrowserACT.triggered.connect(self.showSdkBrowser)

    def checkOpen(self):
        # determine if there have been any changes
        if self.uiOpenTREE.topLevelItemCount() != len(
            self.uiWindowsAREA.subWindowList()
        ):
            self.refreshOpen()

    def currentDocument(self):
        window = self.uiWindowsAREA.activeSubWindow()
        if window:
            return window.widget()
        return None

    def currentProject(self):
        return self._project

    def currentPath(self):
        path = ''
        import os.path

        if not self.uiProjectTREE.model():
            return ''

        # load from the project
        if self.uiBrowserTAB.currentIndex() == 0:
            path = self.uiProjectTREE.model().filePath(
                self.uiProjectTREE.currentIndex()
            )
            if path:
                path = os.path.split(str(path))[0]
        else:
            path = str(
                self.uiExplorerTREE.model().filePath(self.uiExplorerTREE.currentIndex())
            )
            if path:
                path = os.path.split(str(path))[0]

        return os.path.normpath(path)

    def closeEvent(self, event):
        closedown = True
        for window in self.uiWindowsAREA.subWindowList():
            if not window.widget().checkForSave():
                closedown = False

        if closedown:
            self.recordSettings()
            Window.closeEvent(self, event)
        else:
            event.ignore()

    def displayTabs(self):
        self.uiWindowsAREA.setViewMode(self.uiWindowsAREA.TabbedView)

    def displayWindows(self):
        self.uiWindowsAREA.setViewMode(self.uiWindowsAREA.SubWindowView)

    def documentClose(self):
        window = self.uiWindowsAREA.activeSubWindow()
        if window and window.widget().checkForSave():
            self._closing = True
            window.close()
            self._closing = False
            return True
        return False

    def documentCloseAll(self):
        for window in self.uiWindowsAREA.subWindowList():
            if window.widget().checkForSave():
                self._closing = True
                window.close()
                self._closing = False

    def documentCloseAllExcept(self):
        for window in self.uiWindowsAREA.subWindowList():
            if (
                window != self.uiWindowsAREA.activeSubWindow()
                and window.widget().checkForSave()
            ):
                self._closing = True
                window.close()
                self._closing = False

    def documentCut(self):
        doc = self.currentDocument()
        if doc:
            doc.cut()

    def documentCopy(self):
        doc = self.currentDocument()
        if doc:
            doc.copy()

    def documentExec(self):
        doc = self.currentDocument()
        if doc:
            doc.exec_()

    def documentExecStandalone(self):
        doc = self.currentDocument()
        if doc:
            doc.execStandalone()

    def documentFindNext(self):
        doc = self.currentDocument()
        if not doc:
            return False

        doc.findNext(self.searchText(), self.searchFlags())
        return True

    def documentFindPrev(self):
        doc = self.currentDocument()
        if not doc:
            return False

        doc.findPrev(self.searchText(), self.searchFlags())
        return True

    def documentGoTo(self):
        doc = self.currentDocument()
        if doc:
            doc.goToLine()

    def documentMarkerToggle(self):
        doc = self.currentDocument()
        if doc:
            doc.markerToggle()

    def documentMarkerNext(self):
        doc = self.currentDocument()
        if doc:
            doc.markerNext()

    def documentMarkerClear(self):
        doc = self.currentDocument()
        if doc:
            doc.markerDeleteAll()

    def documentPaste(self):
        doc = self.currentDocument()
        if doc:
            doc.paste()

    def documentNew(self):
        from documenteditor import DocumentEditor

        editor = DocumentEditor(self)
        window = self.uiWindowsAREA.addSubWindow(editor)
        window.setWindowTitle(editor.windowTitle())
        window.installEventFilter(self)
        window.show()

    def documentOpen(self):
        from PyQt4.QtGui import QFileDialog
        import lexers

        filename = QFileDialog.getOpenFileName(
            self, 'Open file...', '', lexers.fileTypes()
        )
        if filename:
            self.load(filename)

    def documentRedo(self):
        doc = self.currentDocument()
        if doc:
            doc.redo()

    def documentSave(self):
        doc = self.currentDocument()
        if doc:
            doc.save()

    def documentSaveAs(self):
        doc = self.currentDocument()
        if doc:
            doc.saveAs()

    def documentSaveAll(self):
        for window in self.uiWindowsAREA.subWindowList():
            window.widget().save()

    def documentSelectAll(self):
        doc = self.currentDocument()
        if doc:
            doc.selectAll()

    def documentUndo(self):
        doc = self.currentDocument()
        if doc:
            doc.undo()

    def dragEnterEvent(self, event):
        # allow drag & drop events for files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

        # allow drag & drop events for tools
        source = event.source()
        if source and source.inherits('QTreeWidget'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        # allow drag & drop events for files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

        # allow drag & drop events for tools
        source = event.source()
        if source and source.inherits('QTreeWidget'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        # drop a file
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            import os.path

            for url in urls:
                text = str(url.toString())
                if text.startswith('file:///'):
                    filename = text.replace('file:///', '')

                    # load a blur project
                    if os.path.splitext(filename)[1] == '.blurproj':
                        self.setCurrentProject(IdeProject.fromXml(filename))
                    else:
                        self.load(filename)

        # drop a tool
        else:
            source = event.source()
            item = source.currentItem()

            tool = None
            try:
                tool = item.tool()
            except:
                pass

            if tool:
                self.setCurrentProject(IdeProject.fromTool(tool))

    def editItem(self, index):
        import blurdev

        import os

        filename = ''

        # load a project file
        if self.uiBrowserTAB.currentIndex() == 0:
            filename = str(self.uiProjectTREE.model().filePath(index))

        # focus an existing item
        elif self.uiBrowserTAB.currentIndex() == 1:
            self.uiWindowsAREA.subWindowList()[
                self.uiOpenTREE.indexOfTopLevelItem(index)
            ].setFocus()

        # load an explorer file
        elif self.uiBrowserTAB.currentIndex() == 2:
            filename = str(self.uiExplorerTREE.model().filePath(index))

        # load the file
        if filename:
            from PyQt4.QtCore import Qt

            # when shift+doubleclick, run the file
            from PyQt4.QtGui import QApplication

            modifiers = QApplication.instance().keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                import blurdev

                blurdev.core.runScript(filename)
            elif modifiers == (Qt.ShiftModifier | Qt.ControlModifier):
                from PyQt4.QtCore import QProcess

                QProcess.startDetached(filename, [filename], self.currentPath())
            else:
                self.load(filename)

    def eventFilter(self, object, event):
        if not self._closing and event.type() == event.Close:
            if not object.widget().checkForSave():
                event.ignore()
                return True
        return False

    def load(self, filename):
        filename = str(filename)

        # make sure the file is not already loaded
        for window in self.uiWindowsAREA.subWindowList():
            if window.widget().filename() == filename:
                window.setFocus()
                return True

        import os

        ext = os.path.splitext(str(filename))[1]

        cmd, key, path = IdeEditor.Command.get(ext, ('', '', ''))
        if cmd:
            from PyQt4.QtCore import QProcess

            if key:
                args = [key, filename]
            else:
                args = [filename]
            QProcess.startDetached(cmd, args, path)
        else:
            from documenteditor import DocumentEditor

            window = self.uiWindowsAREA.addSubWindow(DocumentEditor(self, filename))
            window.installEventFilter(self)
            window.setWindowTitle(os.path.basename(filename))
            window.show()
            window.move(10, 10)
            window.resize(
                self.uiWindowsAREA.width() - 20, self.uiWindowsAREA.height() - 20
            )

    def projectNew(self):
        from ideprojectdialog import IdeProjectDialog
        from ideproject import IdeProject

        proj = IdeProject()
        proj.setObjectName('New Project')
        if IdeProjectDialog.edit(proj):
            self.setCurrentProject(proj)

    def projectEdit(self):
        from ideprojectdialog import IdeProjectDialog
        from ideproject import IdeProject

        proj = IdeProject.fromXml(self.currentProject().filename())
        if IdeProjectDialog.edit(proj):
            self.setCurrentProject(proj)

    def projectFavorites(self):
        from ideprojectfavoritesdialog import IdeProjectFavoritesDialog

        proj = IdeProjectFavoritesDialog.getProject()
        if proj:
            self.setCurrentProject(proj)

    def projectOpen(self):
        from PyQt4.QtGui import QFileDialog

        filename = QFileDialog.getOpenFileName(
            self,
            'Blur IDE Project',
            '',
            'Blur IDE Project (*.blurproj);;XML Files (*.xml);;All Files (*.*)',
        )
        if filename:
            from ideproject import IdeProject

            proj = IdeProject.fromXml(filename)

            # load the project
            self.setCurrentProject(proj)
            self.uiBrowserTAB.setCurrentIndex(0)

    def projectOpenIndex(self):
        model = self.uiProjectTREE.model()
        object = model.object(self.uiProjectTREE.currentIndex())
        if not object:
            return

        import os.path

        path = str(object.filePath())
        if os.path.isfile(path):
            self.load(path)

    def projectExploreIndex(self):
        model = self.uiProjectTREE.model()
        object = model.object(self.uiProjectTREE.currentIndex())
        if not object:
            return

        import os

        path = str(object.filePath())
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        if os.path.exists(path):
            os.startfile(path)
        else:
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(None, 'Missing Path', 'Could not find %s' % path)

    def projectRefreshIndex(self):
        model = self.uiProjectTREE.model()
        object = model.object(self.uiProjectTREE.currentIndex())
        if object:
            object.refresh()

    def projectClose(self):
        self.setCurrentProject(None)

    def recordSettings(self):
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/ideeditor')

        filename = ''
        proj = self.currentProject()
        if proj:
            filename = proj.filename()

        pref.recordProperty('currproj', filename)

        from ideproject import IdeProject

        pref.recordProperty('proj_favorites', IdeProject.Favorites)
        pref.recordProperty('geom', self.geometry())

        pref.save()

    def refreshOpen(self):
        self.uiOpenTREE.blockSignals(True)
        self.uiOpenTREE.setUpdatesEnabled(False)
        self.uiOpenTREE.clear()

        from PyQt4.QtGui import QTreeWidgetItem

        for window in self.uiWindowsAREA.subWindowList():
            self.uiOpenTREE.addTopLevelItem(
                QTreeWidgetItem([str(window.windowTitle()).strip('*')])
            )

        self.uiOpenTREE.blockSignals(False)
        self.uiOpenTREE.setUpdatesEnabled(True)

    def refreshProject(self):
        proj = self.currentProject()
        if proj:
            from ideprojectmodel import IdeProjectModel

            self.uiProjectTREE.setModel(IdeProjectModel(proj))
            self.uiEditProjectACT.setEnabled(True)
            self.uiCloseProjectACT.setEnabled(True)
        else:
            self.uiProjectTREE.setModel(None)
            self.uiEditProjectACT.setEnabled(False)
            self.uiCloseProjectACT.setEnabled(False)

        self.updatePath()

    def restoreSettings(self):
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/ideeditor')

        # update project options
        from ideproject import IdeProject

        self.setCurrentProject(IdeProject.fromXml(pref.restoreProperty('currproj')))

        # update project favorites
        from ideproject import IdeProject

        IdeProject.Favorites = pref.restoreProperty('proj_favorites', [])

        # update ui items
        from PyQt4.QtCore import QRect

        geom = pref.restoreProperty('geom', QRect())
        if geom and not geom.isNull():
            self.setGeometry(geom)

    def runCommand(self):
        cmd = str(self.uiCommandLineDDL.currentText())
        split = cmd.split(' ')
        cmd = split[0]
        args = split[1:]

        if not cmd:
            return

        path = self.currentPath()

        if path:
            from PyQt4.QtCore import QProcess

            QProcess.startDetached(path + '/' + cmd, args, path)

        self.uiCommandLineDDL.lineEdit().setText('')

    def searchFlags(self):
        return self._searchFlags

    def searchText(self):
        if not self._searchDialog:
            return ''

        # refresh the search text
        if not self._searchDialog.isVisible():
            doc = self.currentDocument()
            if doc:
                text = doc.selectedText()
                if text:
                    self._searchText = text

        return self._searchText

    def showAssistant(self):
        from PyQt4.QtCore import QProcess

        QProcess.startDetached('c:/blur/common/assistant.exe', [], '')

    def showProjectMenu(self):
        from PyQt4.QtGui import QMenu, QCursor

        menu = QMenu(self)
        menu.addAction(self.uiNewACT)
        menu.addAction(self.uiNewFromTemplateACT)
        menu.addSeparator()
        menu.addAction('Open').triggered.connect(self.projectOpenIndex)
        menu.addAction('Explore').triggered.connect(self.projectExploreIndex)
        menu.addAction('Refresh').triggered.connect(self.projectRefreshIndex)
        menu.addSeparator()
        menu.addAction(self.uiEditProjectACT)

        menu.popup(QCursor.pos())

    def showConfig(self):
        # 		from blurdev.gui.dialogs.configdialog 	import ConfigDialog

        # create the general options
        # 		general = {}
        # 		from blurdev.ide.config.projectconfig import ProjectConfig
        # 		general[ 'Projects' ] = ProjectConfig

        # 		ConfigDialog.edit( { 'General Options': general } )
        pass

    def showDesigner(self):
        from PyQt4.QtCore import QProcess

        QProcess.startDetached('c:/blur/common/designer.exe', [], '')

    def showSdkBrowser(self):
        print 'coming soon'

    def setCurrentProject(self, project):
        self._project = project
        self.currentProjectChanged.emit(project)
        self.refreshProject()

    def setSearchText(self, text):
        self._searchText = text

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def updatePath(self):
        self.uiPathLBL.setText(self.currentPath() + '>')

    def updateTitle(self, window):
        if window:
            self.setWindowTitle('IDE | Code Editor - [%s]' % window.windowTitle())
        else:
            self.setWindowTitle('IDE | Code Editor')

    @staticmethod
    def createNew():
        window = IdeEditor.instance()
        window.documentNew()
        window.show()

    @staticmethod
    def instance():
        if not IdeEditor._instance:
            from PyQt4.QtCore import Qt

            IdeEditor._instance = IdeEditor()
            IdeEditor._instance.setAttribute(Qt.WA_DeleteOnClose, False)
        return IdeEditor._instance

    @staticmethod
    def edit(project=None, filename=None):
        window = IdeEditor.instance()
        window.setCurrentProject(project)
        window.show()

        # set the filename
        if filename:
            window.load(filename)


# if this is run directly
if __name__ == '__main__':
    import blurdev

    blurdev.launch(IdeEditor, coreName='ide')
