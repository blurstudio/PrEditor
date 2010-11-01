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
        self.uiOpenTREE.itemClicked.connect(self.editItem)
        self.uiExplorerTREE.doubleClicked.connect(self.editItem)
        self.uiExplorerTREE.clicked.connect(self.updatePath)
        self.uiWindowsAREA.subWindowActivated.connect(self.updateTitle)
        self.uiWindowsAREA.subWindowActivated.connect(self.checkOpen)
        self.documentTitleChanged.connect(self.refreshOpen)
        self.uiCommandLineDDL.lineEdit().returnPressed.connect(self.runCommand)

        # connect file menu
        from blurdev.ide.templatebuilder import TemplateBuilder

        self.uiNewACT.triggered.connect(self.documentNew)
        self.uiNewFromTemplateACT.triggered.connect(TemplateBuilder.createTemplate)
        self.uiOpenACT.triggered.connect(self.documentOpen)
        self.uiOpenProjectACT.triggered.connect(self.projectOpen)
        self.uiCloseACT.triggered.connect(self.documentClose)
        self.uiCloseAllACT.triggered.connect(self.documentCloseAll)
        self.uiCloseAllExceptACT.triggered.connect(self.documentCloseAllExcept)
        self.uiSaveACT.triggered.connect(self.documentSave)
        self.uiSaveAsACT.triggered.connect(self.documentSaveAs)
        self.uiSaveAllACT.triggered.connect(self.documentSaveAll)
        self.uiExitACT.triggered.connect(self.close)

        # connect edit menu
        self.uiUndoACT.triggered.connect(self.documentUndo)
        self.uiRedoACT.triggered.connect(self.documentRedo)
        self.uiCutACT.triggered.connect(self.documentCut)
        self.uiCopyACT.triggered.connect(self.documentCopy)
        self.uiPasteACT.triggered.connect(self.documentPaste)
        self.uiSelectAllACT.triggered.connect(self.documentSelectAll)
        self.uiFindACT.triggered.connect(self._searchDialog.show)
        self.uiFindNextACT.triggered.connect(self.documentFindNext)
        self.uiFindPrevACT.triggered.connect(self.documentFindPrev)

        # connect view menu
        self.uiDisplayWindowsACT.triggered.connect(self.displayWindows)
        self.uiDisplayTabsACT.triggered.connect(self.displayTabs)
        self.uiDisplayTileACT.triggered.connect(self.uiWindowsAREA.tileSubWindows)
        self.uiDisplayCascadeACT.triggered.connect(self.uiWindowsAREA.cascadeSubWindows)

        # connect tools menu
        self.uiAssistantACT.triggered.connect(self.showAssistant)
        self.uiDesignerACT.triggered.connect(self.showDesigner)
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

        filename = QFileDialog.getOpenFileName(self, 'Open file...')
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

    def editItem(self, index):
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
            self.load(filename)

    def eventFilter(self, object, event):
        if not self._closing and event.type() == event.Close:
            if not object.widget().checkForSave():
                event.ignore()
                return True
        return False

    def load(self, filename):
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
            self.refreshProject()

    def recordSettings(self):
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/ideeditor')

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
        else:
            self.uiProjectTREE.setModel(None)

        self.updatePath()

    def restoreSettings(self):
        import blurdev
        from blurdev import prefs

        pref = prefs.find('ide/ideeditor')

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

    def showConfig(self):
        from blurdev.gui.dialogs.configdialog import ConfigDialog

        # create the general options
        general = {}
        from blurdev.ide.config.projectconfig import ProjectConfig

        general['Projects'] = ProjectConfig

        ConfigDialog.edit({'General Options': general})

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

    blurdev.launch(IdeEditor)
