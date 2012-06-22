##
# 	\namespace	blurdev.ide.ideeditor
#
# 	\remarks	This is the main ide window
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

import os
import copy

from PyQt4.QtCore import (
    pyqtSignal,
    QDir,
    QFileInfo,
    QMimeData,
    QProcess,
    QRect,
    QSize,
    QUrl,
    QVariant,
    Qt,
    QFileSystemWatcher,
)

from PyQt4.QtGui import (
    QAction,
    QApplication,
    QComboBox,
    QCursor,
    QFileDialog,
    QFileSystemModel,
    QFont,
    QIcon,
    QInputDialog,
    QListWidget,
    QMenu,
    QMessageBox,
    QTreeWidgetItem,
    QToolBar,
    QToolButton,
)

from blurdev.gui import Window
from blurdev.gui.dialogs.configdialog import ConfigSet
from blurdev.ide.ideproject import IdeProject, IdeProjectDelegate
from blurdev.ide.languagecombobox import LanguageComboBox

from blurdev import osystem, settings


class IdeEditor(Window):
    documentTitleChanged = pyqtSignal()
    # currentProjectChanged should be IdeProject or None.
    # Blur's Qt now is more strict on types being passed through signals.
    # this can be changed back to IdeProject, if None can no longer be passed in. Probubly a empty IdeProject in its place.
    currentProjectChanged = pyqtSignal(object)
    currentDocumentChanged = pyqtSignal()
    settingsRecorded = pyqtSignal()
    editorCreated = pyqtSignal(object)  # emitted when ever a subWindow is added

    _instance = None

    # define the global config set
    _globalConfigSet = None

    def __init__(self, parent=None):
        Window.__init__(self, parent)

        # load the ui
        import blurdev
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # create the registry for this instance
        from blurdev.ide.ideregistry import IdeRegistry

        self._registry = IdeRegistry()

        # synchronize the environment variables based on the currently loaded config settings
        self.syncEnvironment()
        self.updateSettings()

        # create custom properties
        self._closing = False
        self._searchText = ''
        self._searchFlags = 0
        self._searchDialog = None
        self._searchReplaceDialog = None
        self._searchFileDialog = None
        self._recentFiles = []
        self._recentFileMax = 10
        self._recentFileMenu = None
        self._loaded = False
        self._initfiles = []
        self.documentMarkrerDict = {}

        from idefilemenu import IdeFileMenu

        self._fileMenuClass = IdeFileMenu

        # strip out all pre-existing actions
        actions = self.uiWindowsAREA.findChildren(QAction)
        for action in actions:
            action.setParent(None)
            action.deleteLater()

        self.setAcceptDrops(True)
        QDir.setCurrent(osystem.expandvars(os.environ.get('BDEV_PATH_PROJECT', '')))

        # create the search dialog
        from blurdev.ide.finddialog import FindDialog

        self._searchDialog = FindDialog(self)
        self._searchDialog.setAttribute(Qt.WA_DeleteOnClose, False)

        # create a search replace dialog
        from blurdev.ide.findreplacedialog import FindReplaceDialog

        self._searchReplaceDialog = FindReplaceDialog(self)
        self._searchReplaceDialog.setAttribute(Qt.WA_DeleteOnClose, False)

        # create a template completer
        from blurdev import template

        self._templateCompleter = QListWidget(self)
        self._templateCompleter.addItems(template.allTemplNames())
        self._templateCompleter.setWindowFlags(Qt.Popup)
        self._templateCompleter.installEventFilter(self)

        # create the system model
        model = QFileSystemModel()
        model.setRootPath('')
        self.uiExplorerTREE.setModel(model)
        for i in range(1, 4):
            self.uiExplorerTREE.setColumnHidden(i, True)

        self.setupToolbars()

        # add the toolbar menu
        self.uiToolbarMENU = self.uiViewMENU.addMenu(self.createPopupMenu())
        self.uiToolbarMENU.setText('Toolbars')
        self.uiToolbarMENU.setToolTip('Control visibility of the toolbars')

        # setup settings, files and icons
        self.restoreSettings()
        self.refreshRecentFiles()
        self.setupIcons()

        blurdev.setAppUserModelID('BlurIDE')

        # create the project tree delegate
        self.uiProjectTREE.setItemDelegate(IdeProjectDelegate(self.uiProjectTREE))
        # Set the projectTREE's delegate so we can provide mimeData
        self.uiProjectTREE.setIdentifier('projectTree')
        self.uiProjectTREE.setDelegate(self)

        # create a method browser Widget
        from blurdev.ide.idemethodbrowserwidget import IdeMethodBrowserWidget

        self._methodBrowser = IdeMethodBrowserWidget(self)
        self.uiBrowserTAB.addTab(self._methodBrowser, 'Outliner')

        # make tree's resize to contents so they have a horizontal scroll bar
        for header in (
            self.uiProjectTREE.header(),
            self.uiOpenTREE.header(),
            self.uiExplorerTREE.header(),
        ):
            header.setStretchLastSection(False)
            header.setMovable(False)
            header.setResizeMode(header.ResizeToContents)

        # create connections
        self.uiProjectTREE.itemActivated.connect(self.editItem)
        self.uiProjectTREE.customContextMenuRequested.connect(self.showProjectMenu)
        self.uiProjectTREE.itemExpanded.connect(self.projectInitItem)
        self.uiBrowserTAB.currentChanged.connect(self._methodBrowser.refresh)

        self.uiOpenTREE.itemClicked.connect(self.editItem)
        self.uiExplorerTREE.activated.connect(self.editItem)
        self.uiExplorerTREE.customContextMenuRequested.connect(self.showExplorerMenu)

        self.uiWindowsAREA.subWindowActivated.connect(self.emitCurrentDocumentChanged)
        self.currentDocumentChanged.connect(self.updateTitle)
        self.currentDocumentChanged.connect(self.checkOpen)
        self.documentTitleChanged.connect(self.refreshOpen)

        # connect file menu
        self.uiNewACT.triggered.connect(self.documentNew)
        self.uiNewFromWizardACT.triggered.connect(self.documentFromWizard)
        self.uiOpenACT.triggered.connect(self.documentOpen)
        self.uiReloadFileACT.triggered.connect(self.documentReload)
        self.uiCloseACT.triggered.connect(self.documentClose)
        self.uiCloseAllACT.triggered.connect(self.documentCloseAll)
        self.uiCloseAllExceptACT.triggered.connect(
            lambda x: self.documentCloseAllExcept()
        )
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

        # connect document menu
        self.uiLineWrapACT.triggered.connect(self.toggleLineWrap)
        self.uiSmartHighlightingACT.triggered.connect(self.updateDocumentSettings)
        self.uiShowCaretLineACT.triggered.connect(self.updateDocumentSettings)
        self.uiShowIndentationsACT.triggered.connect(self.updateDocumentSettings)
        self.uiShowLineNumbersACT.triggered.connect(self.updateDocumentSettings)
        self.uiShowWhitespacesACT.triggered.connect(self.updateDocumentSettings)
        self.uiShowEndlinesACT.triggered.connect(self.updateDocumentSettings)

        # connect edit menu
        self.uiUndoACT.triggered.connect(self.documentUndo)
        self.uiRedoACT.triggered.connect(self.documentRedo)
        self.uiCutACT.triggered.connect(self.documentCut)
        self.uiCopyACT.triggered.connect(self.documentCopy)
        self.uiPasteACT.triggered.connect(self.documentPaste)
        self.uiSelectAllACT.triggered.connect(self.documentSelectAll)
        self.uiSelectToMatchingBraceACT.triggered.connect(self.documentSelectMatching)
        self.uiInsertTemplateACT.triggered.connect(self.documentChooseTemplate)
        self.uiCommentAddACT.triggered.connect(self.documentCommentAdd)
        self.uiCommentRemoveACT.triggered.connect(self.documentCommentRemove)
        self.uiCommentToggleACT.triggered.connect(self.documentCommentToggle)
        self.uiToLowercaseACT.triggered.connect(self.documentToLowercase)
        self.uiToUppercaseACT.triggered.connect(self.documentToUppercase)
        self._templateCompleter.itemClicked.connect(self.documentInsertTemplate)

        # connect search menu
        self.uiFindAndReplaceACT.triggered.connect(self.showSearchReplaceDialog)
        self.uiFindACT.triggered.connect(self.showSearchDialog)
        self.uiFindInFilesACT.triggered.connect(self.showSearchFilesDialog)
        self.uiFindNextACT.triggered.connect(self.documentFindNext)
        self.uiFindPrevACT.triggered.connect(self.documentFindPrev)
        self.uiReplaceACT.triggered.connect(self.documentReplace)
        self.uiReplaceAllACT.triggered.connect(self.documentReplaceAll)
        self.uiGotoACT.triggered.connect(self.documentGoTo)
        self.uiGotoDefinitionACT.triggered.connect(self.documentGoToDefinition)
        self.uiAddRemoveMarkerACT.triggered.connect(self.documentMarkerToggle)
        self.uiNextMarkerACT.triggered.connect(self.documentMarkerNext)
        self.uiClearMarkersACT.triggered.connect(self.documentMarkerClear)

        # connect run menu
        self.uiRunScriptACT.triggered.connect(self.documentExec)
        self.uiRunSelectedACT.triggered.connect(self.runSelected)
        self.uiCleanRunACT.triggered.connect(self.documentExecClean)
        self.uiCleanPathsACT.triggered.connect(self.cleanEnvironment)

        # connect view menu
        self.uiDisplayWindowsACT.triggered.connect(self.displayWindows)
        self.uiDisplayTabsACT.triggered.connect(self.displayTabs)
        self.uiDisplayTileACT.triggered.connect(self.uiWindowsAREA.tileSubWindows)
        self.uiDisplayCascadeACT.triggered.connect(self.uiWindowsAREA.cascadeSubWindows)

        # connect tools menu
        self.uiDesignerACT.triggered.connect(self.showDesigner)
        self.uiTreegruntACT.triggered.connect(blurdev.core.showTreegrunt)
        self.uiShowLoggerACT.triggered.connect(blurdev.core.showLogger)

        # connect advanced menu
        self.uiConfigurationACT.triggered.connect(self.editGlobalConfig)

        # connect help menu
        self.uiHelpAssistantACT.triggered.connect(self.showAssistant)
        self.uiSdkBrowserACT.triggered.connect(self.showSdkBrowser)
        self.uiBlurDevSiteACT.triggered.connect(self.showBlurDevSite)

        # connect debug menu
        blurdev.core.debugLevelChanged.connect(self.refreshDebugLevels)

        # connect browser menu actions
        self.uiCopyFilenameACT.triggered.connect(self.copyFilenameToClipboard)
        self.uiExploreACT.triggered.connect(self.documentExploreItem)
        self.uiConsoleACT.triggered.connect(self.launchConsole)

        self.uiNoDebugACT.triggered.connect(self.setNoDebug)
        self.uiDebugLowACT.triggered.connect(self.setLowDebug)
        self.uiDebugMidACT.triggered.connect(self.setMidDebug)
        self.uiDebugHighACT.triggered.connect(self.setHighDebug)

        self.uiAboutACT.triggered.connect(self.showAbout)

        # connect the global config set
        configSet = self.globalConfigSet()
        configSet.settingsChanged.connect(self.updateSettings)

        # refresh the ui
        self.updateTitle()
        self.refreshDebugLevels()

        # initialize the addons
        self.loadAddons()

        # sync the environment again after all the addons have been loaded
        self.syncEnvironment()

    def addSubWindow(self, editor):
        window = self.uiWindowsAREA.addSubWindow(editor)
        window.setWindowTitle(editor.windowTitle())
        window.installEventFilter(editor)

        # strip out all pre-existing actions
        actions = window.findChildren(QAction)
        for action in actions:
            action.setParent(None)
            action.deleteLater()

        # add new actions
        menu = window.systemMenu()

        # these actions need to have a new triggered call
        self.duplicateAction(menu, self.uiExploreACT, editor.exploreDocument)
        self.duplicateAction(menu, self.uiConsoleACT, editor.launchConsole)
        menu.addSeparator()
        self.duplicateAction(
            menu, self.uiCopyFilenameACT, editor.copyFilenameToClipboard
        )
        menu.addSeparator()
        self.duplicateAction(menu, self.uiReloadFileACT, editor.reloadFile)
        self.duplicateAction(menu, self.uiCloseACT, editor.closeEditor)
        menu.addAction(self.uiCloseAllACT)
        self.duplicateAction(menu, self.uiCloseAllExceptACT, editor.closeAllExcept)

        self.editorCreated.emit(editor)
        return window

    def checkOpen(self):
        # determine if there have been any changes
        if self.uiOpenTREE.topLevelItemCount() != len(
            self.uiWindowsAREA.subWindowList()
        ):
            self.refreshOpen()

    def copyFilenameToClipboard(self):
        if self.uiBrowserTAB.currentIndex() == 0:
            item = self.uiProjectTREE.currentItem()
            if item.isFileSystem():
                import os

                path = os.path.abspath(item.filePath())
            else:
                path = item.text(0)
        elif self.uiBrowserTAB.currentIndex() == 2:
            path = self.currentFilePath()
        else:
            path = ''

        QApplication.clipboard().setText(path)

    def createNewFolder(self):
        path = self.currentFilePath()
        if not path:
            return False

        import os

        if os.path.isfile(path):
            path = os.path.split(str(path))[0]

        text, accepted = QInputDialog.getText(self, 'New Folder Name', '')
        if accepted:
            folder = os.path.join(path, str(text))
            try:
                os.mkdir(folder)
            except:
                QMessageBox.critical(
                    self, 'Error Creating Folder', 'Could not create folder: ', folder
                )

        item = self.uiProjectTREE.currentItem()
        if item:
            item.refresh()

    def cleanEnvironment(self):
        import blurdev

        blurdev.activeEnvironment().resetPaths()

    def currentBasePath(self):
        path = ''
        import os.path

        # load from the project
        if self.uiBrowserTAB.currentIndex() == 0:
            item = self.uiProjectTREE.currentItem()
            if item:
                path = item.filePath()
                if path:
                    path = os.path.split(str(path))[0]
        else:
            path = str(
                self.uiExplorerTREE.model().filePath(self.uiExplorerTREE.currentIndex())
            )
            if path:
                path = os.path.split(str(path))[0]

        return os.path.normpath(path)

    def currentConfigSet(self):
        proj = self.currentProject()
        if proj:
            return proj.configSet()
        return self.globalConfigSet()

    def currentDocument(self):
        window = self.uiWindowsAREA.activeSubWindow()
        if window:
            return window.widget()
        return None

    def currentFilePath(self):
        filename = ''

        # load a project file
        if self.uiBrowserTAB.currentIndex() == 0:
            item = self.uiProjectTREE.currentItem()
            if item:
                filename = item.filePath()

        # load an explorer file
        elif self.uiBrowserTAB.currentIndex() == 2:
            filename = str(
                self.uiExplorerTREE.model().filePath(self.uiExplorerTREE.currentIndex())
            )

        return filename

    def currentProjectItem(self):
        return self.uiProjectTREE.currentItem()

    def currentProject(self):
        return IdeProject.currentProject()

    def closeEvent(self, event):
        closedown = True
        for window in self.uiWindowsAREA.subWindowList():
            if not window.widget().checkForSave():
                closedown = False
                break

        if closedown:
            self.recordSettings()
            Window.closeEvent(self, event)
        else:
            event.ignore()

    def displayTabs(self):
        self.uiWindowsAREA.setViewMode(self.uiWindowsAREA.TabbedView)
        self.uiDisplayTabsACT.setEnabled(False)
        self.uiDisplayWindowsACT.setEnabled(True)

    def displayWindows(self):
        self.uiWindowsAREA.setViewMode(self.uiWindowsAREA.SubWindowView)
        self.uiDisplayTabsACT.setEnabled(True)
        self.uiDisplayWindowsACT.setEnabled(False)

    def documents(self):
        return [subwindow.widget() for subwindow in self.uiWindowsAREA.subWindowList()]

    def documentClose(self):
        window = self.uiWindowsAREA.activeSubWindow()
        if window:
            return window.close()
        return False

    def documentCloseAll(self):
        for window in self.uiWindowsAREA.subWindowList():
            if not window.close():
                break

    def documentCloseAllExcept(self, current=None):
        """
            \Remarks	Closes all open subWindows except the current window or the passed in window. If no window is passed in it will take the current window.
            \param		current		<PyQt4.QtGui.QMdiSubWindow> || None
        """
        if not current:
            current = self.uiWindowsAREA.activeSubWindow()
        for window in self.uiWindowsAREA.subWindowList():
            if window != current:
                if not window.close():
                    break

    def documentCut(self):
        doc = self.currentDocument()
        if doc:
            doc.cut()

    def documentCommentAdd(self):
        doc = self.currentDocument()
        if doc:
            doc.commentAdd()

    def documentCommentRemove(self):
        doc = self.currentDocument()
        if doc:
            doc.commentRemove()

    def documentCommentToggle(self):
        doc = self.currentDocument()
        if doc:
            doc.commentToggle()

    def documentCopy(self):
        doc = self.currentDocument()
        if doc:
            doc.copy()

    def documentExec(self):
        doc = self.currentDocument()
        if doc:
            doc.exec_()

    def documentExecClean(self):
        self.cleanEnvironment()
        doc = self.currentDocument()
        if doc:
            doc.exec_()

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

    def documentReload(self):
        doc = self.currentDocument()
        if not doc:
            return False
        doc.reloadFile()

    def documentReplace(self):
        doc = self.currentDocument()
        if not doc:
            return False

        count = doc.replace(self.replaceText())
        return True

    def documentReplaceAll(self):
        doc = self.currentDocument()
        if not doc:
            return False

        count = doc.replace(self.replaceText(), searchtext=self.searchText(), all=True)

        # show the results in the messagebox
        QMessageBox.critical(
            self,
            'Replace Results',
            'Replaced %i instances of "%s" with "%s".'
            % (count, self.searchText(), self.replaceText()),
        )

    def documentFromWizard(self):
        QDir.setCurrent(self.currentFilePath())

        from idewizardbrowser import IdeWizardBrowser

        if IdeWizardBrowser.createFromWizard():
            self.projectRefreshItem()

    def documentGoTo(self):
        doc = self.currentDocument()
        if doc:
            doc.goToLine()

    def documentGoToDefinition(self):
        doc = self.currentDocument()
        if doc:
            doc.goToDefinition()

    def documentChooseTemplate(self):
        self._templateCompleter.move(QCursor.pos())
        self._templateCompleter.show()

    def documentInsertTemplate(self, item):
        if not item:
            return

        doc = self.currentDocument()
        if doc:
            options = {}

            fname = doc.filename()
            options['selection'] = doc.selectedText()
            options['filename'] = fname

            # include package, module info for python files
            import os.path, blurdev

            if os.path.splitext(fname)[1].startswith('.py'):
                options['package'] = blurdev.packageForPath(os.path.split(fname)[0])
                mname = os.path.basename(fname).split('.')[0]

                if mname != '__init__':
                    options['module'] = mname
                else:
                    options['module'] = ''

            from blurdev import template

            text = template.templ(item.text(), options)
            if text:
                doc.removeSelectedText()
                doc.insert(text)

        self._templateCompleter.close()

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

    def documentNew(self, trigger=True, filename='', lineno=''):
        from documenteditor import DocumentEditor

        # create the editor
        editor = DocumentEditor(self, filename, lineno)
        editor.fontsChanged.connect(self.updateDocumentFonts)

        editor.markerLoad(self.documentMarkrerDict.get(filename, []))

        # create the window
        window = self.addSubWindow(editor)
        window.show()

        return window

    def documentOpen(self):
        from blurdev.ide import lang

        filename = QFileDialog.getOpenFileName(
            self, 'Open file...', '', lang.filetypes()
        )
        if filename:
            self.load(filename)

    def documentOpenRecentTriggered(self, action):
        filename = unicode(action.data().toString())
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
            if doc.saveAs():
                self.recordRecentFile(doc.filename())

    def documentSaveAll(self):
        for window in self.uiWindowsAREA.subWindowList():
            window.widget().save()

    def documentSelectAll(self):
        doc = self.currentDocument()
        if doc:
            doc.selectAll()

    def documentSelectMatching(self):
        doc = self.currentDocument()
        if doc:
            doc.selectToMatchingBrace()

    def documentToLowercase(self):
        doc = self.currentDocument()
        if doc:
            doc.toLower()

    def documentToUppercase(self):
        doc = self.currentDocument()
        if doc:
            doc.toUpper()

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
            from blurdev import settings

            urls = event.mimeData().urls()
            for url in urls:
                text = str(url.toString())
                if text.startswith('file://'):
                    # striping off only 2 slashes preserves linux functionality
                    filename = text.replace('file://', '')

                    if settings.OS_TYPE == 'Windows':
                        if filename.startswith('/'):
                            # only drive letters have 3 slashes so we need to remove the starting slash
                            filename = filename.strip('/')
                        else:
                            # Network shares only have 2 slashes so this must be a network share, add the two foward slashes.
                            filename = '//' + filename

                    # ignore the registry when drag/dropping
                    self.load(filename, useRegistry=False)

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

    def duplicateAction(self, menu, source, trigger=None):
        """
            \remarks	Creates a new action with the same name and icon and adds it to the provided menu. Optionaly connect triggered to the new action.
            \param		menu	<QMenu>
            \param		source	<QAction>
            \param		trigger	<function> || <None>
            \return		<QAction>
        """
        act = menu.addAction(source.text())
        act.setIcon(source.icon())
        act.triggered.connect(trigger)
        return act

    def editGlobalConfig(self):
        # edit the globals config settings
        self._globalConfigSet.setCustomData('ide', self)
        if self._globalConfigSet.edit(self):
            # update the project's common settings
            proj = self.currentProject()
            if proj:
                options = QMessageBox.Yes | QMessageBox.No
                answer = QMessageBox.question(
                    self,
                    'Edit Project Settings',
                    'Do you want to update the common settings for the current project also?',
                    options,
                )
                if answer == QMessageBox.Yes:
                    proj.configSet().copyFrom(self.globalConfigSet())
                    proj.save()

            # update the environment & settings
            self.syncEnvironment()
            self.updateSettings()

    def emitDocumentTitleChanged(self):
        if not self.signalsBlocked():
            self.documentTitleChanged.emit()

    def emitCurrentDocumentChanged(self):
        if not self.signalsBlocked():
            document = self.currentDocument()

            # the document simply lost focus
            if not document and self.uiWindowsAREA.subWindowList():
                return

            # otherwise, this document has changed
            self.currentDocumentChanged.emit()

    def editItem(self):
        filename = str(self.currentFilePath())

        # load the file
        if filename:
            import os.path

            if not os.path.isfile(filename):
                return False

            # when shift+doubleclick, run the file
            modifiers = QApplication.instance().keyboardModifiers()

            # run script
            if modifiers == Qt.ShiftModifier:
                self.runCurrentScript()

            # run standalone
            elif modifiers == (Qt.ShiftModifier | Qt.ControlModifier):
                self.runCurrentStandalone()

            # load in the editor
            else:
                self.load(filename)

        # focus an existing item
        elif self.uiBrowserTAB.currentIndex() == 1:
            self.uiWindowsAREA.subWindowList()[
                self.uiOpenTREE.indexOfTopLevelItem(self.uiOpenTREE.currentItem())
            ].setFocus()

    def eventFilter(self, object, event):
        if object == self._templateCompleter:
            if event.type() == event.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._templateCompleter.close()

                elif event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                    self.documentInsertTemplate(self._templateCompleter.currentItem())

            return False

        return False

    def initialize(self):
        """ initialize the settings once the application has loaded """

        # restore initial files
        for filename in self._initfiles:
            self.load(filename)

        # initialize the logger
        import blurdev

        blurdev.core.logger(self)

        # launch with a given filename
        if 'BDEV_FILE_START' in os.environ:
            self.load(osystem.expandvars(os.environ['BDEV_FILE_START']))

    def launchConsole(self):
        filename = self.currentFilePath()
        if not filename:
            return False
        osystem.console(filename)

    def load(self, filename, lineno=0, useRegistry=True):
        filename = os.path.abspath(str(filename))

        if not QFileInfo(filename).isFile():
            return False

        # record the file to the recent files
        self.recordRecentFile(filename)

        # make sure the file is not already loaded
        for window in self.uiWindowsAREA.subWindowList():
            if window.widget().filename() == filename:
                window.setFocus()
                return True

        # run inside of a command context, provided ALT is not selected
        mods = QApplication.instance().keyboardModifiers()

        # load the file based on the registry
        if useRegistry and mods != Qt.AltModifier:
            from blurdev import osystem
            from blurdev.ide import RegistryType

            ext = os.path.splitext(str(filename))[-1]
            cmd = self.registry().findCommand(filename)

            # run a command line operation on the file
            if cmd and type(cmd) in (str, unicode):
                osystem.startfile(filename, cmd=osystem.expandvars(cmd))
                return True

            # run a method on the filename
            elif cmd:
                cmd(filename)
                return True

            # hardcoded support for sdk files
            elif ext == '.sdk':
                blurdev.core.sdkBrowser().showSdk(filename)
                return True

            # hardcoded support for blurproj files
            elif ext == '.blurproj':
                self.setCurrentProject(IdeProject.fromXml(filename))
                return True

        # otherwise, load it standard
        window = self.documentNew(filename=filename, lineno=lineno)

        # stagger the windows when in window mode
        if not self.uiWindowsAREA.viewMode() & self.uiWindowsAREA.TabbedView:
            window.move(10, 10)
            window.resize(
                self.uiWindowsAREA.width() - 20, self.uiWindowsAREA.height() - 20
            )

    def loadAddons(self):
        # import the ide addons
        from blurdev.ide.ideaddon import IdeAddon

        IdeAddon.init(self)

    def projectFindInFiles(self):
        import os.path

        filepath = str(self.currentFilePath())
        if os.path.isfile(filepath):
            filepath = os.path.dirname(filepath)

        # search specifying a base path
        dlg = self.searchFileDialog()
        dlg.setBasePath(filepath)
        dlg.show()

    def projectNew(self):
        from ideprojectdialog import IdeProjectDialog
        from ideproject import IdeProject

        proj = IdeProject()
        configSet = proj.configSet()
        configSet.setCustomData('ide', self)
        configSet.copyFrom(self.globalConfigSet())

        # edit the config set
        configSet.edit(self, 'Project::Settings')

        # update the project if necessary
        new_proj = configSet.customData('saved_project')
        if new_proj:
            self.setCurrentProject(IdeProject.fromXml(new_proj.filename()))

        self.updateSettings()

    def projectEdit(self):
        proj = self.currentProject()
        if not proj:
            return

        configSet = proj.configSet()
        configSet.setCustomData('ide', self)
        configSet.setCustomData('project', proj)

        # edit the config set
        configSet.edit(self, 'Project::Settings')

        new_proj = configSet.customData('saved_project')
        if new_proj:
            self.setCurrentProject(IdeProject.fromXml(new_proj.filename()))

        self.updateSettings()

    def projectFavorites(self):
        from ideprojectfavoritesdialog import IdeProjectFavoritesDialog

        proj = IdeProjectFavoritesDialog.getProject()
        if proj:
            self.setCurrentProject(proj)

    def projectInitItem(self, item):
        item.load()

    def projectOpen(self):
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

    def projectTreeMimeData(self, items):
        data = QMimeData()
        urls = []
        for item in items:
            fpath = item.filePath()
            if fpath:
                urls.append(QUrl('file:///' + fpath))

        data.setUrls(urls)
        return data

    def documentOpenItem(self):
        import os.path

        path = str(self.currentFilePath())
        if os.path.isfile(path):
            self.load(path)

    def documentExploreItem(self):
        import os
        from blurdev import settings

        path = str(self.currentFilePath())
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        if os.path.exists(path):
            osystem.explore(path)
        else:
            QMessageBox.critical(
                None, 'Missing Path', 'Could not find %s' % path.replace('/', '\\')
            )

    def openFileChanged(self, filename):
        # TODO: Open file changed message boxes should only pop up when BlurIDE regains primary focus, not as soon as the file is changed.
        # We should probubly create a messageing class that handles these messages.
        # make sure the file is not already loaded
        for window in self.uiWindowsAREA.subWindowList():
            if window.widget().filename() == filename:
                window.setFocus()
                window.widget().reloadChange()
                return True

    def openFileMonitor(self):
        """
            \Remarks	Returns the file system monitor so documents can connect to it, or none
            \Return 	<QFileSystemWatcher>||<None>
        """
        return self._openFileMonitor

    def projectRefreshItem(self):
        item = self.uiProjectTREE.currentItem()
        if not item:
            return False

        item.refresh()

    def projectClose(self):
        self.setCurrentProject(None)

    def recordSettings(self):
        # emit the signal so other items can manage their prefs
        self.settingsRecorded.emit()

        # save the settings
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/interface')

        filename = ''
        proj = self.currentProject()
        if proj:
            filename = proj.filename()

        pref.recordProperty('currproj', filename)
        pref.recordProperty(
            'selectedArgumentIndex', self.uiCommandArgsDDL.currentText()
        )
        pref.recordProperty('selectedCommandIndex', self.uiCommandDDL.currentText())
        pref.recordProperty('selectedRunLevel', self.uiExecuteDDL.currentText())
        pref.recordProperty(
            'toolbarVisibility',
            dict(
                [
                    (str(toolbar.windowTitle()), toolbar.isVisible())
                    for toolbar in self.findChildren(QToolBar)
                ]
            ),
        )

        pref.recordProperty('recentFiles', self._recentFiles)

        from ideproject import IdeProject

        pref.recordProperty('proj_favorites', IdeProject.Favorites)
        pref.recordProperty('geom', self.geometry())

        pref.recordProperty('documentMarkers', self.documentMarkrerDict)
        pref.recordProperty('windowState', self.windowState().__int__())
        pref.recordProperty('windowStateSave', self.saveState())

        pref.recordProperty('MidiViewMode', self.uiWindowsAREA.viewMode())
        pref.recordProperty(
            'openFiles',
            [str(doc.filename()) for doc in self.documents() if doc.filename()],
        )

        if blurdev.core.objectName() == 'ide':
            blurdev.core.logger().recordPrefs()

        # record module properties
        from blurdev.ide import ideglobals

        pref.recordModule(ideglobals)

        # save the preferences
        pref.save()

    def recordRecentFile(self, filename):
        if filename in self._recentFiles:
            self._recentFiles.remove(filename)
        self._recentFiles.insert(0, filename)
        self._recentFiles = self._recentFiles[: self._recentFileMax]
        self.refreshRecentFiles()

    def refreshDebugLevels(self):
        from blurdev.debug import DebugLevel, debugLevel

        dlevel = debugLevel()
        for act, level in [
            (self.uiNoDebugACT, 0),
            (self.uiDebugLowACT, DebugLevel.Low),
            (self.uiDebugMidACT, DebugLevel.Mid),
            (self.uiDebugHighACT, DebugLevel.High),
        ]:
            act.blockSignals(True)
            act.setChecked(level == dlevel)
            act.blockSignals(False)

    def refreshOpen(self):
        self.uiOpenTREE.blockSignals(True)
        self.uiOpenTREE.setUpdatesEnabled(False)
        self.uiOpenTREE.clear()

        for window in self.uiWindowsAREA.subWindowList():
            self.uiOpenTREE.addTopLevelItem(
                QTreeWidgetItem([str(window.windowTitle()).strip('*')])
            )

        self.uiOpenTREE.blockSignals(False)
        self.uiOpenTREE.setUpdatesEnabled(True)

    def refreshRecentFiles(self):
        # remove the recent file menu
        if self._recentFileMenu:
            self._recentFileMenu.triggered.disconnect(self.documentOpenRecentTriggered)
            self._recentFileMenu.close()
            self._recentFileMenu.setParent(None)
            self._recentFileMenu.deleteLater()
            self._recentFileMenu = None

        if self._recentFiles:
            # create a new recent file menu
            self._recentFileMenu = QMenu(self)
            self._recentFileMenu.setTitle('Recent Files')
            self._recentFileMenu.triggered.connect(self.documentOpenRecentTriggered)

            for index, filename in enumerate(self._recentFiles):
                action = QAction(self._recentFileMenu)
                action.setText('%i: %s' % (index + 1, os.path.basename(filename)))
                action.setData(filename)
                self._recentFileMenu.addAction(action)

            self.uiFileMENU.addMenu(self._recentFileMenu)

    def refreshTemplateCompleter(self):
        from blurdev import template

        self._templateCompleter.clear()
        self._templateCompleter.addItems(template.allTemplNames())

    def registerTemplatePath(self, key, path):
        from blurdev import template

        template.registerPath(key, path)
        self.refreshTemplateCompleter()

    def registry(self):
        return self._registry

    def restoreSettings(self):
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/interface')

        # load the recent files
        self._recentFiles = pref.restoreProperty('recentFiles', [])

        # update project options
        from ideproject import IdeProject

        self.setCurrentProject(
            IdeProject.fromXml(pref.restoreProperty('currproj')), silent=True
        )

        # restore the arguments index
        text = pref.restoreProperty('selectedArgumentIndex', None)
        if text:
            self.uiCommandArgsDDL.setCurrentIndex(self.uiCommandArgsDDL.findText(text))

        # restore the command index
        text = pref.restoreProperty('selectedCommandIndex', None)
        if text:
            self.uiCommandDDL.setCurrentIndex(self.uiCommandDDL.findText(text))

        # restore toolbar visibility
        tbarvis = pref.restoreProperty('toolbarVisibility', {})
        for tbar in self.findChildren(QToolBar):
            tbar.setVisible(tbarvis.get(str(tbar.windowTitle()), True))

        # restore the run level
        text = pref.restoreProperty('selectedRunLevel', None)
        if text:
            self.uiExecuteDDL.setCurrentIndex(self.uiExecuteDDL.findText(text))

        # update project favorites
        from ideproject import IdeProject

        IdeProject.Favorites = pref.restoreProperty('proj_favorites', [])

        # update ui items
        geom = pref.restoreProperty('geom', QRect())
        if geom and not geom.isNull():
            self.setGeometry(geom)

        # Save document markers
        self.documentMarkrerDict = pref.restoreProperty('documentMarkers', {})

        try:
            self.setWindowState(Qt.WindowStates(pref.restoreProperty('windowState', 0)))
        except:
            from blurdev import debug

            debug.debugObject(self.restoreSettings, 'error restoring window state')
        states = pref.restoreProperty('windowStateSave')
        if states:
            self.restoreState(states)

        # restore tabbed prefrence
        if (
            pref.restoreProperty('MidiViewMode', self.uiWindowsAREA.SubWindowView)
            == self.uiWindowsAREA.TabbedView
        ):
            self.displayTabs()
        else:
            self.displayWindows()

        # restore module settings
        from blurdev.ide import ideglobals

        pref.restoreModule(ideglobals)

        # record which files should load on open
        self._initfiles = pref.restoreProperty('openFiles', [])

    def runCurrentScript(self):
        filename = self.currentFilePath()
        if not filename:
            return False

        import blurdev

        blurdev.core.runScript(filename)
        return True

    def runCurrentStandalone(self):
        filename = self.currentFilePath()
        if not filename:
            return False

        import blurdev
        import os, sys

        blurdev.core.runStandalone(
            filename,
            basePath=self.currentBasePath(),
            environ=os.environ,
            paths=sys.path,
        )

    def runCurrentStandaloneDebug(self):
        filename = self.currentFilePath()
        if not filename:
            return False

        import blurdev
        from blurdev import debug

        blurdev.core.runStandalone(
            filename, debugLevel=debug.DebugLevel.High, basePath=self.currentBasePath()
        )

    def runSelected(self):
        project = self.currentProject()
        if project:
            selected = str(self.uiCommandDDL.currentText())
            commandList = project.commandList()
            if not selected in commandList:
                return False
            command = commandList[selected][1]
            if self.uiCommandArgsACT.isVisible():
                argumentList = project.argumentList()
                key = str(self.uiCommandArgsDDL.currentText())
                if key != 'No Args' and key in argumentList:
                    arguments = argumentList[key][1]
                    command += arguments
            text = self.uiExecuteDDL.currentText()
            if not command:
                return False

            if text == 'Debug':
                osystem.shell(command, self.currentBasePath(), persistent=True)
            else:
                osystem.shell(command, self.currentBasePath())

    def replaceText(self):
        if not self._searchReplaceDialog:
            return ''

        # refresh the replace results
        return self._searchReplaceDialog.replaceText()

    def searchFileDialog(self):
        if not self._searchFileDialog:
            from blurdev.ide.findfilesdialog import FindFilesDialog

            self._searchFileDialog = FindFilesDialog.instance(self)
            self._searchFileDialog.fileDoubleClicked.connect(self.load)
        return self._searchFileDialog

    def searchFlags(self):
        return self._searchFlags

    def searchText(self):
        if not (self._searchDialog and self._searchReplaceDialog):
            return ''

        # refresh the search text
        if not (
            self._searchDialog.isVisible() or self._searchReplaceDialog.isVisible()
        ):
            doc = self.currentDocument()
            if doc:
                text = doc.selectedText()
                if text:
                    self._searchText = text

        return self._searchText

    def setNoDebug(self):
        from blurdev import debug

        debug.setDebugLevel(None)

    def setLowDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Low)

    def setMidDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.Mid)

    def setHighDebug(self):
        from blurdev import debug

        debug.setDebugLevel(debug.DebugLevel.High)

    def setupIcons(self):
        import blurdev

        self.setWindowIcon(QIcon(blurdev.resourcePath('img/ide.png')))

        self.uiNoDebugACT.setIcon(QIcon(blurdev.resourcePath('img/debug_off.png')))
        self.uiDebugLowACT.setIcon(QIcon(blurdev.resourcePath('img/debug_low.png')))
        self.uiDebugMidACT.setIcon(QIcon(blurdev.resourcePath('img/debug_mid.png')))
        self.uiDebugHighACT.setIcon(QIcon(blurdev.resourcePath('img/debug_high.png')))

        self.uiNewACT.setIcon(QIcon(blurdev.resourcePath('img/ide/newfile.png')))
        self.uiNewFromWizardACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/newwizard.png'))
        )
        self.uiOpenACT.setIcon(QIcon(blurdev.resourcePath('img/ide/open.png')))
        self.uiReloadFileACT.setIcon(QIcon(blurdev.resourcePath('img/ide/refresh.png')))
        self.uiCloseACT.setIcon(QIcon(blurdev.resourcePath('img/ide/close.png')))
        self.uiSaveACT.setIcon(QIcon(blurdev.resourcePath('img/ide/save.png')))
        self.uiSaveAsACT.setIcon(QIcon(blurdev.resourcePath('img/ide/saveas.png')))
        self.uiExitACT.setIcon(QIcon(blurdev.resourcePath('img/ide/quit.png')))

        self.uiUndoACT.setIcon(QIcon(blurdev.resourcePath('img/ide/undo.png')))
        self.uiRedoACT.setIcon(QIcon(blurdev.resourcePath('img/ide/redo.png')))
        self.uiCopyACT.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))
        self.uiCutACT.setIcon(QIcon(blurdev.resourcePath('img/ide/cut.png')))
        self.uiCommentAddACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/comment_add.png'))
        )
        self.uiCommentRemoveACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/comment_remove.png'))
        )
        self.uiCommentToggleACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/comment_toggle.png'))
        )
        self.uiToLowercaseACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/lowercase.png'))
        )
        self.uiToUppercaseACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/uppercase.png'))
        )
        self.uiPasteACT.setIcon(QIcon(blurdev.resourcePath('img/ide/paste.png')))
        self.uiConfigurationACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/preferences.png'))
        )

        self.uiNewProjectACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/newproject.png'))
        )
        self.uiOpenProjectACT.setIcon(QIcon(blurdev.resourcePath('img/ide/open.png')))
        self.uiCloseProjectACT.setIcon(QIcon(blurdev.resourcePath('img/ide/close.png')))
        self.uiEditProjectACT.setIcon(QIcon(blurdev.resourcePath('img/ide/edit.png')))
        self.uiOpenFavoritesACT.setIcon(QIcon(blurdev.resourcePath('img/favorite.png')))

        self.uiCleanPathsACT.setIcon(QIcon(blurdev.resourcePath('img/ide/clean.png')))
        self.uiRunScriptACT.setIcon(QIcon(blurdev.resourcePath('img/ide/run.png')))
        self.uiRunSelectedACT.setIcon(QIcon(blurdev.resourcePath('img/ide/run.png')))

        self.uiDisplayRulerACT.setIcon(QIcon(blurdev.resourcePath('img/ide/ruler.png')))
        self.uiDisplayTabsACT.setIcon(QIcon(blurdev.resourcePath('img/ide/tabbed.png')))
        self.uiDisplayCascadeACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/windowed.png'))
        )
        self.uiDisplayTileACT.setIcon(QIcon(blurdev.resourcePath('img/ide/tile.png')))
        self.uiDisplayWindowsACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/windowed.png'))
        )
        self.uiToolbarMENU.setIcon(QIcon(blurdev.resourcePath('img/ide/toolbar.png')))

        self.uiCopyFilenameACT.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))
        self.uiExploreACT.setIcon(QIcon(blurdev.resourcePath('img/ide/find.png')))
        self.uiConsoleACT.setIcon(QIcon(blurdev.resourcePath('img/ide/console.png')))

        self.uiTreegruntACT.setIcon(
            QIcon(
                blurdev.relativePath(
                    blurdev.__file__, 'gui/dialogs/treegruntdialog/img/icon.png'
                )
            )
        )
        self.uiShowLoggerACT.setIcon(QIcon(blurdev.resourcePath('img/ide/console.png')))

        self.uiFindACT.setIcon(QIcon(blurdev.resourcePath('img/ide/find.png')))
        self.uiFindNextACT.setIcon(QIcon(blurdev.resourcePath('img/ide/findnext.png')))
        self.uiFindPrevACT.setIcon(QIcon(blurdev.resourcePath('img/ide/findprev.png')))
        self.uiFindInFilesACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/folder_find.png'))
        )
        self.uiFindAndReplaceACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/find_replace.png'))
        )
        self.uiGotoACT.setIcon(QIcon(blurdev.resourcePath('img/ide/goto.png')))
        self.uiGotoDefinitionACT.setIcon(
            QIcon(blurdev.resourcePath('img/ide/goto_def.png'))
        )

        self.uiSdkBrowserACT.setIcon(QIcon(blurdev.resourcePath('img/ide/sdk.png')))
        self.uiHelpAssistantACT.setIcon(QIcon(blurdev.resourcePath('img/ide/qt.png')))
        self.uiDesignerACT.setIcon(QIcon(blurdev.resourcePath('img/ide/qt.png')))
        self.uiBlurDevSiteACT.setIcon(QIcon(blurdev.resourcePath('img/ide/help.png')))

    def setupToolbars(self):
        # create the main toolbar
        self.uiMainTBAR = QToolBar(self)
        self.uiMainTBAR.setObjectName('MainToolbar')
        self.uiMainTBAR.setWindowTitle('Main')
        self.uiMainTBAR.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, self.uiMainTBAR)

        # add actions to the toolbar
        self.uiMainTBAR.addAction(self.uiNewACT)
        self.uiMainTBAR.addAction(self.uiNewFromWizardACT)
        self.uiMainTBAR.addAction(self.uiOpenACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiSaveACT)
        self.uiMainTBAR.addAction(self.uiSaveAsACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiUndoACT)
        self.uiMainTBAR.addAction(self.uiRedoACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiCutACT)
        self.uiMainTBAR.addAction(self.uiCopyACT)
        self.uiMainTBAR.addAction(self.uiPasteACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiCommentAddACT)
        self.uiMainTBAR.addAction(self.uiCommentRemoveACT)
        self.uiMainTBAR.addAction(self.uiCommentToggleACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiToLowercaseACT)
        self.uiMainTBAR.addAction(self.uiToUppercaseACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiFindPrevACT)
        self.uiMainTBAR.addAction(self.uiFindACT)
        self.uiMainTBAR.addAction(self.uiFindNextACT)
        self.uiMainTBAR.addAction(self.uiFindAndReplaceACT)
        self.uiMainTBAR.addAction(self.uiFindInFilesACT)
        self.uiMainTBAR.addAction(self.uiGotoACT)
        self.uiMainTBAR.addAction(self.uiGotoDefinitionACT)
        self.uiMainTBAR.addSeparator()
        self.uiMainTBAR.addAction(self.uiTreegruntACT)
        self.uiMainTBAR.addAction(self.uiDesignerACT)
        self.uiMainTBAR.addAction(self.uiShowLoggerACT)

        # create the project toolbar
        self.uiProjectTBAR = QToolBar(self)
        self.uiProjectTBAR.setObjectName('ProjectToolbar')
        self.uiProjectTBAR.setIconSize(QSize(16, 16))
        self.uiProjectTBAR.setWindowTitle('Project')
        self.addToolBar(Qt.TopToolBarArea, self.uiProjectTBAR)

        # create the widgets
        self.uiCommandDDL = QComboBox(self.uiProjectTBAR)
        self.uiExecuteDDL = QComboBox(self.uiProjectTBAR)
        self.uiCommandArgsDDL = QComboBox(self.uiProjectTBAR)
        self.uiExecuteDDL.addItems(['Run', 'Standalone', 'Debug'])

        self.uiCommandDDL.setMinimumWidth(100)
        policy = self.uiCommandDDL.sizePolicy()
        policy.setHorizontalPolicy(policy.Maximum)
        self.uiCommandDDL.setSizePolicy(policy)
        self.uiCommandArgsDDL.setSizePolicy(policy)
        self.uiCommandDDL.setMaxVisibleItems(40)
        self.uiCommandArgsDDL.setMaxVisibleItems(40)

        self.uiProjectTBAR.addWidget(self.uiCommandDDL)
        self.uiCommandArgsACT = self.uiProjectTBAR.addWidget(self.uiCommandArgsDDL)
        self.uiProjectTBAR.addWidget(self.uiExecuteDDL)
        self.uiProjectTBAR.addAction(self.uiRunSelectedACT)

        # create the Document toolbar
        self.uiLanguageTBAR = QToolBar(self)
        self.uiLanguageTBAR.setObjectName('LanguageToolbar')
        self.uiLanguageTBAR.setWindowTitle('Language')
        self.uiLanguageDDL = LanguageComboBox(self.uiLanguageTBAR)
        self.uiLanguageDDL.currentLanguageChanged.connect(self.setCurrentLanguage)
        self.uiLanguageTBAR.addWidget(self.uiLanguageDDL)

        self.addToolBar(Qt.TopToolBarArea, self.uiLanguageTBAR)

    def show(self):
        Window.show(self)

        # If a filename was passed in on launch, open the file
        if not self._loaded:
            # call the initialize method
            self.initialize()

        self._loaded = True

    def showAbout(self):
        from blurdev.ide.ideaboutdialog import IdeAboutDialog

        dlg = IdeAboutDialog(self)
        dlg.show()

    def showAssistant(self):
        QProcess.startDetached(
            osystem.expandvars(os.environ['BDEV_APP_QASSISTANT']), [], ''
        )

    def showBlurDevSite(self):
        osystem.startfile('http://blur-dev.googlecode.com')

    def showMenu(self, projectMode=True):
        menu = self._fileMenuClass(self, self.currentFilePath(), projectMode)
        menu.popup(QCursor.pos())

    def showProjectMenu(self):
        self.showMenu(True)

    def showExplorerMenu(self):
        self.showMenu(False)

    def showDesigner(self):
        QProcess.startDetached(
            osystem.expandvars(os.environ['BDEV_APP_QDESIGNER']), [], ''
        )

    def showSdkBrowser(self):
        import blurdev

        blurdev.core.sdkBrowser().show()

    def showSearchDialog(self):
        self._searchDialog.search(self.searchText())

    def showSearchReplaceDialog(self):
        self._searchReplaceDialog.search(self.searchText())

    def showSearchFilesDialog(self):
        self.searchFileDialog().show()

    def setCurrentLanguage(self, language):
        document = self.currentDocument()
        if not document:
            return
        document.setLanguage(language)

    def setCurrentProject(self, project, silent=True):
        # check to see if we should prompt the user before changing projects
        change = True
        import os.path

        if (
            not silent
            and project
            and IdeProject.currentProject()
            and os.path.normcase(project.filename())
            != os.path.normcase(IdeProject.currentProject().filename())
        ):
            change = (
                QMessageBox.question(
                    self,
                    'Change Projects',
                    'Are you sure you want to change to the %s project?'
                    % project.text(0),
                    QMessageBox.Yes | QMessageBox.No,
                )
                == QMessageBox.Yes
            )

        if change:
            self.uiProjectTREE.blockSignals(True)
            self.uiProjectTREE.setUpdatesEnabled(False)

            IdeProject.setCurrentProject(project)
            self.uiProjectTREE.clear()
            self.uiProjectTREE.addTopLevelItem(project)
            self.uiProjectTREE.blockSignals(False)
            self.uiProjectTREE.setUpdatesEnabled(True)

            # update the list of runable arguments
            self.uiCommandArgsDDL.clear()
            if project:
                self.uiCommandArgsDDL.addItem('No Args')
                self.uiCommandArgsDDL.insertSeparator(1)
                cmds = project.argumentList()
                offset = self.uiCommandArgsDDL.count()
                for index, key in enumerate(
                    sorted(cmds.keys(), key=lambda i: cmds[i][0])
                ):
                    if key.startswith("!Separator!"):
                        self.uiCommandArgsDDL.insertSeparator(index + offset)
                    else:
                        self.uiCommandArgsDDL.addItem(key)
                self.uiCommandArgsACT.setVisible(len(cmds))
            else:
                self.uiCommandArgsACT.setVisible(False)
            self.uiCommandArgsDDL.updateGeometry()

            # update the list of runable commands
            self.uiCommandDDL.clear()
            if project:
                cmds = project.commandList()
                for index, key in enumerate(
                    sorted(cmds.keys(), key=lambda i: cmds[i][0])
                ):
                    if key.startswith("!Separator!"):
                        self.uiCommandDDL.insertSeparator(index)
                    else:
                        self.uiCommandDDL.addItem(key)

            self.uiCommandDDL.updateGeometry()

            self.currentProjectChanged.emit(project)
            self.syncEnvironment()

    def setFileMenuClass(self, cls):
        self._fileMenuClass = cls

    def setSearchText(self, text):
        self._searchText = text

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def shutdown(self):
        # if this is the global instance, then allow it to be deleted on close
        if self == IdeEditor._instance:
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            IdeEditor._instance = None

        # clear out the system
        self.close()

    def syncEnvironment(self):
        # grab the current config (globals, or project)
        globalconfig = self.globalConfigSet()

        # update the registry from the config set
        from blurdev.ide.ideregistry import RegistryType

        registry = self.registry()
        registry.flush(RegistryType.GlobalOverride)
        registry.flush(RegistryType.ProjectOverride)

        section = globalconfig.section('Editor::Registry')
        for key, value in section.value('entries').items():
            registry.register(RegistryType.GlobalOverride, key, value)

        # create a copy of the startup environment
        environ = copy.deepcopy(settings.startup_environ)

        # update based on the current environment overrides
        section = globalconfig.section('Editor::Environment')
        for key, value in section.value('variables').items():
            environ[key] = value

        # grab the current config
        config = self.currentConfigSet()

        # sync the indent settings
        section = config.section('Common::Document')
        if section:
            if section.value('indentationsUseTabs'):
                environ['BDEV_DOCUMENT_INDENT'] = '\t'
            else:
                environ['BDEV_DOCUMENT_INDENT'] = '    '

        # update based on the current author settings
        author = config.section('Common::Author')
        if author:
            # set the environment settings based on the author config
            environ['BDEV_AUTHOR_EMAIL'] = author.value('email')
            environ['BDEV_AUTHOR_COMPANY'] = author.value('company')
            environ['BDEV_AUTHOR_NAME'] = author.value('name')
            environ['BDEV_AUTHOR_INITIALS'] = author.value('initials')

        # set the environment
        os.environ = environ

    def toggleLineWrap(self):
        doc = self.currentDocument()
        if not doc:
            return
        if doc.wrapMode():
            doc.setWrapMode(doc.WrapNone)
        else:
            doc.setWrapMode(doc.WrapWord)

    def unregisterTemplatePath(self, key):
        from blurdev import template

        template.unregisterPath(key)
        self.refreshTemplateCompleter()

    def updateDocumentSettings(self):
        configSet = self.currentConfigSet()
        if not configSet:
            return

        section = configSet.section('Common::Document')
        if not section:
            return

        section.setValue('showWhitespaces', self.uiShowWhitespacesACT.isChecked())
        section.setValue('showEol', self.uiShowEndlinesACT.isChecked())
        section.setValue('showIndentations', self.uiShowIndentationsACT.isChecked())
        section.setValue('showLineNumbers', self.uiShowLineNumbersACT.isChecked())
        section.setValue('caretLineVisible', self.uiShowCaretLineACT.isChecked())
        section.setValue('smartHighlighting', self.uiSmartHighlightingACT.isChecked())

        configSet.save()
        self.updateSettings()

    def updateDocumentFonts(self, font, marginFont):
        configSet = self.globalConfigSet()
        if not configSet:
            return

        section = configSet.section('Editor::Scheme')
        if not section:
            return

        section.setValue('document_font', font.toString())
        section.setValue('document_marginFont', marginFont.toString())

        configSet.save()

    def updateTitle(self):
        import blurdev
        from blurdev import version

        proj = self.currentProject()
        if proj:
            projtext = 'Project: %s' % proj.text(0)
        else:
            projtext = 'Project: <None>'

        document = self.currentDocument()

        if document:
            path = document.filename().replace('/', '\\')
            self.setWindowTitle(
                '%s | %s - [%s] - %s'
                % (
                    str(blurdev.core.objectName()).capitalize(),
                    projtext,
                    path,
                    version.toString(),
                )
            )
            self.uiLanguageDDL.setCurrentLanguage(document.language())
        else:
            self.setWindowTitle(
                '%s | %s - %s'
                % (
                    str(blurdev.core.objectName()).capitalize(),
                    projtext,
                    version.toString(),
                )
            )
            self.uiLanguageDDL.setCurrentLanguage('')

    def updateSettings(self):
        # update the application settings
        configSet = self.globalConfigSet()

        # grab the scheme section
        section = configSet.section('Editor::Scheme')

        # update the font
        font = QFont()
        font.fromString(section.value('application_font'))
        QApplication.setFont(font)

        # update the colors
        if section.value('application_override_colors'):
            palette = self.palette()
            palette.setColor(palette.Window, section.value('application_color_window'))
            palette.setColor(
                palette.WindowText, section.value('application_color_windowText')
            )
            palette.setColor(palette.Button, section.value('application_color_window'))
            palette.setColor(
                palette.ButtonText, section.value('application_color_windowText')
            )
            palette.setColor(
                palette.Base, section.value('application_color_background')
            )
            palette.setColor(
                palette.AlternateBase,
                section.value('application_color_alternateBackground'),
            )
            palette.setColor(palette.Text, section.value('application_color_text'))
            palette.setColor(
                palette.Highlight, section.value('application_color_highlight')
            )
            palette.setColor(
                palette.HighlightedText,
                section.value('application_color_highlightedText'),
            )
            self.setPalette(palette)

            # if the ide is managing the application, then update the scheme
            import blurdev

            if (
                blurdev.application
                and blurdev.core
                and blurdev.core.objectName() == 'ide'
            ):
                blurdev.application.setPalette(palette)

        # update the ui
        configSet = self.currentConfigSet()
        section = configSet.section('Common::Document')
        self.uiSmartHighlightingACT.setChecked(section.value('smartHighlighting'))
        self.uiShowCaretLineACT.setChecked(section.value('caretLineVisible'))
        self.uiShowIndentationsACT.setChecked(section.value('showIndentations'))
        self.uiShowLineNumbersACT.setChecked(section.value('showLineNumbers'))
        self.uiShowWhitespacesACT.setChecked(section.value('showWhitespaces'))
        self.uiShowEndlinesACT.setChecked(section.value('showEol'))

        # enable open file monitoring
        if section.value('openFileMonitor'):
            self._openFileMonitor = QFileSystemWatcher(self)
            self._openFileMonitor.fileChanged.connect(self.openFileChanged)
        else:
            self._openFileMonitor = None

        # update the documents
        for doc in self.documents():
            doc.initSettings()

    @staticmethod
    def createNew():
        window = IdeEditor.instance()
        window.documentNew()
        window.show()

    @staticmethod
    def edit(filename=None):
        window = IdeEditor.instance()
        window.show()

        # set the filename
        if filename:
            window.load(filename)

    @staticmethod
    def documentConfigSet():
        # create a temp config set to duplicate the settings from
        import blurdev.ide.config.common
        import blurdev.ide.config.editor

        configSet = ConfigSet()
        configSet.loadPlugins(blurdev.ide.config.common)
        configSet.loadPlugins(blurdev.ide.config.editor)

        # copy parameters from the global
        configSet.copyFrom(IdeEditor.globalConfigSet())

        # copy from project specific config set
        from blurdev.ide.ideproject import IdeProject

        proj = IdeProject.currentProject()
        if proj:
            configSet.copyFrom(proj.configSet())

        return configSet

    @staticmethod
    def globalConfigSet():
        if not IdeEditor._globalConfigSet:
            import blurdev.ide.config.common
            import blurdev.ide.config.editor

            IdeEditor._globalConfigSet = ConfigSet('ide/config')
            IdeEditor._globalConfigSet.loadPlugins(blurdev.ide.config.common)
            IdeEditor._globalConfigSet.loadPlugins(blurdev.ide.config.editor)
            IdeEditor._globalConfigSet.restore()

        return IdeEditor._globalConfigSet

    @staticmethod
    def instance(parent=None):
        # create the instance for the logger
        if not IdeEditor._instance:
            # determine default parenting
            import blurdev

            parent = None
            if not blurdev.core.isMfcApp():
                parent = blurdev.core.rootWindow()

            # create the logger instance
            inst = IdeEditor(parent)

            # protect the memory
            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            # cache the instance
            IdeEditor._instance = inst

        return IdeEditor._instance

    @staticmethod
    def instanceShutdown():
        """
            \remarks	Faster way to shutdown the instance of IdeEditor if it possibly was not used. Returns if shutdown was required.
            \return		<bool>
        """
        instance = IdeEditor._instance
        if instance:
            instance.shutdown()
            return True
        return False
