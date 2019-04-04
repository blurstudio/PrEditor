""" LoggerWindow class is an overloaded python interpreter for blurdev

"""

from builtins import str as text
from future.utils import iteritems
import re
import __main__
import os
import sys
import sip
import time
import traceback

from Qt.QtCore import QDateTime, QObject, QPoint, Qt, Property
from Qt.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from Qt.QtWidgets import QAction, QApplication, QTextEdit

import blurdev
from blurdev import debug
from blurdev.debug import BlurExcepthook
from .completer import PythonCompleter
from blurdev.gui.highlighters.codehighlighter import CodeHighlighter
from blurdev.gui.windows.loggerwindow.errordialog import ErrorDialog
import blurdev.gui.windows.loggerwindow
from blurdev.contexts import ErrorReport


SafeOutput = None


class Win32ComFix(object):
    pass


# win32com's redirects all sys.stderr output to sys.stdout if the existing sys.stdout is not a instance of its SafeOutput
# Make our logger classes inherit from SafeOutput so they don't get replaced by win32com
# This is only neccissary for Softimage
if blurdev.core.objectName() == 'softimage':
    try:
        from win32com.axscript.client.framework import SafeOutput

        class Win32ComFix(SafeOutput):
            pass

    except ImportError:
        pass


class ErrorLog(QObject, Win32ComFix):
    def flush(self):
        """ flush the logger instance """
        pass

    def write(self, msg):
        """ log an error message """
        self.parent().write(msg, error=True)


