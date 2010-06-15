##
# 	\namespace	blurdev.gui.windows.scriptwindow.scriptwindow
#
# 	\remarks	Creates a basic script editing window for the blurdev application
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/19/10
#

from blurdev.gui import Window

# -------------------------------------------------------------------------------------------------------------


class ScriptWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # create the code highlighter
        from blurdev.gui.highlighters.codehighlighter import CodeHighlighter

        highlighter = CodeHighlighter(self.uiCodeTXT)
        highlighter.setLanguage('Python')

        self._dirty = False
        self._fileName = None

        # create a key press helper
        from PyQt4.QtCore import QEvent
        from blurdev.gui.helpers.widgeteventhelper import WidgetEventHelper

        helper = WidgetEventHelper(self.uiCodeTXT)
        helper.eventConnect(QEvent.KeyPress, self.handleKeyPress)

        from PyQt4.QtGui import QFont

        self.uiCodeTXT.setFont(QFont('Courier New', 8))

        self.viewLineNumbers()

        self._connect()
        self.updateTitle()

    def _connect(self):
        from PyQt4.QtCore import SIGNAL

        self.connect(self.uiEvaluateACT, SIGNAL('triggered()'), self.runScript)
        self.connect(self.uiNewACT, SIGNAL('triggered()'), self.newScript)
        self.connect(self.uiSaveACT, SIGNAL('triggered()'), self.saveScript)
        self.connect(self.uiSaveAsACT, SIGNAL('triggered()'), self.saveScriptAs)
        self.connect(self.uiOpenACT, SIGNAL('triggered()'), self.openScript)
        self.connect(self.uiCloseACT, SIGNAL('triggered()'), self.close)

        self.connect(self.uiCodeTXT, SIGNAL('textChanged()'), self.setDirty)
        self.connect(
            self.uiCodeTXT, SIGNAL('cursorPositionChanged()'), self.updateStatus
        )

        self.connect(self.uiLineNumbersACT, SIGNAL('triggered()'), self.viewLineNumbers)

    def closeEvent(self, event):
        if self.clean():
            event.accept()
        else:
            event.ignore()

    def clean(self):
        success = True

        if self.isDirty():
            import blurdev.api

            if not blurdev.api.flags.flag('silent'):
                from PyQt4.QtGui import QMessageBox

                result = QMessageBox.question(
                    self,
                    'File is not Updated',
                    'Would you like to save your changes before closing?',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                )

                if result == QMessageBox.Yes:
                    self.saveScript()

                elif result == QMessageBox.Cancel:
                    success = False

        return success

    def isDirty(self):
        return self._dirty

    def handleKeyPress(self, object, event):
        from PyQt4.QtCore import Qt

        # Ctrl+S - Save
        if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            self.saveScript()

        # Ctrl+Shift+S - Save as
        elif event.key() == Qt.Key_S and event.modifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self.saveScript('')

        # Ctrl+O
        elif event.key() == Qt.Key_O and event.modifiers() == Qt.ControlModifier:
            self.openScript()

        # Ctrl+N
        elif event.key() == Qt.Key_N and event.modifiers() == Qt.ControlModifier:
            self.newScript()

        # Ctrl+E
        elif event.key() == Qt.Key_E and event.modifiers() == Qt.ControlModifier:
            self.runScript()

        else:
            from PyQt4.QtGui import QTextEdit

            QTextEdit.keyPressEvent(self.uiCodeTXT, event)

            # Match the indent
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                lastText = str(self.uiCodeTXT.textCursor().block().previous().text())
                import re

                indent = re.match('[ \t]*', lastText).group()

                if lastText.endswith(':'):
                    indent += '\t'

                self.uiCodeTXT.textCursor().insertText(indent)

        return True

    def openScript(self, fileName=None):
        if self.clean():
            import blurdev.gui

            if fileName == None:
                fileName = blurdev.gui.getOpenFileName(
                    caption='Open script file...',
                    filters='Python Script (*.py);;All Files (*.*)',
                )

            import os.path

            if fileName and os.path.exists(fileName):
                self._fileName = fileName

                file = open(fileName, 'r')
                self.uiCodeTXT.setText(file.read())
                file.close()

                self.setDirty(False)

    def newScript(self):
        if self.clean():
            self.uiCodeTXT.setText('')
            self._fileName = None
            self.setDirty(False)
            self.updateTitle()

    def runScript(self):
        import blurdev

        # Execute the string command
        exec str(self.uiCodeTXT.toPlainText()) in {
            '__file__': self._fileName,
            'blurdev': blurdev,
        }

    def saveScript(self, fileName=None):
        if fileName == None:
            fileName = self._fileName

        import blurdev.api

        if not (fileName or blurdev.api.flags.flag('silent')):
            fileName = blurdev.gui.getSaveFileName(
                caption='Save file as...',
                filters='Python Script (*.py);;All Files (*.*)',
            )

        import os.path

        if fileName and os.path.exists(os.path.split(fileName)[0]):
            self._fileName = fileName

            file = open(fileName, 'w')
            file.write(self.uiCodeTXT.toPlainText())
            file.close()

            self.setDirty(False)

    def saveScriptAs(self):
        self.saveScript('')

    def setDirty(self, state=True):
        self._dirty = state
        self.updateTitle()

    def viewLineNumbers(self):
        if self.uiLineNumbersACT.isChecked():
            self.uiLineNumbersTXT.show()
        else:
            self.uiLineNumbersTXT.hide()

    def updateStatus(self):
        from PyQt4.QtCore import QString

        cursor = self.uiCodeTXT.textCursor()
        msg = (
            QString("pos = ")
            + QString().setNum(cursor.position())
            + QString(" | line = ")
            + QString().setNum(cursor.blockNumber())
            + QString(" | col = ")
            + QString().setNum(cursor.columnNumber())
        )
        self.uiStatusBar.showMessage(msg)

    def updateTitle(self):
        title = 'Untitled'
        if self._fileName:
            title = self._fileName

        if self.isDirty():
            title += ' *'
        title += ' - Script Editor'
        self.setWindowTitle(title)

    @staticmethod
    def newScript():
        """
            \remarks	creates a new script window
        """
        import blurdev.api

        window = ScriptWindow(blurdev.api.core.activeWindow())
        window.show()

    @staticmethod
    def loadScript(fileName=None):
        """
            \remarks	loads the inputed file in a new script window
            \param		fileName	<str> || <QString> || None
        """
        import blurdev.api, blurdev.gui

        if not fileName:
            fileName = blurdev.gui.getOpenFileName(
                'Select Script File', filters='Python Files (*.py);;All Files (*.*)'
            )

        if fileName:
            window = ScriptWindow(blurdev.api.core.activeWindow())
            window.openScript(fileName)
            window.show()
