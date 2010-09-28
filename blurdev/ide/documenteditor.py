##
# 	\namespace	blurdev.ide.documenteditor
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.Qsci import *


class DocumentEditor(QsciScintilla):
    def __init__(self, parent, filename=''):
        QsciScintilla.__init__(self, parent)

        # create custom properties
        self._filename = ''

        # initialize the look of the system
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QFont, QFontMetrics, QColor

        font = QFont()
        font.setFamily('Courier New')
        font.setFixedPitch(True)
        font.setPointSize(10)

        # set the font information
        self.setFont(font)
        mfont = QFont(font)
        mfont.setPointSize(8)
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
            self.setLexer(lexer)
            self.refreshTitle()
            self.setModified(False)
            return True
        return False

    def filename(self):
        return self._filename

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
