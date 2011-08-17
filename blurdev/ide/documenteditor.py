##
# 	\namespace	blurdev.ide.documenteditor
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

import os.path

from PyQt4.QtCore import pyqtProperty, Qt, QFile, pyqtSignal
from PyQt4.Qsci import QsciScintilla
from PyQt4.QtGui import QApplication, QFont, QFileDialog

from blurdev.enum import enum
from blurdev.ide import lang


class DocumentEditor(QsciScintilla):
    SearchDirection = enum('First', 'Forward', 'Backward')

    fontsChanged = pyqtSignal(
        QFont, QFont
    )  # emits the font size change (font size, margin font size)

    def __init__(self, parent, filename='', lineno=0):
        QsciScintilla.__init__(self, parent)

        # create custom properties
        self._filename = ''
        self._language = ''
        self._lastSearch = ''
        self._marginsFont = QFont()
        self._lastSearchDirection = self.SearchDirection.First

        # intialize settings
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
        from PyQt4.QtGui import QMessageBox as msg

        # collect the language
        language = lang.byName(self._language)
        if not language:
            msg.critical(
                None,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return False

        # grab the line comment
        comment = language.lineComment()
        if not comment:
            msg.critical(
                None,
                'No Line Comment Defined',
                'There is no line comment symbol defined for the %s language.'
                % (self._language),
            )
            return False

        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()

        for lineno in range(startline, endline + 1):
            self.setCursorPosition(lineno, 0)
            self.insert(comment)
        return True

    def commentRemove(self):
        from PyQt4.QtGui import QMessageBox

        # collect the language
        language = lang.byName(self._language)
        if not language:
            msg.critical(
                None,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return False

        # collect the expression
        comment = language.lineComment()
        if not comment:
            msg.critical(
                None,
                'No Line Comment Defined',
                'There is no line comment symbol defined for the "%s" language'
                % (self._language),
            )
            return False

        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(comment)

        for line in range(startline, endline + 1):
            self.setSelection(line, 0, line, commentlen)
            if self.selectedText() == comment:
                self.removeSelectedText()

        return True

    def copyFilenameToClipboard(self):
        QApplication.clipboard().setText(self._filename)

    def eventFilter(self, object, event):
        if event.type() == event.Close and not self.checkForSave():
            event.ignore()
            return True
        return False

    def exploreDocument(self):
        import os
        from blurdev import osystem

        path = self._filename
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        if os.path.exists(path):
            osystem.explore(path)
        else:
            QMessageBox.critical(
                None, 'Missing Path', 'Could not find %s' % path.replace('/', '\\')
            )

    def exec_(self):
        if self.save():
            import blurdev

            blurdev.core.runScript(self.filename())

    def execStandalone(self):
        if self.save():
            import os

            os.startfile(str(self.filename()))

    def findInFiles(self, state=False):
        from ideeditor import IdeEditor

        window = self.window()
        if isinstance(window, IdeEditor):
            window.uiFindInFilesACT.triggered.emit()

    def goToLine(self, line=None):
        from PyQt4.QtGui import QInputDialog

        if type(line) != int:
            line, accepted = QInputDialog.getInt(self, 'Line Number', 'Line:')
        else:
            accepted = True

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

    def launchConsole(self):
        if not self._filename:
            return False
        from blurdev import osystem

        osystem.console(self._filename)

    def lineMarginWidth(self):
        return self.marginWidth(self.SymbolMargin)

    def load(self, filename):
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
        # grab the document settings config set
        from blurdev.ide.ideeditor import IdeEditor
        from PyQt4.QtGui import QFont, QFontMetrics, QColor

        configSet = IdeEditor.documentConfigSet()

        # set the document settings
        section = configSet.section('Common::Document')

        # set visibility settings
        self.setAutoIndent(section.value('autoIndent'))
        self.setIndentationsUseTabs(section.value('indentationsUseTabs'))
        self.setTabIndents(section.value('tabIndents'))
        self.setTabWidth(section.value('tabWidth'))
        self.setCaretLineVisible(section.value('caretLineVisible'))
        self.setShowWhitespaces(section.value('showWhitespaces'))
        self.setMarginLineNumbers(0, section.value('showLineNumbers'))
        self.setIndentationGuides(section.value('showIndentations'))
        self.setEolVisibility(section.value('showEol'))

        if section.value('showLimitColumn'):
            self.setEdgeMode(self.EdgeLine)
            self.setEdgeColumn(section.value('limitColumn'))
        else:
            self.setEdgeMode(self.EdgeNone)

        # set endline settings
        eolmode = section.value('eolMode')

        # try to determine the end line mode based on the file itself
        if eolmode == 'Auto-Detect':
            text = self.text()

            # guess from the file, otherwise, use the base system
            if text:
                winCount = text.count('\r\n')  # windows style endline
                linCount = text.count('\n')  # unix style endline
                macCount = text.count('\r')  # mac style endline

                # use windows syntax
                if winCount and winCount == linCount and winCount == macCount:
                    eolmode = self.EolWindows
                elif macCount > linCount:
                    eolmode = self.EolMac
                else:
                    eolmode = self.EolUnix
            else:
                eolmode = None

        # force to windows mode
        elif eolmode == 'Windows':
            eolmode = self.EolWindows

        # force to unix mode
        elif eolmode == 'Unix':
            eolmode = self.EolUnix

        # force to mac mode
        elif eolmode == 'Mac':
            eolmode = self.EolMac

        # use default system mode
        else:
            eolmode = None

        if eolmode != None:
            # set new eols to being the inputed type
            self.setEolMode(eolmode)

        # convert the current eols if necessary
        if section.value('convertEol'):
            self.convertEols(self.eolMode())

        # set autocompletion settings
        if section.value('autoComplete'):
            self.setAutoCompletionSource(QsciScintilla.AcsAll)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)

        self.setAutoCompletionThreshold(section.value('autoCompleteThreshold'))

        # set the scheme settings
        scheme = configSet.section('Editor::Scheme')

        font = QFont()
        font.fromString(scheme.value('document_font'))

        mfont = QFont()
        mfont.fromString(scheme.value('document_marginFont'))

        self.setFont(font)
        self.setMarginsFont(mfont)
        self.setMarginWidth(0, QFontMetrics(mfont).width('0000000') + 5)

        # check to see if the user is using a custom color scheme
        if not scheme.value('document_override_colors'):
            return

        # setup the colors
        default_fg = scheme.value('document_color_text')
        default_bg = scheme.value('document_color_background')
        lexer = self.lexer()

        # set the coloring for a lexer
        if lexer:
            lexer.setFont(font)
            lexer.setDefaultPaper(default_bg)
            lexer.setDefaultColor(default_fg)
            lexer.setColor(default_bg)
            lexer.setColor(default_fg)

            # set the default coloring
            for i in range(128):
                lexer.setPaper(default_bg, i)
                lexer.setColor(default_fg, i)

            # lookup the language
            language = lang.byName(self.language())
            if language:
                for key, values in language.lexerColorTypes().items():
                    clr = scheme.value('document_color_%s' % key)
                    if not clr:
                        continue

                    for value in values:
                        lexer.setColor(clr, value)
                        lexer.setPaper(default_bg)

            # set default coloring styles
            lexer.setColor(
                scheme.value('document_color_indentGuide'), self.STYLE_INDENTGUIDE
            )
            lexer.setColor(
                scheme.value('document_color_invalidBrace'), self.STYLE_BRACEBAD
            )
            lexer.setColor(
                scheme.value('document_color_braceHighlight'), self.STYLE_BRACELIGHT
            )
            lexer.setColor(
                scheme.value('document_color_controlCharacter'), self.STYLE_CONTROLCHAR
            )
            lexer.setColor(
                scheme.value('document_color_lineNumber'), self.STYLE_LINENUMBER
            )

        # set the coloring for a document
        else:
            self.setColor(default_fg)
            self.setPaper(default_bg)

        # set editor level colors
        self.setFoldMarginColors(
            scheme.value('document_color_foldMarginText'),
            scheme.value('document_color_foldMargin'),
        )
        self.setCaretLineBackgroundColor(scheme.value('document_color_currentLine'))
        self.setCaretForegroundColor(scheme.value('document_color_cursor'))
        self.setSelectionForegroundColor(scheme.value('document_color_highlightText'))
        self.setSelectionBackgroundColor(scheme.value('document_color_highlight'))
        self.setMarginsBackgroundColor(scheme.value('document_color_margins'))
        self.setMarginsForegroundColor(scheme.value('document_color_marginsText'))
        self.setEdgeColor(scheme.value('document_color_limitColumn'))

        self.setUnmatchedBraceForegroundColor(
            scheme.value('document_color_invalidBrace')
        )
        self.setMarkerBackgroundColor(scheme.value('document_color_markerBackground'))
        self.setMarkerForegroundColor(scheme.value('document_color_markerForeground'))
        self.setMatchedBraceBackgroundColor(
            scheme.value('document_color_braceBackground')
        )
        self.setMatchedBraceForegroundColor(scheme.value('document_color_braceText'))

        palette = self.palette()
        palette.setColor(palette.Base, scheme.value('document_color_background'))
        palette.setColor(palette.Text, scheme.value('document_color_text'))
        self.setPalette(palette)

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

    def marginsFont(self):
        return self._marginsFont

    def redo(self):
        super(DocumentEditor, self).redo()
        self.refreshTitle()

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
        parent = self.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            parent.setWindowTitle(self.windowTitle())

    def save(self):
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        if not filename:
            filename = QFileDialog.getSaveFileName(
                self.window(), 'Save File as...', self.filename()
            )

        if filename:
            # save the file to disk
            f = QFile(filename)
            f.open(QFile.WriteOnly)
            self.write(f)
            f.close()

            # update the file
            self.updateFilename(filename)
            return True
        return False

    def setLanguage(self, language):
        # grab the language from the lang module if it is a string
        if type(language) != lang.Language:
            language = str(language)
            language = lang.byName(language)

        # collect the language's lexer
        if language:
            lexer = language.createLexer(self)
            self._language = language.name()
        else:
            lexer = None
            self._language = ''

        # set the lexer & init the settings
        self.setLexer(lexer)
        self.initSettings()

    def setLineMarginWidth(self, width):
        self.setMarginWidth(self.SymbolMargin, width)

    def setMarginsFont(self, font):
        super(DocumentEditor, self).setMarginsFont(font)
        self._marginsFont = font

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
        import blurdev
        from PyQt4.QtGui import QMenu, QCursor, QIcon

        menu = QMenu(self)

        act = menu.addAction('Find in Files...')
        act.triggered.connect(self.findInFiles)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/folder_find.png')))
        act = menu.addAction('Go to Line...')
        act.triggered.connect(self.goToLine)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto.png')))

        menu.addSeparator()

        act = menu.addAction('Collapse/Expand All')
        act.triggered.connect(self.toggleFolding)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/plus_minus.png')))

        menu.addSeparator()

        act = menu.addAction('Cut')
        act.triggered.connect(self.cut)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/cut.png')))

        act = menu.addAction('Copy')
        act.triggered.connect(self.copy)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        act = menu.addAction('Paste')
        act.triggered.connect(self.paste)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/paste.png')))

        menu.addSeparator()

        act = menu.addAction('Comment Add')
        act.triggered.connect(self.commentAdd)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_add.png')))
        act = menu.addAction('Comment Remove')
        act.triggered.connect(self.commentRemove)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_remove.png')))

        menu.addSeparator()

        submenu = menu.addMenu('View as...')
        submenu.addAction('Plain Text')
        submenu.addSeparator()

        for language in lang.languages():
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

    def undo(self):
        super(DocumentEditor, self).undo()
        self.refreshTitle()

    def updateFilename(self, filename):
        filename = str(filename)
        extension = os.path.splitext(filename)[1]

        # determine if we need to modify the language
        if not self._filename or extension != os.path.splitext(self._filename)[1]:
            self.setLanguage(lang.byExtension(extension))

        # update the filename information
        self._filename = filename
        self.setModified(False)

        try:
            self.window().emitDocumentTitleChanged()
        except:
            pass

        self.refreshTitle()

    def unindentSelection(self):
        lineFrom = 0
        indexFrom = 0
        lineTo = 0
        indexTo = 0

        lineFrom, indexFrom, lineTo, indextTo = self.getSelection()

        for line in range(lineFrom, lineTo + 1):
            self.unindent(line)

    def windowTitle(self):
        if self._filename:
            title = os.path.basename(self._filename)
        else:
            title = 'New Document'

        if self.isModified():
            title += '*'

        return title

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            font = self.font()
            marginsFont = self.marginsFont()
            lexer = self.lexer()
            if lexer:
                font = lexer.font(0)

            if event.delta() > 0:
                font.setPointSize(font.pointSize() + 1)
                marginsFont.setPointSize(marginsFont.pointSize() + 1)
            else:
                if font.pointSize() - 1 > 0:
                    font.setPointSize(font.pointSize() - 1)
                if marginsFont.pointSize() - 1 > 0:
                    marginsFont.setPointSize(marginsFont.pointSize() - 1)

            self.setMarginsFont(marginsFont)
            if lexer:
                lexer.setFont(font)
            else:
                self.setFont(font)

            self.fontsChanged.emit(font, marginsFont)
            event.accept()
        else:
            super(DocumentEditor, self).wheelEvent(event)

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
