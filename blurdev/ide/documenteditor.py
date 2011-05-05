##
# 	\namespace	blurdev.ide.documenteditor
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtCore import pyqtProperty, Qt
from PyQt4.Qsci import *
from blurdev.enum import enum


class DocumentEditor(QsciScintilla):
    SearchDirection = enum('First', 'Forward', 'Backward')

    def __init__(self, parent, filename='', lineno=0):
        QsciScintilla.__init__(self, parent)

        # create custom properties
        self._filename = ''
        self._language = ''
        self._lastSearch = ''
        self._lastSearchDirection = self.SearchDirection.First

        # intialize settings
        from PyQt4.QtCore import Qt

        self.initSettings()

        # set one time properties
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(False)

        # create connections
        self.customContextMenuRequested.connect(self.showMenu)
        self.textChanged.connect(self.refreshTitle)

        # load the file
        if filename:
            self.load(filename)
        else:
            self.refreshTitle()

        # goto the line
        if lineno:
            self.setCursorPosition(lineno, 0)

    def checkForSave(self):
        if self.isModified():
            from PyQt4.QtGui import QMessageBox

            result = QMessageBox.question(
                self.window(),
                'Save changes to...',
                'Do you want to save your changes?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if result == QMessageBox.Yes:
                return self.save()
            elif result == QMessageBox.Cancel:
                return False
        return True

    def commentAdd(self):
        from blurdev.ide import lexers

        lexerMap = lexers.lexerMap(self._language)
        lineComment = ''
        if lexerMap:
            lineComment = lexerMap.lineComment

        if not lineComment:
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(
                None,
                'Line Comment Not Defined',
                'There is no line comment symbol defined for the "%s" language'
                % (self._language),
            )
            return False

        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()

        for line in range(startline, endline + 1):
            self.setCursorPosition(line, 0)
            self.insert(lineComment)
        return True

    def commentRemove(self):
        from blurdev.ide import lexers

        lexerMap = lexers.lexerMap(self._language)

        lineComment = ''
        if lexerMap:
            lineComment = lexerMap.lineComment

        lineComment = lexerMap.lineComment
        if not lineComment:
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(
                None,
                'Line Comment Not Defined',
                'There is no line comment symbol defined for the "%s" language'
                % (self._language),
            )
            return False

        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(lineComment)

        for line in range(startline, endline + 1):
            self.setSelection(line, 0, line, commentlen)
            if self.selectedText() == lineComment:
                self.removeSelectedText()

        return True

    def exec_(self):
        if self.save():
            import blurdev

            blurdev.core.runScript(self.filename())

    def execStandalone(self):
        if self.save():
            import os

            os.startfile(str(self.filename()))

    def findInFiles(self):
        from ideeditor import IdeEditor

        window = self.window()
        if isinstance(window, IdeEditor):
            window.uiFindInFilesACT.triggered.emit()

    def goToLine(self):
        from PyQt4.QtGui import QInputDialog

        line, accepted = QInputDialog.getInt(self, 'Line Number', 'Line:')
        if accepted:
            # MH 04/12/11 changed from line + 1 to line - 1 to make the gotoLine dialog go to the correct line.
            self.setCursorPosition(line - 1, 0)

    def language(self):
        return self._language

    def languageChosen(self, action):
        if action.text() == 'Plain Text':
            self.setLanguage('')
        else:
            self.setLanguage(action.text())

    def lineMarginWidth(self):
        return self.marginWidth(self.SymbolMargin)

    def load(self, filename):
        import os.path

        filename = str(filename)
        if filename and os.path.exists(filename):
            self.setText(open(filename).read())
            self.updateFilename(filename)
            return True
        return False

    def filename(self):
        return self._filename

    def findNext(self, text, flags):
        from PyQt4.QtGui import QTextDocument

        re = False
        cs = (flags & QTextDocument.FindCaseSensitively) != 0
        wo = (flags & QTextDocument.FindWholeWords) != 0
        wrap = True
        forward = True

        result = self.findFirst(text, re, cs, wo, wrap, forward)

        if not result:
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(
                None, 'No Text Found', 'Search string "%s" was not found.' % text
            )

        return result

    def findPrev(self, text, flags):
        from PyQt4.QtGui import QTextDocument

        re = False
        cs = (flags & QTextDocument.FindCaseSensitively) != 0
        wo = (flags & QTextDocument.FindWholeWords) != 0
        wrap = True
        forward = False

        isSelected = self.hasSelectedText()
        result = self.findFirst(text, re, cs, wo, wrap, forward)
        if result and isSelected:
            # If text is selected when finding previous, it will find the currently selected text so do another find.
            result = QsciScintilla.findNext(self)

        if not result:
            from PyQt4.QtGui import QMessageBox

            QMessageBox.critical(
                None, 'No Text Found', 'Search string "%s" was not found.' % text
            )

        return result

    def keyPressEvent(self, event):
        from PyQt4.QtCore import Qt

        if event.key() == Qt.Key_Backtab:
            self.unindentSelection()
        else:
            return QsciScintilla.keyPressEvent(self, event)

    def initSettings(self):
        # load default settings
        from blurdev.ide.idedocumentsettings import IdeDocumentSettings

        defaults = IdeDocumentSettings.defaultSettings()
        defaults.setupEditor(self)

        # override with project specific settings
        from blurdev.ide.ideproject import IdeProject

        project = IdeProject.currentProject()
        if project:
            project.documentSettings().setupEditor(self)

    def markerNext(self):
        line, index = self.getCursorPosition()
        newline = self.markerFindNext(line + 1, self.marginMarkerMask(1))

        # wrap around the document if necessary
        if newline == -1:
            newline = self.markerFindNext(0, self.marginMarkerMask(1))

        self.setCursorPosition(newline, index)

    def markerToggle(self):
        line, index = self.getCursorPosition()
        markers = self.markersAtLine(line)
        if not markers:
            marker = self.markerDefine(self.Circle)
            self.markerAdd(line, marker)
        else:
            self.markerDelete(line)

    def replace(self, text, all=False):
        # replace the current text with the inputed text
        searchtext = self.selectedText()

        # make sure something is selected
        if not searchtext:
            return 0

        sel = self.getSelection()
        alltext = self.text()

        # replace all of the instances of the text
        if all:
            count = alltext.count(searchtext)
            alltext.replace(searchtext, text, Qt.CaseSensitive)

        # replace a single instance of the text
        else:
            count = 1
            startpos = self.positionFromLineIndex(sel[0], sel[1])
            alltext.replace(startpos, len(searchtext), text)

        self.setText(alltext)
        self.setSelection(*sel)

        return count

    def refreshTitle(self):
        if self.filename():
            import os.path

            title = os.path.basename(str(self.filename()))
        else:
            title = 'New Document'

        if self.isModified():
            title += '*'

        self.setWindowTitle(title)
        parent = self.parent()
        if parent.inherits('QMdiSubWindow'):
            parent.setWindowTitle(self.windowTitle())

    def save(self):
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        if not filename:
            from PyQt4.QtGui import QFileDialog

            filename = QFileDialog.getSaveFileName(
                self.window(), 'Save File as...', self.filename()
            )

        if filename:
            # save the file to disk
            filename = str(filename)
            f = open(filename, 'w')
            f.write(unicode(self.text()).replace('\r', ''))  # scintilla puts both
            f.close()

            # update the file
            self.updateFilename(filename)
            return True
        return False

    def setLanguage(self, language):
        language = str(language)
        self._language = language

        from blurdev.ide import lexers

        lexers.load()
        lexer = lexers.lexer(language)
        if lexer:
            lexer.setFont(self.font())
            lexer.setParent(self)

        self.setLexer(lexer)
        self.initSettings()

    def setLineMarginWidth(self, width):
        self.setMarginWidth(self.SymbolMargin, width)

    def setShowFolding(self, state):
        if state:
            self.setFolding(self.BoxedTreeFoldStyle)
        else:
            self.setFolding(self.NoFoldStyle)

    def setShowLineNumbers(self, state):
        self.setMarginLineNumbers(self.SymbolMargin, state)

    def setShowWhitespaces(self, state):
        if state:
            self.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.setWhitespaceVisibility(QsciScintilla.WsInvisible)

    def showMenu(self):
        from PyQt4.QtGui import QMenu, QCursor

        menu = QMenu(self)

        menu.addAction('Find in Files...').triggered.connect(self.findInFiles)
        menu.addAction('Go to Line...').triggered.connect(self.goToLine)

        menu.addSeparator()

        menu.addAction('Collapse/Expand All').triggered.connect(self.toggleFolding)

        menu.addSeparator()

        menu.addAction('Comment Add').triggered.connect(self.commentAdd)
        menu.addAction('Comment Remove').triggered.connect(self.commentRemove)

        menu.addSeparator()

        submenu = menu.addMenu('View as...')
        submenu.addAction('Plain Text')
        submenu.addSeparator()

        import lexers

        for language in lexers.languages():
            submenu.addAction(language)

        submenu.triggered.connect(self.languageChosen)

        menu.popup(QCursor.pos())

    def showFolding(self):
        return self.folding() != self.NoFoldStyle

    def showLineNumbers(self):
        return self.marginLineNumbers(self.SymbolMargin)

    def showWhitespaces(self):
        return self.whitespaceVisibility() == QsciScintilla.WsVisible

    def toggleFolding(self):
        from PyQt4.QtGui import QApplication
        from PyQt4.QtCore import Qt

        self.foldAll(QApplication.instance().keyboardModifiers() == Qt.ShiftModifier)

    def updateFilename(self, filename):
        import os.path

        filename = str(filename)

        # determine if we need to modify the language
        if (
            not self._filename
            or os.path.splitext(filename)[1] != os.path.splitext(self._filename)[1]
        ):
            import lexers

            lexers.load()
            lexer = lexers.lexerFor(os.path.splitext(filename)[1])
            if lexer:
                lexer.setFont(self.font())
                lexer.setParent(self)
                self._language = lexers.languageFor(lexer)
            else:
                self._language = ''

            self.setLexer(lexer)
            self.initSettings()

        # update the filename information
        self._filename = filename
        self.setModified(False)
        self.window().documentTitleChanged.emit()
        self.refreshTitle()

    def unindentSelection(self):
        lineFrom = 0
        indexFrom = 0
        lineTo = 0
        indexTo = 0

        lineFrom, indexFrom, lineTo, indextTo = self.getSelection()

        for line in range(lineFrom, lineTo + 1):
            self.unindent(line)

    # expose properties for the designer
    pyLanguage = pyqtProperty("QString", language, setLanguage)
    pyLineMarginWidth = pyqtProperty("int", lineMarginWidth, setLineMarginWidth)
    pyShowLineNumbers = pyqtProperty("bool", showLineNumbers, setShowLineNumbers)
    pyShowFolding = pyqtProperty("bool", showFolding, setShowFolding)

    pyAutoCompletionCaseSensitivity = pyqtProperty(
        "bool",
        QsciScintilla.autoCompletionCaseSensitivity,
        QsciScintilla.setAutoCompletionCaseSensitivity,
    )
    pyAutoCompletionReplaceWord = pyqtProperty(
        "bool",
        QsciScintilla.autoCompletionReplaceWord,
        QsciScintilla.setAutoCompletionReplaceWord,
    )
    pyAutoCompletionShowSingle = pyqtProperty(
        "bool",
        QsciScintilla.autoCompletionShowSingle,
        QsciScintilla.setAutoCompletionShowSingle,
    )
    pyAutoCompletionThreshold = pyqtProperty(
        "int",
        QsciScintilla.autoCompletionThreshold,
        QsciScintilla.setAutoCompletionThreshold,
    )
    pyAutoIndent = pyqtProperty(
        "bool", QsciScintilla.autoIndent, QsciScintilla.setAutoIndent
    )
    pyBackspaceUnindents = pyqtProperty(
        "bool", QsciScintilla.backspaceUnindents, QsciScintilla.setBackspaceUnindents
    )
    pyIndentationGuides = pyqtProperty(
        "bool", QsciScintilla.indentationGuides, QsciScintilla.setIndentationGuides
    )
    pyIndentationsUseTabs = pyqtProperty(
        "bool", QsciScintilla.indentationsUseTabs, QsciScintilla.setIndentationsUseTabs
    )
    pyTabIndents = pyqtProperty(
        "bool", QsciScintilla.tabIndents, QsciScintilla.setTabIndents
    )
    pyUtf8 = pyqtProperty("bool", QsciScintilla.isUtf8, QsciScintilla.setUtf8)
    pyWhitespaceVisibility = pyqtProperty(
        "bool",
        QsciScintilla.whitespaceVisibility,
        QsciScintilla.setWhitespaceVisibility,
    )