class ConsoleEdit(QTextEdit, Win32ComFix):
    # Ensure the error prompt only shows up once.
    _errorPrompted = False
    # the color error messages are displayed in, can be set by stylesheets
    _errorMessageColor = QColor(Qt.red)

    def __init__(self, parent):
        QTextEdit.__init__(self, parent)

        # store the error buffer
        self._completer = None

        # create the completer
        self.setCompleter(PythonCompleter(self))

        # sys.__stdout__ doesn't work if some third party has implemented their
        # own override. Use these to backup the current logger so the logger displays output, but
        # application specific consoles also get the info.
        self.stdout = None
        self.stderr = None
        self._errorLog = None
        # overload the sys logger (if we are not on a high debugging level)
        if (
            os.path.basename(sys.executable) != 'python.exe'
            or debug.debugLevel() != debug.DebugLevel.High
        ):
            # Store the current outputs
            self.stdout = sys.stdout
            self.stderr = sys.stderr
            # insert our own outputs
            sys.stdout = self
            sys.stderr = ErrorLog(self)
            self._errorLog = sys.stderr
            BlurExcepthook.install()

        # create the highlighter
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')
        self.uiCodeHighlighter = highlight

        # If populated, also write to this interface
        self.outputPipe = None

        self._stdoutColor = QColor(17, 154, 255)
        self._commentColor = QColor(0, 206, 52)
        self._keywordColor = QColor(17, 154, 255)
        self._stringColor = QColor(255, 128, 0)
        self._resultColor = QColor(128, 128, 128)
        # These variables are used to enable pdb mode. This is a special mode used by the logger if
        # it is launched externally via getPdb, set_trace, or post_mortem in blurdev.debug.
        self._pdbPrompt = '(Pdb) '
        self._consolePrompt = '>>> '
        # Note: Changing _outputPrompt may require updating resource\lang\python.xml
        # If still using a #
        self._outputPrompt = '#Result: '
        self._pdbMode = False
        # if populated when setPdbMode is called, this action will be enabled and its check state
        # will match the current pdbMode.
        self.pdbModeAction = None
        # Method used to update the gui when pdb mode changes
        self.pdbUpdateVisibility = None
        # Method used to update the gui when code is executed
        self.reportExecutionTime = None

        self._firstShow = True

        # When executing code, that takes longer than this seconds, flash the window
        self.flashTime = 1.0

        self.uiClearToLastPromptACT = QAction('Clear to Last', self)
        self.uiClearToLastPromptACT.triggered.connect(self.clearToLastPrompt)
        self.uiClearToLastPromptACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_Backspace)
        self.addAction(self.uiClearToLastPromptACT)

    def clear(self):
        """ clears the text in the editor """
        QTextEdit.clear(self)
        self.startInputLine()

    def clearToLastPrompt(self):
        # store the current cursor position so we can restore when we are done
        currentCursor = self.textCursor()
        # move to the end of the document so we can search backwards
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)
        # Check if the last line is a empty prompt. If so, then preform two finds so we
        # find the prompt we are looking for instead of this empty prompt
        findCount = (
            2 if self.toPlainText()[-len(self.prompt()) :] == self.prompt() else 1
        )
        for i in range(findCount):
            self.find(self.prompt(), QTextDocument.FindBackward)
        # move to the end of the found line, select the rest of the text and remove it
        # preserving history if there is anything to remove.
        cursor = self.textCursor()
        cursor.movePosition(cursor.EndOfLine)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        text = cursor.selectedText()
        if text:
            self.setTextCursor(cursor)
            self.insertPlainText('')
        # Restore the cursor position to its original location
        self.setTextCursor(currentCursor)

    def commentColor(self):
        return self._commentColor

    def setCommentColor(self, color):
        self._commentColor = color

    def completer(self):
        """ returns the completer instance that is associated with this editor """
        return self._completer

    def errorMessageColor(self):
        return self.__class__._errorMessageColor

    def setErrorMessageColor(self, color):
        self.__class__._errorMessageColor = color

    def foregroundColor(self):
        return self._foregroundColor

    def setForegroundColor(self, color):
        self._foregroundColor = color

    def executeString(self, commandText, filename='<ConsoleEdit>'):
        cmdresult = None
        # https://stackoverflow.com/a/29456463
        # If you want to get the result of the code, you have to call eval
        # however eval does not accept multiple statements. For that you need
        # exec which has no Return.
        wasEval = False
        startTime = time.time()
        try:
            compiled = compile(commandText, filename, 'eval')
        except:
            compiled = compile(commandText, filename, 'exec')
            exec (compiled, __main__.__dict__, __main__.__dict__)
        else:
            cmdresult = eval(compiled, __main__.__dict__, __main__.__dict__)
            wasEval = True
        # Provide user feedback when running long code execution.
        delta = time.time() - startTime
        if self.flashTime and delta >= self.flashTime:
            blurdev.core.flashWindow()
        # Report the total time it took to execute this code.
        if self.reportExecutionTime is not None:
            self.reportExecutionTime(delta)
        return cmdresult, wasEval

    def executeCommand(self):
        """ executes the current line of code """
        # grab the command from the line
        block = self.textCursor().block().text()
        p = '{prompt}(.*)'.format(prompt=re.escape(self.prompt()))
        results = re.search(p, block)
        if results:
            commandText = results.groups()[0]
            # if the cursor position is at the end of the line
            if self.textCursor().atEnd():
                # insert a new line
                self.insertPlainText('\n')

                if self._pdbMode:
                    if commandText:
                        self.pdbSendCommand(commandText)
                    else:
                        # Sending a blank line to pdb will cause it to quit raising a exception.
                        # Most likely the user just wants to add some white space between their
                        # commands, so just add a new prompt line.
                        self.startInputLine()
                        self.insertPlainText(commandText)
                else:
                    # evaluate the command
                    cmdresult, wasEval = self.executeString(commandText)

                    # print the resulting commands
                    if cmdresult is not None:
                        # When writing to additional stdout's not including a new line makes
                        # the output not match the formatting you get inside the console.
                        self.write(u'{}\n'.format(cmdresult))
                        # NOTE: I am using u'' above so unicode strings in python 2 don't get
                        # converted to str objects.

                    self.startInputLine()

            # otherwise, move the command to the end of the line
            else:
                self.startInputLine()
                self.insertPlainText(commandText)

        # if no command, then start a new line
        else:
            self.startInputLine()

    def flush(self):
        pass

    def focusInEvent(self, event):
        """ overload the focus in event to ensure the completer has the proper widget """
        if self.completer():
            self.completer().setWidget(self)
        QTextEdit.focusInEvent(self, event)

    def insertCompletion(self, completion):
        """ inserts the completion text into the editor """
        if self.completer().widget() == self:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Left)
            cursor.movePosition(QTextCursor.EndOfWord)
            cursor.insertText(completion[len(self.completer().completionPrefix()) :])
            self.setTextCursor(cursor)

    def insertFromMimeData(self, mimeData):
        html = False
        if mimeData.hasHtml():
            text = mimeData.html()
            html = True
        else:
            text = mimeData.text()

        doc = QTextDocument()

        if html:
            doc.setHtml(text)
        else:
            doc.setPlainText(text)

        text = doc.toPlainText()

        exp = re.compile(
            '[^A-Za-z0-9\~\!\@\#\$\%\^\&\*\(\)\_\+\{\}\|\:\"\<\>\?\`\-\=\[\]\\\;\'\,\.\/ \t\n]'
        )
        newText = text.encode('utf-8')
        for each in exp.findall(newText):
            newText = newText.replace(each, '?')

        self.insertPlainText(newText)

    def isatty(self):
        """ Return True if the stream is interactive (i.e., connected to a terminal/tty device). """
        # This method is required for pytest to run in a DCC. Returns False so the output does not
        # contain cursor control characters that disrupt the visual display of the output.
        return False

    def lastError(self):
        try:
            return ''.join(
                traceback.format_exception(
                    sys.last_type, sys.last_value, sys.last_traceback
                )
            )
        except AttributeError:
            # last_traceback, last_type and last_value do not always exist
            return ''

    def keyPressEvent(self, event):
        """ overload the key press event to handle custom events """

        completer = self.completer()

        if completer and event.key() in (
            Qt.Key_Backspace,
            Qt.Key_Delete,
            Qt.Key_Escape,
        ):
            completer.hideDocumentation()

        # enter || return keys will execute the command
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if completer.popup().isVisible():
                completer.clear()
                event.ignore()
            else:
                self.executeCommand()

        # home key will move the cursor to home
        elif event.key() == Qt.Key_Home:
            self.moveToHome()

        # otherwise, ignore the event for completion events
        elif event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            if not completer.popup().isVisible():
                # The completer does not get updated if its not visible while typing.
                # We are about to complete the text using it so ensure its updated.
                completer.refreshList(scope=__main__.__dict__)
                completer.popup().setCurrentIndex(
                    completer.completionModel().index(0, 0)
                )
            # Insert the correct text and clear the completion model
            index = completer.popup().currentIndex()
            self.insertCompletion(index.data(Qt.DisplayRole))
            completer.clear()

        elif event.key() == Qt.Key_Escape and completer.popup().isVisible():
            completer.clear()

        # other wise handle the keypress
        else:
            ctrlSpace = (
                event.key() == Qt.Key_Space
                and QApplication.instance().keyboardModifiers() == Qt.ControlModifier
            )
            # Process all events we do not want to override
            if not ctrlSpace:
                QTextEdit.keyPressEvent(self, event)

            # check for particular events for the completion
            if completer:
                # look for documentation popups
                if event.key() == Qt.Key_ParenLeft:
                    rect = self.cursorRect()
                    point = self.mapToGlobal(QPoint(rect.x(), rect.y()))
                    completer.showDocumentation(pos=point, scope=__main__.__dict__)

                # hide documentation popups
                elif event.key() == Qt.Key_ParenRight:
                    completer.hideDocumentation()

                # determine if we need to show the popup or if it already is visible, we need to update it
                elif (
                    event.key() == Qt.Key_Period
                    or event.key() == Qt.Key_Escape
                    or completer.popup().isVisible()
                    or ctrlSpace
                ):
                    completer.refreshList(scope=__main__.__dict__)
                    completer.popup().setCurrentIndex(
                        completer.completionModel().index(0, 0)
                    )

                    # show the completer for the rect
                    rect = self.cursorRect()
                    rect.setWidth(
                        completer.popup().sizeHintForColumn(0)
                        + completer.popup().verticalScrollBar().sizeHint().width()
                    )
                    completer.complete(rect)

    def keywordColor(self):
        return self._keywordColor

    def setKeywordColor(self, color):
        self._keywordColor = color

    def moveToHome(self):
        """ moves the cursor to the home location """
        mode = QTextCursor.MoveAnchor
        # select the home
        if QApplication.instance().keyboardModifiers() == Qt.ShiftModifier:
            mode = QTextCursor.KeepAnchor
        # grab the cursor
        cursor = self.textCursor()
        if QApplication.instance().keyboardModifiers() == Qt.ControlModifier:
            # move to the top of the document if control is pressed
            cursor.movePosition(QTextCursor.Start)
        else:
            # Otherwise just move it to the start of the line
            block = cursor.block().text().split()
            cursor.movePosition(QTextCursor.StartOfBlock, mode)
        # move the cursor to the end of the prompt.
        cursor.movePosition(QTextCursor.Right, mode, len(self.prompt()))
        self.setTextCursor(cursor)

    def outputPrompt(self):
        """ The prompt used to output a result.
        """
        return self._outputPrompt

    def pdbContinue(self):
        self.pdbSendCommand('continue')

    def pdbDown(self):
        self.pdbSendCommand('down')

    def pdbNext(self):
        self.pdbSendCommand('next')

    def pdbStep(self):
        self.pdbSendCommand('step')

    def pdbUp(self):
        self.pdbSendCommand('up')

    def pdbMode(self):
        return self._pdbMode

    def setPdbMode(self, mode):
        if self.pdbModeAction:
            if not self.pdbModeAction.isEnabled():
                # pdbModeAction is disabled by default, enable the action, so the user can switch
                # between pdb and normal mode any time they want. pdbMode does nothing if this instance
                # of python is not the child process of blurdev.external.External, and the parent
                # process is in pdb mode.
                self.pdbModeAction.blockSignals(True)
                self.pdbModeAction.setChecked(mode)
                self.pdbModeAction.blockSignals(False)
                self.pdbModeAction.setEnabled(True)
        self._pdbMode = mode
        if self.pdbUpdateVisibility:
            self.pdbUpdateVisibility(mode)
        self.startInputLine()

    def pdbSendCommand(self, commandText):
        import blurdev.external

        blurdev.external.External(['pdb', '', {'msg': commandText}])

    def prompt(self):
        if self._pdbMode:
            return self._pdbPrompt
        return self._consolePrompt

    def resultColor(self):
        return self._resultColor

    def setResultColor(self, color):
        self._resultColor = color

    def setCompleter(self, completer):
        """ sets the completer instance for this widget """
        if completer:
            self._completer = completer
            completer.setWidget(self)
            completer.activated.connect(self.insertCompletion)

    def showEvent(self, event):
        # _firstShow is used to ensure the first imput prompt is styled by any active stylesheet
        if self._firstShow:
            self.startInputLine()
            self._firstShow = False
        super(ConsoleEdit, self).showEvent(event)

    def startInputLine(self):
        """ create a new command prompt line """
        self.startPrompt(self.prompt())

    def startPrompt(self, prompt):
        """ create a new command prompt line with the given prompt

        Args:
            prompt(str): The prompt to start the line with. If this prompt
                is already the only text on the last line this function does nothing.
        """
        self.moveCursor(QTextCursor.End)

        # if this is not already a new line
        if self.textCursor().block().text() != prompt:
            charFormat = QTextCharFormat()
            self.setCurrentCharFormat(charFormat)

            inputstr = prompt
            if self.textCursor().block().text():
                inputstr = '\n' + inputstr

            self.insertPlainText(inputstr)

    def startOutputLine(self):
        """ Create a new line to show output text. """
        self.startPrompt(self._outputPrompt)

    def stdoutColor(self):
        return self._stdoutColor

    def setStdoutColor(self, color):
        self._stdoutColor = color

    def stringColor(self):
        return self._stringColor

    def setStringColor(self, color):
        self._stringColor = color

    def write(self, msg, error=False):
        """ write the message to the logger """
        if not sip.isdeleted(self):
            self.moveCursor(QTextCursor.End)

            charFormat = QTextCharFormat()
            if not error:
                charFormat.setForeground(self.stdoutColor())
            else:
                charFormat.setForeground(self.errorMessageColor())

            self.setCurrentCharFormat(charFormat)
            try:
                self.insertPlainText(msg)
            except:
                if SafeOutput:
                    # win32com writes to the debugger if it is unable to print, so ensure it still does this.
                    SafeOutput.write(self, msg)
        else:
            if SafeOutput:
                # win32com writes to the debugger if it is unable to print, so ensure it still does this.
                SafeOutput.write(self, msg)

        # if a outputPipe was provided, write the message to that pipe
        if self.outputPipe:
            self.outputPipe(msg, error=error)

        # Pass data along to the original stdout
        try:
            if sys.stderr and error:
                self.stderr.write(msg)
            elif self.stdout:
                self.stdout.write(msg)
            else:
                sys.__stdout__.write(msg)
        except:
            pass
