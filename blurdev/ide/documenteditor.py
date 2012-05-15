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
from PyQt4.QtGui import QApplication, QFont, QFileDialog, QInputDialog, QMessageBox

from blurdev.enum import enum
from blurdev.ide import lang
from blurdev.debug import debugMsg
from ideeditor import IdeEditor
import time


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
        self._fileMonitoringActive = False
        self._marginsFont = QFont()
        self._lastSearchDirection = self.SearchDirection.First
        self._saving = False
        self._saveTimer = 0.0

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

    def closeEditor(self):
        parent = self.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            parent.close()

    def closeAllExcept(self):
        window = self.window()
        parent = self.parent()
        if (
            (isinstance(window, IdeEditor))
            and parent
            and parent.inherits('QMdiSubWindow')
        ):
            window.documentCloseAllExcept(self.parent())

    def closeEvent(self, event):
        # unsubcribe the file from the open file monitor
        self.enableFileWatching(False)
        super(DocumentEditor, self).closeEvent(event)

    def commentAdd(self):
        # collect the language
        language = lang.byName(self._language)
        if not language:
            QMessageBox.critical(
                None,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return False

        # grab the line comment
        comment = language.lineComment()
        if not comment:
            QMessageBox.critical(
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
        # collect the language
        language = lang.byName(self._language)
        if not language:
            QMessageBox.critical(
                None,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return False

        # collect the expression
        comment = language.lineComment()
        if not comment:
            QMessageBox.critical(
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
        QApplication.clipboard().setText(os.path.abspath(self._filename))

    def enableFileWatching(self, state):
        """
            \Remarks	Enables/Disables open file change monitoring. If enabled, A dialog will pop up when ever the open file is changed externally.
                        If file monitoring is disabled in the IDE settings it will be ignored
            \Return		<bool>
        """
        # if file monitoring is enabled and we have a file name then set up the file monitoring
        window = self.window()
        self._fileMonitoringActive = False
        if isinstance(window, IdeEditor):
            fm = window.openFileMonitor()
            if fm:
                if state:
                    fm.addPath(self._filename)
                    self._fileMonitoringActive = True
                else:
                    fm.removePath(self._filename)
        return self._fileMonitoringActive

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
        window = self.window()
        if isinstance(window, IdeEditor):
            window.uiFindInFilesACT.triggered.emit()

    def goToLine(self, line=None):
        if type(line) != int:
            line, accepted = QInputDialog.getInt(self, 'Line Number', 'Line:')
        else:
            accepted = True

        if accepted:
            # MH 04/12/11 changed from line + 1 to line - 1 to make the gotoLine dialog go to the correct line.
            self.setCursorPosition(line - 1, 0)
            self.ensureLineVisible(line)

    def goToDefinition(self, text=None):
        if not text:
            text = self.selectedText()
            if not text:
                text, accepted = QInputDialog.getText(self, 'def Name', 'Name:')
            else:
                accepted = True
        else:
            accepted = True
        if accepted:
            descriptors = lang.byName(self.language()).descriptors()
            docText = self.text()
            for descriptor in descriptors:
                result = descriptor.search(docText)
                while result:
                    name = unicode(result.group('name'))
                    if name.startswith(text):
                        self.findNext(name, 0)
                        return
                    result = descriptor.search(docText, result.end())

    def language(self):
        return self._language

    def languageChosen(self, action):
        window = self.window()
        self._fileMonitoringActive = False
        if isinstance(window, IdeEditor):
            window.uiLanguageDDL.setCurrentLanguage(action.text())

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
            f = QFile(filename)
            f.open(QFile.ReadOnly)
            self.read(f)
            f.close()
            self.updateFilename(filename)
            self.enableFileWatching(True)
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
            self.findTextNotFound(text)

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
            self.findTextNotFound(text)

        return result

    def findTextNotFound(self, text):
        try:
            line = int(text)
            result = QMessageBox.critical(
                None,
                'No Text Found',
                'Search string "%s" was not found. \nIt looks like a line number, would you like to goto line %i?'
                % (text, line),
                buttons=(QMessageBox.Yes | QMessageBox.No),
            )
            if result == QMessageBox.Yes:
                self.goToLine(line)
        except:
            QMessageBox.critical(
                None, 'No Text Found', 'Search string "%s" was not found.' % text
            )

    def keyPressEvent(self, event):
        from PyQt4.QtCore import Qt

        if event.key() == Qt.Key_Backtab:
            self.unindentSelection()
        else:
            return QsciScintilla.keyPressEvent(self, event)

    def initSettings(self):
        # grab the document settings config set
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
        # 		eolmode = section.value('eolMode' )

        # try to determine the end line mode based on the file itself
        # 		if ( eolmode == 'Auto-Detect' ):
        # 			text        = self.text()
        #
        # 			# guess from the file, otherwise, use the base system
        # 			if ( text ):
        # 				winCount    = text.count('\r\n')    # windows style endline
        # 				linCount    = text.count('\n')      # unix style endline
        # 				macCount    = text.count('\r')      # mac style endline
        #
        # 				# use windows syntax
        # 				if ( winCount and winCount == linCount and winCount == macCount ):
        # 					eolmode = self.EolWindows
        # 				elif ( macCount > linCount ):
        # 					eolmode = self.EolMac
        # 				else:
        # 					eolmode = self.EolUnix
        # 			else:
        # 				eolmode = None
        #
        # 		# force to windows mode
        # 		elif ( eolmode == 'Windows' ):
        # 			eolmode = self.EolWindows
        #
        # 		# force to unix mode
        # 		elif ( eolmode == 'Unix' ):
        # 			eolmode = self.EolUnix
        #
        # 		# force to mac mode
        # 		elif ( eolmode == 'Mac' ):
        # 			eolmode = self.EolMac
        #
        # 		# use default system mode
        # 		else:
        # 			eolmode = None
        #
        # 		if ( eolmode != None ):
        # 			# set new eols to being the inputed type
        # 			self.setEolMode(eolmode)
        #
        # 		# convert the current eols if necessary
        # 		if (section.value('convertEol')):
        # 			self.convertEols(self.eolMode())

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
        self._enableFontResizing = scheme.value('document_EnableFontResize')

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

    def reloadFile(self):
        return self.reloadDialog(
            'Are you sure you want to reload %s? You will lose all changes'
            % os.path.basename(self.filename())
        )

    def reloadChange(self):
        """
            \Remarks	Callback for file monitoring. If a file was modified or deleted this method is called when Open File Monitoring is enabled.
                        Returns if the file was updated or left open
            \Return		<bool>
        """
        debugMsg('Reload Change called: %f' % self._saveTimer)
        # 		if self._saving:
        if time.time() - self._saveTimer < 0.25:
            # If we are saving no need to reload the file
            # 			self._saving = False
            debugMsg('timer has not expired')
            return False
        if not os.path.isfile(self.filename()):
            debugMsg('The file was deleted: %r' % self._saving)
            # the file was deleted, ask the user if they still want to keep the file in the editor.
            result = QMessageBox.question(
                self.window(),
                'File Removed...',
                'File: %s has been deleted.\nKeep file in editor?' % self.filename(),
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if result == QMessageBox.No:
                debugMsg(
                    'The file was deleted, removing document from editor: %r'
                    % self._saving
                )
                self.parent().close()
                return False
            # TODO: The file no longer exists, and the document should be marked as changed.
            debugMsg(
                'The file was deleted, But the user left it in the editor: %r'
                % self._saving
            )
            self.enableFileWatching(False)
            return True
        debugMsg('Defaulting to reload message: %r' % self._saving)
        return self.reloadDialog(
            'File: %s has been changed.\nReload from disk?' % self.filename()
        )

    def reloadDialog(self, message, title='Reload File...'):
        result = QMessageBox.question(
            self.window(), title, message, QMessageBox.Yes | QMessageBox.No
        )
        if result == QMessageBox.Yes:
            return self.load(self.filename())
        return False

    def replace(self, text, searchtext=None, all=False):
        # replace the current text with the inputed text
        if not searchtext:
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

        self.setText(alltext)  # This system causes the undoStack to be cleared.
        self.setSelection(*sel)

        return count

    def refreshTitle(self):
        parent = self.parent()
        if parent and parent.inherits('QMdiSubWindow'):
            parent.setWindowTitle(self.windowTitle())

    def save(self):
        debugMsg(
            '------------------------------ Save Called ------------------------------ '
        )
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        debugMsg(
            '------------------------------ Save As Called ------------------------------ '
        )
        newFile = False
        if not filename:
            newFile = True
            filename = QFileDialog.getSaveFileName(
                self.window(), 'Save File as...', self.filename()
            )

        if filename:
            self._saveTimer = time.time()
            # 			if self._fileMonitoringActive:
            # 				self._saving = True
            # 				debugMsg('File Monitoring active, seting self._saving = %r' % self._saving)
            # save the file to disk
            f = QFile(filename)
            f.open(QFile.WriteOnly)
            # make sure the file is writeable
            if f.error() != QFile.NoError:
                # 				self._saving = False
                debugMsg('An error occured while saving = %r' % self._saving)
                QMessageBox.question(
                    self.window(),
                    'Error saving file...',
                    'There was a error saving the file. Error Code: %i' % f.error(),
                    QMessageBox.Ok,
                )
                f.close()
                return False
            self.write(f)
            f.close()

            # update the file
            self.updateFilename(filename)
            if newFile:
                self.enableFileWatching(True)
            return True
        return False

    def setLanguage(self, language):
        if language == 'Plain Text':
            language = ''
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
        act = menu.addAction('Go to Definition')
        act.triggered.connect(self.goToDefinition)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto_def.png')))

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
        l = self.language()
        act = submenu.addAction('Plain Text')
        if l == "":
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/check.png')))
        submenu.addSeparator()

        for language in lang.languages():
            act = submenu.addAction(language)
            if language == l:
                act.setIcon(QIcon(blurdev.resourcePath('img/ide/check.png')))

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
        if self._enableFontResizing and event.modifiers() == Qt.ControlModifier:
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
