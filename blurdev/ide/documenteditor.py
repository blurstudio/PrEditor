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

from PyQt4.QtCore import pyqtProperty, Qt, QFile, pyqtSignal, QTextCodec
from PyQt4.Qsci import QsciScintilla
from PyQt4.QtGui import (
    QApplication,
    QFont,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QColor,
)

from blurdev.enum import enum
from blurdev.ide import lang
from blurdev.debug import debugMsg, DebugLevel
from ideeditor import IdeEditor
import time, re


class DocumentEditor(QsciScintilla):
    SearchDirection = enum('First', 'Forward', 'Backward')
    SearchOptions = enum('Backward', 'CaseSensitive', 'WholeWords', 'QRegExp')

    fontsChanged = pyqtSignal(
        QFont, QFont
    )  # emits the font size change (font size, margin font size)
    documentSaved = pyqtSignal(
        QsciScintilla, object
    )  # (DocumentEditor, filename) emitted when ever the document is saved.

    def __init__(self, parent, filename='', lineno=0):
        self._showSmartHighlighting = True
        QsciScintilla.__init__(self, parent)

        # create custom properties
        self._filename = ''
        self._language = ''
        self._lastSearch = ''
        self._textCodec = None
        self._fileMonitoringActive = False
        self._marginsFont = QFont()
        self._lastSearchDirection = self.SearchDirection.First
        self._saveTimer = 0.0
        self._autoReloadOnChange = False
        # TODO: figure out how to query these values
        # QSci doesnt provide accessors to these values, so store them internally
        self._foldMarginBackgroundColor = QColor(224, 224, 224)
        self._foldMarginForegroundColor = QColor(Qt.white)
        self._marginsBackgroundColor = QColor(224, 224, 224)
        self._marginsForegroundColor = QColor()
        self._caretForegroundColor = QColor()
        self._caretBackgroundColor = QColor(255, 255, 255, 255)
        # used to store the right click location
        self._clickPos = None
        # dialog shown is used to prevent showing multiple versions of the of the confirmation dialog.
        # this is caused because multiple signals are emitted and processed.
        self._dialogShown = False
        self.setSmartHighlightingRegEx()

        # intialize settings
        self.initSettings()

        # set one time properties
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(False)

        # create connections
        self.customContextMenuRequested.connect(self.showMenu)
        self.selectionChanged.connect(self.updateSelectionInfo)

        # load the file
        if filename:
            self.load(filename)
        else:
            self.refreshTitle()

        # goto the line
        if lineno:
            self.setCursorPosition(lineno, 0)

    def autoFormat(self):
        try:
            import autopep8
        except ImportError:
            QMessageBox.warning(
                self.window(),
                'autopep8 missing',
                'The autopep8 library is missing. To use this feature you must install it. https://pypi.python.org/pypi/autopep8/ ',
                QMessageBox.Ok,
            )
            return
        version = autopep8.__version__.split('.')
        if version and version[0] < 1:
            QMessageBox.warning(
                self.window(),
                'autopep8 out of date',
                'The autopep8 library is out of date and needs to be updated. To use this feature you must install it. https://pypi.python.org/pypi/autopep8/ ',
                QMessageBox.Ok,
            )
            return
        options = autopep8.parse_args([''])
        options.max_line_length = self.edgeColumn()
        fixed = autopep8.fix_code(unicode(self.text()), options=options)
        self.beginUndoAction()
        startline, startcol, endline, endcol = self.getSelection()
        self.selectAll()
        self.removeSelectedText()
        self.insert(fixed)
        if self.indentationsUseTabs():
            # fix tab indentations
            self.indentSelection(True)
            self.unindentSelection(True)
        self.setSelection(startline, startcol + 1, endline, endcol)
        self.endUndoAction()

    def autoReloadOnChange(self):
        return self._autoReloadOnChange

    def caretBackgroundColor(self):
        return self._caretBackgroundColor

    def caretForegroundColor(self):
        return self._caretForegroundColor

    def setCaretLineBackgroundColor(self, color):
        self._caretBackgroundColor = color
        super(DocumentEditor, self).setCaretLineBackgroundColor(color)

    def setCaretForegroundColor(self, color):
        self._caretForegroundColor = color
        super(DocumentEditor, self).setCaretForegroundColor(color)

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

    def closeEvent(self, event):
        self.disableTitleUpdate()
        super(DocumentEditor, self).closeEvent(event)

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

    def commentCheck(self):
        # collect the language
        language = lang.byName(self._language)
        if not language:
            QMessageBox.critical(
                None,
                'No Language Defined',
                'There is no language defined for this editor.',
            )
            return '', False

        # grab the line comment
        comment = language.lineComment()
        if not comment:
            QMessageBox.critical(
                None,
                'No Line Comment Defined',
                'There is no line comment symbol defined for the "%s" language.'
                % (self._language),
            )
            return '', False
        return comment, True

    def commentAdd(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        self.beginUndoAction()
        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()

        for line in range(startline, endline + 1):
            # do not comment the last line if it contains no selection
            if line != endline or endcol:
                self.setCursorPosition(line, 0)
                self.insert(comment)
        # restore the currently selected text and compensate for the new characters
        if endcol:
            # only adjust the end column value if it contained a selection in the first place.
            endcol += 1
        self.setSelection(startline, startcol + 1, endline, endcol)
        self.endUndoAction()
        return True

    def commentRemove(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        # lookup the selected text positions
        self.beginUndoAction()
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(comment)

        for line in range(startline, endline + 1):
            # do not un-comment the last line if it contains no selection
            if line != endline or endcol:
                self.setSelection(line, 0, line, commentlen)
                if self.selectedText() == comment:
                    self.removeSelectedText()
                    if line == startline:
                        startcol -= 1
                    if line == endline:
                        endcol -= 1
        # restore the currently selected text
        self.setSelection(startline, startcol, endline, endcol)
        self.endUndoAction()
        return True

    def commentToggle(self):
        comment, result = self.commentCheck()
        if not result:
            return False

        self.beginUndoAction()
        # lookup the selected text positions
        startline, startcol, endline, endcol = self.getSelection()
        commentlen = len(comment)

        for line in range(startline, endline + 1):
            # do not toggle comments on the last line if it contains no selection
            if line != endline or endcol:
                self.setSelection(line, 0, line, commentlen)
                if self.selectedText() == comment:
                    self.removeSelectedText()
                    if line == startline:
                        startcol -= 1
                    elif line == endline:
                        endcol -= 1
                else:
                    self.setCursorPosition(line, 0)
                    self.insert(comment)
                    if line == startline:
                        startcol += 1
                    elif line == endline:
                        endcol += 1
        # restore the currently selected text
        self.setSelection(startline, startcol, endline, endcol)
        self.endUndoAction()
        return True

    def copyFilenameToClipboard(self):
        QApplication.clipboard().setText(self._filename)

    def copyLineReference(self):
        from PyQt4.QtGui import QCursor

        sel = self.getSelection()
        # Note: getSelection is 0 based like all good code
        if sel[0] == -1 and self._clickPos:
            lines = (self.lineAt(self.mapFromGlobal(self._clickPos)) + 1, -1)
        else:
            end = sel[2]
            if sel[3] == 0:
                # if nothing is selected on the last line, exclude it
                end -= 1
            lines = (sel[0] + 1, end + 1)
        args = {'filename': self.filename(), 'plural': ''}
        if lines[1] == -1 or lines[0] == lines[1]:
            args['line'] = lines[0]
        else:
            args['line'] = '{}-{}'.format(*lines)
            args['plural'] = 's'
        QApplication.clipboard().setText(
            '{filename}: Line{plural} {line}'.format(**args)
        )

    def copyLstrip(self):
        """Copy's the selected text, but strips off any leading whitespace shared by the entire selection.
        """
        start, s, end, e = self.getSelection()
        count = end - start + 1
        self.setSelection(start, 0, end, e)
        text = unicode(self.selectedText())
        while len(re.findall(r'^\W', text, flags=re.M)) == count:
            text = re.sub(r'^\W', '', unicode(text), flags=re.M)
        QApplication.clipboard().setText(text)

    def colorScheme(self):
        """ Pulls the current color settings from the DocumentEditor and returns them as a dict.
        
        This dict contains diffrent color types, color(foreground), paper(background), defaultPaper,
        etc, these contain lists of colors for each color enum, or a color definition if no enum is 
        used. A color def is a list of r,g,b,alpha values that can be passed as args to QColor.
        
        returns:
            A dict of color settings
        """
        # See the index number definitions here
        # http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciLexerPython.html#a9091a6d7c7327b004480ebaa130c1c18ac55b65493dace8925090544c401e8556
        lex = self.lexer()
        # Get the current colors from the proper implementaton
        ret = {}
        ret['paper'] = dict(
            [(i, lex.paper(i).getRgb()) for i in range(lex.Decorator + 1)]
        )
        ret['color'] = dict(
            [(i, lex.color(i).getRgb()) for i in range(lex.Decorator + 1)]
        )
        # For some reason this takes a index, but the setter doesn't
        ret['defaultPaper'] = lex.defaultPaper(0).getRgb()
        ret['marginsForeground'] = self.marginsForegroundColor().getRgb()
        ret['marginsBackground'] = self.marginsBackgroundColor().getRgb()
        foldMarginColors = self.foldMarginColors()
        ret['foldMarginsForeground'] = foldMarginColors[0].getRgb()
        ret['foldMarginsBackground'] = foldMarginColors[1].getRgb()
        ret['caretBackgroundColor'] = self.caretBackgroundColor().getRgb()
        ret['caretForegroundColor'] = self.caretForegroundColor().getRgb()
        return ret

    def setColorScheme(self, colors):
        """ Sets the DocumentEditor's lexer colors, see colorScheme for a compatible dict """
        # See the index number definitions here
        # http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciLexerPython.html#a9091a6d7c7327b004480ebaa130c1c18ac55b65493dace8925090544c401e8556
        lex = self.lexer()
        for key, value in colors['paper'].iteritems():
            lex.setPaper(QColor(*value), int(key))
        for key, value in colors['color'].iteritems():
            lex.setColor(QColor(*value), int(key))
        lex.setDefaultPaper(QColor(*colors['defaultPaper']))
        if 'marginsBackground' in colors:
            self.setMarginsBackgroundColor(QColor(*colors['marginsBackground']))
        if 'marginsForeground' in colors:
            self.setMarginsForegroundColor(QColor(*colors['marginsForeground']))
        if 'foldMarginsBackground' in colors and 'foldMarginsForeground' in colors:
            self.setFoldMarginColors(
                QColor(*colors['foldMarginsForeground']),
                QColor(*colors['foldMarginsBackground']),
            )
        if 'caretForegroundColor' in colors:
            self.setCaretForegroundColor(QColor(*colors['caretForegroundColor']))
        if 'caretBackgroundColor' in colors:
            self.setCaretLineBackgroundColor(QColor(*colors['caretBackgroundColor']))

    def detectEndLine(self, text):
        newlineN = text.indexOf('\n')
        newlineR = text.indexOf('\r')
        if newlineN != -1 and newlineR != -1:
            if newlineN == newlineR + 1:
                # CR LF Windows
                return self.EolWindows
            elif newlineR == newlineN + 1:
                # LF CR ACorn and RISC unsuported
                return self.eolMode()
        if newlineN != -1 and newlineR != -1:
            if newlineN < newlineR:
                # First return is a LF
                return self.EolUnix
            else:
                # first return is a CR
                return self.EolMac
        if newlineN != -1:
            return self.EolUnix
        return self.EolMac

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

    def disableTitleUpdate(self):
        self.SCN_MODIFIED.disconnect(self.refreshTitle)

    def enableTitleUpdate(self):
        self.SCN_MODIFIED.connect(self.refreshTitle)

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
            window.searchFileDialog().setSearchText(self.selectedText())
            window.uiFindInFilesACT.triggered.emit(False)

    def findInFilesPath(self):
        path = self._filename
        if os.path.isfile(path):
            path = os.path.split(path)[0]

        window = self.window()
        if isinstance(window, IdeEditor):
            if os.path.exists(path):
                window.searchFileDialog().setBasePath(path)
            window.uiFindInFilesACT.triggered.emit(False)

    def foldMarginColors(self):
        """ Returns the fold margin's foreground and background QColor
        
        Returns:
            foreground(QColor): The foreground color
            background(QColor): The background color
        """
        return self._foldMarginForegroundColor, self._foldMarginBackgroundColor

    def setFoldMarginColors(self, foreground, background):
        """ Sets the fold margins foreground and background QColor
        
        Args:
            foreground(QColor): The forground color of the checkerboard
            background(QColor): The background color of the checkerboard
        """
        self._foldMarginForegroundColor = foreground
        self._foldMarginBackgroundColor = background
        super(DocumentEditor, self).setFoldMarginColors(foreground, background)

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
            text = f.readAll()
            self._textCodec = QTextCodec.codecForUtfText(
                text, QTextCodec.codecForName('System')
            )
            self.setText(self._textCodec.toUnicode(text))
            f.close()
            self.updateFilename(filename)
            self.enableFileWatching(True)
            self.setEolMode(self.detectEndLine(self.text()))
            return True
        return False

    def filename(self):
        return self._filename

    def findNext(self, text, flags):
        re = (flags & self.SearchOptions.QRegExp) != 0
        cs = (flags & self.SearchOptions.CaseSensitive) != 0
        wo = (flags & self.SearchOptions.WholeWords) != 0
        wrap = True
        forward = True

        result = self.findFirst(text, re, cs, wo, wrap, forward)

        if not result:
            self.findTextNotFound(text)

        return result

    def findPrev(self, text, flags):
        re = (flags & self.SearchOptions.QRegExp) != 0
        cs = (flags & self.SearchOptions.CaseSensitive) != 0
        wo = (flags & self.SearchOptions.WholeWords) != 0
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
        self.setShowSmartHighlighting(section.value('smartHighlighting'))

        if section.value('showLimitColumn'):
            self.setEdgeMode(self.EdgeLine)
            self.setEdgeColumn(section.value('limitColumn'))
        else:
            self.setEdgeMode(self.EdgeNone)

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
                    if key == 'smarthighlight':
                        # The ini parser in language.lexerColorTypes lowercasses the keys
                        # but scheme expects the original names.
                        key = 'smartHighlight'
                    clr = scheme.value('document_color_%s' % key)
                    if not clr:
                        continue

                    bgclr = scheme.value('document_color_%sBackground' % key)
                    if not bgclr:
                        bgclr = default_bg

                    for value in values:
                        lexer.setColor(clr, value)
                        lexer.setPaper(bgclr, value)

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

    def marginsBackgroundColor(self):
        return self._marginsBackgroundColor

    def marginsForegroundColor(self):
        return self._marginsForegroundColor

    def setMarginsBackgroundColor(self, color):
        self._marginsBackgroundColor = color
        super(DocumentEditor, self).setMarginsBackgroundColor(color)

    def setMarginsForegroundColor(self, color):
        self._marginsForegroundColor = color
        super(DocumentEditor, self).setMarginsForegroundColor(color)

    def markerNext(self):
        line, index = self.getCursorPosition()
        newline = self.markerFindNext(line + 1, self.marginMarkerMask(1))

        # wrap around the document if necessary
        if newline == -1:
            newline = self.markerFindNext(0, self.marginMarkerMask(1))

        self.setCursorPosition(newline, index)

    def markerLoad(self, input):
        r"""
            \remarks	Takes a list of line numbers and adds a marker to each of them in the file.
        """
        for line in input:
            marker = self.markerDefine(self.Circle)
            self.markerAdd(line, marker)

    def markerToggle(self):
        line, index = self.getCursorPosition()
        markers = self.markersAtLine(line)
        if not markers:
            marker = self.markerDefine(self.Circle)
            self.markerAdd(line, marker)
        else:
            self.markerDelete(line)
        # update the dictionary that stores the document markers when the ide is closed.
        window = self.window()
        if isinstance(window, IdeEditor):
            if self._filename in window.documentMarkrerDict:
                if line in window.documentMarkrerDict[self._filename]:
                    window.documentMarkrerDict[self._filename].remove(line)
                else:
                    window.documentMarkrerDict[self._filename].append(line)
            else:
                window.documentMarkrerDict[self._filename] = [line]

    def marginsFont(self):
        return self._marginsFont

    def paste(self):
        text = QApplication.clipboard().text()
        if text.indexOf('\n') == -1 and text.indexOf('\r') == -1:
            return super(DocumentEditor, self).paste()

        def repForMode(mode):
            if mode == self.EolWindows:
                return '\r\n'
            elif mode == self.EolUnix:
                return '\n'
            else:
                return '\r'

        text = text.replace(
            repForMode(self.detectEndLine(text)), repForMode(self.eolMode())
        )
        QApplication.clipboard().setText(text)
        return super(DocumentEditor, self).paste()

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
        debugMsg(
            'Reload Change called: %0.3f Dialog Shown: %r'
            % (self._saveTimer, self._dialogShown),
            DebugLevel.High,
        )
        if time.time() - self._saveTimer < 0.25:
            # If we are saving no need to reload the file
            debugMsg('timer has not expired', DebugLevel.High)
            return False
        if not os.path.isfile(self.filename()) and not self._dialogShown:
            debugMsg('The file was deleted', DebugLevel.High)
            # the file was deleted, ask the user if they still want to keep the file in the editor.
            self._dialogShown = True
            result = QMessageBox.question(
                self.window(),
                'File Removed...',
                'File: %s has been deleted.\nKeep file in editor?' % self.filename(),
                QMessageBox.Yes,
                QMessageBox.No,
            )
            self._dialogShown = False
            if result == QMessageBox.No:
                debugMsg(
                    'The file was deleted, removing document from editor',
                    DebugLevel.High,
                )
                self.parent().close()
                return False
            # TODO: The file no longer exists, and the document should be marked as changed.
            debugMsg(
                'The file was deleted, But the user left it in the editor',
                DebugLevel.High,
            )
            self.enableFileWatching(False)
            return True
        debugMsg('Defaulting to reload message', DebugLevel.High)
        return self.reloadDialog(
            'File: %s has been changed.\nReload from disk?' % self.filename()
        )

    def reloadDialog(self, message, title='Reload File...'):
        if not self._dialogShown:
            self._dialogShown = True
            if self._autoReloadOnChange or not self.isModified():
                result = QMessageBox.Yes
            else:
                result = QMessageBox.question(
                    self.window(), title, message, QMessageBox.Yes | QMessageBox.No
                )
            self._dialogShown = False
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

        self.beginUndoAction()
        sel = self.getSelection()

        # replace all of the instances of the text
        if all:
            count = self.text().count(searchtext, Qt.CaseInsensitive)
            found = 0
            while self.findFirst(searchtext, False, False, False, True, True):
                if found == count:
                    # replaced all items, exit so we don't get a infinite loop
                    break
                found += 1
                super(DocumentEditor, self).replace(text)

        # replace a single instance of the text
        else:
            count = 1
            super(DocumentEditor, self).replace(text)

        self.setSelection(*sel)
        self.endUndoAction()

        return count

    def refreshTitle(self):
        try:
            parent = self.parent()
            if parent and parent.inherits('QMdiSubWindow'):
                parent.setWindowTitle(self.windowTitle())
        except RuntimeError:
            pass

    def save(self):
        debugMsg(
            '------------------------------ Save Called ------------------------------ ',
            DebugLevel.High,
        )
        return self.saveAs(self.filename())

    def saveAs(self, filename=''):
        debugMsg(
            '------------------------------ Save As Called ------------------------------ ',
            DebugLevel.High,
        )
        newFile = False
        if not filename:
            newFile = True
            filename = self.filename()
            if not filename:
                window = self.window()
                if isinstance(window, IdeEditor):
                    if window.lastSavedFilename():
                        filename = os.path.split(window.lastSavedFilename())[0]
            filename = QFileDialog.getSaveFileName(
                self.window(), 'Save File as...', filename
            )

        if filename:
            self._saveTimer = time.time()
            # save the file to disk
            f = QFile(filename)
            f.open(QFile.WriteOnly)
            # make sure the file is writeable
            if f.error() != QFile.NoError:
                debugMsg('An error occured while saving', DebugLevel.High)
                QMessageBox.question(
                    self.window(),
                    'Error saving file...',
                    'There was a error saving the file. Error Code: %i' % f.error(),
                    QMessageBox.Ok,
                )
                f.close()
                return False
            # Attempt to save the file using the same codec that it used to display it
            if self._textCodec:
                f.write(self._textCodec.fromUnicode(self.text()))
            else:
                self.write(f)
            f.close()
            # notify that the document was saved
            self.documentSaved.emit(self, filename)

            # update the file
            self.updateFilename(filename)
            if newFile:
                self.enableFileWatching(True)
            return True
        return False

    def selectProjectItem(self):
        window = self.window()
        if window:
            window.selectProjectItem(self.filename())

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

        # connect the lexer if possible
        self.setShowSmartHighlighting(self._showSmartHighlighting)

        # set the lexer & init the settings
        self.setLexer(lexer)
        self.initSettings()

    def setLexer(self, lexer):
        super(DocumentEditor, self).setLexer(lexer)
        # QSciLexer.wordCharacters is not virtual, or even exposed. This hack allows custom lexers
        # to define their own wordCharacters
        if hasattr(lexer, 'wordCharactersOverride'):
            wordCharacters = lexer.wordCharactersOverride
        else:
            # We can't query the lexer for its word characters, but we can query the document.
            # This ensures the lexer's wordCharacters are used if switching from a wordCharactersOverride
            # lexer to a lexer that doesn't define custom wordCharacters.
            wordCharacters = self.wordCharacters()
        self.SendScintilla(self.SCI_SETWORDCHARS, wordCharacters)

    def setLineMarginWidth(self, width):
        self.setMarginWidth(self.SymbolMargin, width)

    def setMarginsFont(self, font):
        super(DocumentEditor, self).setMarginsFont(font)
        self._marginsFont = font

    def setSmartHighlightingRegEx(
        self, exp='[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>\']'
    ):
        r"""
            \remarks	Set the regular expression used to control if a selection is considered valid for
                        smart highlighting.
            \param		exp		<str>	Default:'[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>]'
        """
        self._smartHighlightingRegEx = exp
        self.selectionValidator = re.compile(exp)

    def setShowFolding(self, state):
        if state:
            self.setFolding(self.BoxedTreeFoldStyle)
        else:
            self.setFolding(self.NoFoldStyle)

    def setShowLineNumbers(self, state):
        self.setMarginLineNumbers(self.SymbolMargin, state)

    def setShowSmartHighlighting(self, state):
        self._showSmartHighlighting = state
        # Disconnect existing connections
        try:
            self.selectionChanged.disconnect(self.updateHighlighter)
        except:
            pass
        # connect to signal if enabling and possible
        if hasattr(self.lexer(), 'highlightedKeywords'):
            if state:
                self.selectionChanged.connect(self.updateHighlighter)
            else:
                lexer = self.lexer()
                self.setHighlightedKeywords(self.lexer(), '')

    def setShowWhitespaces(self, state):
        if state:
            self.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.setWhitespaceVisibility(QsciScintilla.WsInvisible)

    def showMenu(self):
        import blurdev
        from PyQt4.QtGui import QMenu, QCursor, QIcon

        menu = QMenu(self)
        self._clickPos = QCursor.pos()

        act = menu.addAction('Find in Files...')
        act.triggered.connect(self.findInFiles)
        # act.setShortcut('Ctrl+Alt+F')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/folder_find.png')))
        act = menu.addAction('Goto')
        # act.setShortcut('Ctrl+G')
        act.triggered.connect(self.goToLine)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto.png')))
        act = menu.addAction('Go to Definition')
        # act.setShortcut('Ctrl+Shift+G')
        act.triggered.connect(self.goToDefinition)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/goto_def.png')))

        menu.addSeparator()

        act = menu.addAction('Collapse/Expand All')
        act.triggered.connect(self.toggleFolding)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/plus_minus.png')))

        menu.addSeparator()

        act = menu.addAction('Cut')
        act.triggered.connect(self.cut)
        act.setShortcut('Ctrl+X')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/cut.png')))

        act = menu.addAction('Copy')
        act.triggered.connect(self.copy)
        act.setShortcut('Ctrl+C')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        act = menu.addAction('Copy lstrip')
        act.triggered.connect(self.copyLstrip)
        act.setShortcut('Ctrl+Shift+C')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        act = menu.addAction('Paste')
        act.triggered.connect(self.paste)
        act.setShortcut('Ctrl+V')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/paste.png')))

        menu.addSeparator()

        act = menu.addAction('Copy Line Reference')
        act.triggered.connect(self.copyLineReference)
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/copy.png')))

        menu.addSeparator()

        act = menu.addAction('Comment Add')
        act.triggered.connect(self.commentAdd)
        act.setShortcut("Alt+3")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_add.png')))
        act = menu.addAction('Comment Remove')
        act.triggered.connect(self.commentRemove)
        act.setShortcut("Alt+#")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_remove.png')))
        act = menu.addAction('Comment Toggle')
        act.triggered.connect(self.commentToggle)
        act.setShortcut("Ctrl+Alt+3")
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/comment_toggle.png')))

        menu.addSeparator()

        act = menu.addAction('To Lowercase')
        act.triggered.connect(self.toLower)
        # act.setShortcut('Ctrl+L')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/lowercase.png')))
        act = menu.addAction('To Uppercase')
        act.triggered.connect(self.toUpper)
        # act.setShortcut('Ctrl+U')
        act.setIcon(QIcon(blurdev.resourcePath('img/ide/uppercase.png')))

        menu.addSeparator()

        submenu = menu.addMenu('View as...')
        submenu.setIcon(QIcon(blurdev.resourcePath('img/ide/view_as.png')))
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

        menu.addSeparator()

        act = menu.addAction('Indent using tabs')
        act.triggered.connect(self.setIndentationsUseTabs)
        act.setCheckable(True)
        act.setChecked(self.indentationsUseTabs())

        if self._fileMonitoringActive:
            act = menu.addAction('Auto Reload file')
            act.triggered.connect(self.setAutoReloadOnChange)
            act.setCheckable(True)
            act.setChecked(self._autoReloadOnChange)

        if self.language() == 'Python':
            menu.addSeparator()
            act = menu.addAction('Autoformat (PEP 8)')
            act.triggered.connect(self.autoFormat)
            act.setIcon(QIcon(blurdev.resourcePath('img/ide/python.png')))

        menu.popup(self._clickPos)

    def showFolding(self):
        return self.folding() != self.NoFoldStyle

    def showLineNumbers(self):
        return self.marginLineNumbers(self.SymbolMargin)

    def showSmartHighlighting(self):
        return self._showSmartHighlighting

    def showWhitespaces(self):
        return self.whitespaceVisibility() == QsciScintilla.WsVisible

    def smartHighlightingRegEx(self):
        return self._smartHighlightingRegEx

    def toLower(self):
        self.beginUndoAction()
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        text = self.selectedText().toLower()
        self.removeSelectedText()
        self.insert(text)
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

    def toggleFolding(self):
        from PyQt4.QtGui import QApplication
        from PyQt4.QtCore import Qt

        self.foldAll(QApplication.instance().keyboardModifiers() == Qt.ShiftModifier)

    def toUpper(self):
        self.beginUndoAction()
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        text = self.selectedText().toUpper()
        self.removeSelectedText()
        self.insert(text)
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

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
        self._filename = os.path.abspath(filename)
        self.setModified(False)

        try:
            self.window().emitDocumentTitleChanged()
        except:
            pass

        self.refreshTitle()

    def updateHighlighter(self):
        # Get selection
        selectedText = self.selectedText()
        # if text is selected make sure it is a word
        lexer = self.lexer()
        if selectedText != lexer.highlightedKeywords:
            if selectedText:
                validator = self.selectionValidator
                if hasattr(self.lexer(), 'selectionValidator'):
                    # If a lexer has defined its own selectionValidator use that instead
                    validator = self.lexer().selectionValidator
                # Does the text contain a non allowed word?
                if not validator.findall(selectedText) == []:
                    return
                else:
                    selection = self.getSelection()
                    # the character before and after the selection must not be a word.
                    text = self.text(selection[2])  # Character after
                    if selection[3] < len(text):
                        if validator.findall(text[selection[3]]) == []:
                            return
                    text = self.text(selection[0])  # Character Before
                    if selection[1] and selection[1] != -1:
                        if validator.findall(text[selection[1] - 1]) == []:
                            return
            # Make the lexer highlight words
            self.setHighlightedKeywords(lexer, selectedText)

    def updateSelectionInfo(self):
        window = self.window()
        if window and hasattr(window, 'uiCursorInfoLBL'):
            sline, spos, eline, epos = self.getSelection()
            # Add 1 to line numbers because document line numbers are 1 based
            text = ''
            if sline == -1:
                line, pos = self.getCursorPosition()
                line += 1
                text = 'Line: {} Pos: {}'.format(line, pos)
            else:
                sline += 1
                eline += 1
                text = 'Line: {sline} Pos: {spos} To Line: {eline} Pos: {epos} Line Count: {lineCount}'.format(
                    sline=sline,
                    spos=spos,
                    eline=eline,
                    epos=epos,
                    lineCount=eline - sline + 1,
                )
            if self._textCodec and self._textCodec.name() != 'System':
                text = 'Encoding: {enc} {text}'.format(
                    enc=self._textCodec.name(), text=text
                )
            window.uiCursorInfoLBL.setText(text)

    def setAutoReloadOnChange(self, state):
        self._autoReloadOnChange = state

    def setHighlightedKeywords(self, lexer, keywords):
        """
            :remarks	Updates the lexers highlighted keywords
            :param		lexer		<QSciLexer>	Update this lexer and set as the lexer on the document.
            :param		keywords	<str>	keywords to highlight
        """

        lexer.highlightedKeywords = keywords
        marginFont = self.marginsFont()
        foldMarginColors = self.foldMarginColors()
        marginBackground = self.marginsBackgroundColor()
        marginForeground = self.marginsForegroundColor()
        # 		folds = self.contractedFolds()
        self.setLexer(lexer)
        # 		self.setContractedFolds(folds)
        self.setMarginsFont(marginFont)
        self.setMarginsBackgroundColor(marginBackground)
        self.setMarginsForegroundColor(marginForeground)
        self.setFoldMarginColors(*foldMarginColors)

    def indentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        self.beginUndoAction()
        for line in range(lineFrom, lineTo + 1):
            self.indent(line)
        self.endUndoAction()

    def unindentSelection(self, all=False):
        if all:
            lineFrom = 0
            lineTo = self.lines()
        else:
            lineFrom, indexFrom, lineTo, indextTo = self.getSelection()
        self.beginUndoAction()
        for line in range(lineFrom, lineTo + 1):
            self.unindent(line)
        self.endUndoAction()

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
    pyShowSmartHighlighting = pyqtProperty(
        "bool", showSmartHighlighting, setShowSmartHighlighting
    )
    pySmartHighlightingRegEx = pyqtProperty(
        "QString", smartHighlightingRegEx, setSmartHighlightingRegEx
    )

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
