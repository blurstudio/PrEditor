##
# 	\namespace	blurdev.gui.windows.loggerwindow.loggerwindow
#
# 	\remarks	LoggerWindow class is an overloaded python interpreter for blurdev
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/15/08
#

from PyQt4.QtCore import QObject
from PyQt4.QtGui import QTextEdit

# ----------------------------------------------------------------


class ErrorLog(QObject):
    def flush(self):
        """ flush the logger instance """
        self.parent().flush()

    def write(self, msg):
        """ log an error message """
        self.parent().write(msg, error=True)


# ----------------------------------------------------------------


class ConsoleEdit(QTextEdit):
    def __init__(self, parent):
        QTextEdit.__init__(self, parent)

        # store the error buffer
        self._completer = None
        self._errorBuffer = []
        self._errorId = 0

        # create the completer
        from completer import PythonCompleter

        self.setCompleter(PythonCompleter(self))

        # overload the sys logger (if we are not on a high debugging level)
        import sys

        sys.stdout = self
        sys.stderr = ErrorLog(self)

        # create the highlighter
        from blurdev.gui.highlighter import Highlighter

        highlight = Highlighter(self)

        self.startInputLine()

    def clear(self):
        """ clears the text in the editor """
        QTextEdit.clear(self)
        self._errorBuffer = []
        self.startInputLine()

    def completer(self):
        """ returns the completer instance that is associated with this editor """
        return self._completer

    def errorTimeout(self):
        """ end the error lookup """
        self._timer.stop()

    def executeCommand(self):
        """ executes the current line of code """
        import re

        # grab the command from the line
        block = self.textCursor().block().text()
        results = re.search('>>> (.*)', str(block))

        if results:
            # if the cursor position is at the end of the line
            if self.textCursor().atEnd():
                # insert a new line
                self.insertPlainText('\n')

                # evaluate the command
                cmdresult = None
                try:
                    cmdresult = eval(str(results.groups()[0]))
                except:
                    exec (str(results.groups()[0])) in globals()

                # print the resulting commands
                if cmdresult != None:
                    self.write(str(cmdresult))

                self.startInputLine()

            # otherwise, move the command to the end of the line
            else:
                self.startInputLine()
                self.insertPlainText(str(results.groups()[0]))

        # if no command, then start a new line
        else:
            self.startInputLine()

    def focusInEvent(self, event):
        """ overload the focus in event to ensure the completer has the proper widget """
        if self.completer():
            self.completer().setWidget(self)
        QTextEdit.focusInEvent(self, event)

    def insertCompletion(self, completion):
        """ inserts the completion text into the editor """
        if self.completer().widget() == self:
            from PyQt4.QtGui import QTextCursor

            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Left)
            cursor.movePosition(QTextCursor.EndOfWord)
            cursor.insertText(completion[len(self.completer().completionPrefix()) :])
            self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        """ overload the key press event to handle custom events """

        from PyQt4.QtCore import Qt

        # enter || return keys will execute the command
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.completer().popup().isVisible():
                self.completer().popup().hide()
                event.ignore()
            else:
                self.executeCommand()

        # home key will move the cursor to home
        elif event.key() == Qt.Key_Home:
            self.moveToHome()

        # otherwise, ignore the event for completion events
        elif event.key() in (Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
            event.ignore()

        # other wise handle the keypress
        else:
            QTextEdit.keyPressEvent(self, event)

            # check for particular events for the completion
            if self.completer() and not (event.modifiers() and event.text().isEmpty()):
                self.completer().refreshList(scope=globals())
                self.completer().popup().setCurrentIndex(
                    self.completer().completionModel().index(0, 0)
                )

            rect = self.cursorRect()
            rect.setWidth(
                self.completer().popup().sizeHintForColumn(0)
                + self.completer().popup().verticalScrollBar().sizeHint().width()
            )
            self.completer().complete(rect)

    def moveToHome(self):
        """ moves the cursor to the home location """
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QTextCursor, QApplication

        mode = QTextCursor.MoveAnchor

        # select the home
        if QApplication.instance().keyboardModifiers() == Qt.ShiftModifier:
            mode = QTextCursor.KeepAnchor

        # grab the cursor
        cursor = self.textCursor()
        block = str(cursor.block().text()).split()
        cursor.movePosition(QTextCursor.StartOfBlock, mode)
        cursor.movePosition(
            QTextCursor.Right, mode, 4
        )  # the line is 4 characters long (>>> )
        self.setTextCursor(cursor)

    def setCompleter(self, completer):
        """ sets the completer instance for this widget """
        if completer:
            self._completer = completer
            completer.setWidget(self)
            completer.activated.connect(self.insertCompletion)

    def startInputLine(self):
        """ create a new command prompt line """
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QTextCursor
        from PyQt4.QtGui import QTextCharFormat

        self.moveCursor(QTextCursor.End)

        # if this is not already a new line
        if self.textCursor().block().text() != '>>> ':
            charFormat = QTextCharFormat()
            charFormat.setForeground(Qt.black)
            self.setCurrentCharFormat(charFormat)

            inputstr = '>>> '
            if str(self.textCursor().block().text()):
                inputstr = '\n' + inputstr

            self.insertPlainText(inputstr)

    def timerEvent(self, event):
        """ kill the error event """
        self.killTimer(self._errorId)

    def write(self, msg, error=False):
        """ write the message to the logger """
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QTextCharFormat
        from PyQt4.QtGui import QTextCursor

        self.moveCursor(QTextCursor.End)
        charFormat = QTextCharFormat()

        if not error:
            charFormat.setForeground(Qt.blue)
        else:
            # start recording information to the error buffer
            if not self._errorBuffer:
                self._errorId = self.startTimer(1000)

            charFormat.setForeground(Qt.red)
            self._errorBuffer.append(msg)

        self.setCurrentCharFormat(charFormat)
        self.insertPlainText(msg)
