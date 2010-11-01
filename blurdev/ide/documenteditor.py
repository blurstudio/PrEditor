##
# 	\namespace	blurdev.ide.documenteditor
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtCore import pyqtProperty
from PyQt4.Qsci import *


class DocumentEditor(QsciScintilla):
    def __init__(self, parent, filename=''):
        QsciScintilla.__init__(self, parent)

        # create custom properties
        self._filename = ''
        self._language = ''
        self._lastSearch = ''
        self._lastSearchBackward = False

        # initialize the look of the system
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QFont, QFontMetrics, QColor

        font = QFont()
        font.setFamily('Courier New')
        font.setFixedPitch(True)
        font.setPointSize(9)

        # set the font information
        self.setFont(font)
        mfont = QFont(font)
        mfont.setPointSize(7)
        self.setMarginsFont(mfont)

        # set the margin information
        self.setMarginWidth(0, QFontMetrics(mfont).width('00000') + 5)
        self.setMarginLineNumbers(0, True)
        self.setAutoIndent(True)  # automatically match line indentations on new lines
        self.setAutoCompletionSource(QsciScintilla.AcsAll)

        # set code folding options
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)

        # set brace matching
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)

        # set editing line color
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(Qt.white))

        # set margin colors
        self.setMarginsBackgroundColor(QColor(Qt.lightGray))
        self.setMarginsForegroundColor(QColor(Qt.gray))
        self.setFoldMarginColors(QColor(Qt.yellow), QColor(Qt.blue))

        # create the connections
        self.textChanged.connect(self.refreshTitle)

        # load the file
        if filename:
            self.load(filename)
        else:
            self.refreshTitle()

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

    def language(self):
        return self._language

    def lineMarginWidth(self):
        return self.marginWidth(self.SymbolMargin)

    def load(self, filename):
        import os.path

        filename = str(filename)
        if filename and os.path.exists(filename):
            self.setText(open(filename).read())

            self._filename = filename

            import lexers

            lexers.load()
            lexer = lexers.lexerFor(os.path.splitext(filename)[1])
            if lexer:
                lexer.setFont(self.font())
                self._language = lexers.languageFor(lexer)

            self.setLexer(lexer)
            self.refreshTitle()
            self.setModified(False)
            return True
        return False

    def filename(self):
        return self._filename

    def findNext(self, text, flags):
        from PyQt4.QtGui import QTextDocument

        if not (text == self._lastSearch and not self._lastSearchBackward):
            self._lastSearch = text
            self._lastSearchBackward = True
            re = False
            cs = (flags & QTextDocument.FindCaseSensitively) != 0
            wo = (flags & QTextDocument.FindWholeWords) != 0
            wrap = True
            forward = True

            self.findFirst(text, re, cs, wo, wrap, forward)
        else:
            QsciScintilla.findNext(self)

    def findPrev(self, text, flags):
        from PyQt4.QtGui import QTextDocument

        if not (text == self._lastSearch and self._lastSearchBackward):
            self._lastSearch = text
            self._lastSearchBackward = True
            re = False
            cs = (flags & QTextDocument.FindCaseSensitively) != 0
            wo = (flags & QTextDocument.FindWholeWords) != 0
            wrap = True
            forward = False

            self.findFirst(text, re, cs, wo, wrap, forward)
        else:
            QsciScintilla.findNext(self)

    def save(self):
        self.saveAs(self.filename())

    def saveAs(self, filename=''):
        if not filename:
            from PyQt4.QtGui import QFileDialog

            filename = QFileDialog.getSaveFileName(self.window(), 'Save File as...')

        if filename:
            f = open(str(filename), 'w')
            f.write(self.text())
            f.close()

            self._filename = filename
            self.setModified(False)
            self.window().documentTitleChanged.emit()
            self.refreshTitle()
            return True
        return False

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

    def setLanguage(self, language):
        self._language = language

        from blurdev.ide import lexers

        lexers.load()
        lexer = lexers.lexer(language)
        self.setLexer(lexer)

    def setLineMarginWidth(self, width):
        self.setMarginWidth(self.SymbolMargin, width)

    def setShowFolding(self, state):
        if state:
            self.setFolding(self.BoxedTreeFoldStyle)
        else:
            self.setFolding(self.NoFoldStyle)

    def setShowLineNumbers(self, state):
        self.setMarginLineNumbers(self.SymbolMargin, state)

    def showFolding(self):
        return self.folding() != self.NoFoldStyle

    def showLineNumbers(self):
        return self.marginLineNumbers(self.SymbolMargin)

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
