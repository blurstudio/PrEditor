from __future__ import absolute_import

import re
import string
import sys
import time
import traceback
from functools import partial
from typing import Optional

import __main__
from Qt.QtCore import QPoint, Qt, QTimer
from Qt.QtGui import QKeySequence, QTextCursor, QTextDocument
from Qt.QtWidgets import QAbstractItemView, QAction, QApplication, QWidget

from .. import settings
from ..constants import StreamType
from ..utils import Truncate
from ..utils.cute import QtPropertyInit
from .completer import PythonCompleter
from .console_base import ConsoleBase
from .loggerwindow import LoggerWindow


class ConsolePrEdit(ConsoleBase):
    # Ensure the error prompt only shows up once.
    _errorPrompted = False

    _consolePrompt = '>>> '

    # Note: Changing _outputPrompt may require updating resource\lang\python.xml
    # If still using a #
    _outputPrompt = '#Result: '

    def __init__(self, parent: QWidget, controller: Optional[LoggerWindow] = None):
        super(ConsolePrEdit, self).__init__(parent, controller=controller)

        # Method used to update the gui when code is executed
        self.clearExecutionTime = None
        self.reportExecutionTime = None

        # store the error buffer
        self._completer = None

        # When executing code, that takes longer than this seconds, flash the window
        self.flash_window = None

        # Store previous commands to retrieve easily
        self._prevCommands = []
        self._prevCommandIndex = 0
        self._prevCommandsMax = 100

        # create the completer
        self.setCompleter(PythonCompleter(self))

        self.uiClearToLastPromptACT = QAction('Clear to Last', self)
        self.uiClearToLastPromptACT.triggered.connect(self.clearToLastPrompt)
        self.uiClearToLastPromptACT.setShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_Backspace)
        )
        self.addAction(self.uiClearToLastPromptACT)

        # Make sure console cursor is visible. It can get it's width set to 0 with
        # unusual(ie not 100%) os display scaling.
        if not self.cursorWidth():
            self.setCursorWidth(1)

        # The act of changing from no scroll bar to a scroll bar can add up to 1
        # second of time to the process of outputting text, so, just always have
        # it on.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

    def doubleSingleShotSetScrollValue(self, origPercent):
        """This double QTimer.singleShot monkey business seems to be the only way
        to get scroll.maximum() to update properly so that we calc newValue
        correctly. It's quite silly. Apparently, the important part is that
        calling scroll.maximum() has had a pause since the font had been set.
        """

        def singleShotSetScrollValue(self, origPercent):
            scroll = self.verticalScrollBar()
            maximum = scroll.maximum()
            if maximum is not None:
                newValue = round(origPercent * maximum)
                QTimer.singleShot(1, partial(scroll.setValue, newValue))

        # The 100 ms timer amount is somewhat arbitrary. It must be more than
        # some value to work, but what that value is is unknown, and may change
        # under various circumstances. Briefly disable updates for smoother transition.
        self.setUpdatesEnabled(False)
        try:
            QTimer.singleShot(100, partial(singleShotSetScrollValue, self, origPercent))
        finally:
            self.setUpdatesEnabled(True)

    def keyReleaseEvent(self, event):
        """Override of keyReleaseEvent to determine when to end navigation of
        previous commands
        """
        if event.key() == Qt.Key.Key_Alt:
            self._prevCommandIndex = 0
        else:
            event.ignore()

    def getPrevCommand(self):
        """Find and display the previous command in stack"""
        self._prevCommandIndex -= 1

        if abs(self._prevCommandIndex) > len(self._prevCommands):
            self._prevCommandIndex += 1

        if self._prevCommands:
            self.setCommand()

    def getNextCommand(self):
        """Find and display the next command in stack"""
        self._prevCommandIndex += 1
        self._prevCommandIndex = min(self._prevCommandIndex, 0)

        if self._prevCommands:
            self.setCommand()

    def setCommand(self):
        """Do the displaying of currently chosen command"""
        prevCommand = ''
        if self._prevCommandIndex:
            prevCommand = self._prevCommands[self._prevCommandIndex]

        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        if cursor.selectedText().startswith(self._consolePrompt):
            prevCommand = "{}{}".format(self._consolePrompt, prevCommand)
        cursor.insertText(prevCommand)
        self.setTextCursor(cursor)

    def clear(self):
        """clears the text in the editor"""
        super(ConsoleBase, self).clear()
        self.startInputLine()
        # Note: Don't use the regular `super()` call here as it would result
        # in multiple calls to repaint, just call the base Qt class's clear.
        self.maybeRepaint(force=True)

    def clearToLastPrompt(self):
        # store the current cursor position so we can restore when we are done
        currentCursor = self.textCursor()
        # move to the end of the document so we can search backwards
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        # Check if the last line is a empty prompt. If so, then preform two finds so we
        # find the prompt we are looking for instead of this empty prompt
        findCount = (
            2 if self.toPlainText()[-len(self.prompt()) :] == self.prompt() else 1
        )
        for _ in range(findCount):
            self.find(self.prompt(), QTextDocument.FindFlag.FindBackward)
        # move to the end of the found line, select the rest of the text and remove it
        # preserving history if there is anything to remove.
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        cursor.movePosition(
            QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
        )
        txt = cursor.selectedText()
        if txt:
            self.setTextCursor(cursor)
            self.insertPlainText('')
        # Restore the cursor position to its original location
        self.setTextCursor(currentCursor)

    def completer(self):
        """returns the completer instance that is associated with this editor"""
        return self._completer

    def executeString(
        self,
        commandText,
        consoleLine=None,
        filename='<ConsolePrEdit>',
        extraPrint=True,
        echoResult=False,
        truncate=False,
    ):
        # These vars helps with faking code lines in tracebacks for stdin input, which
        # workboxes are, and py3 doesn't include in the traceback
        self.consoleLine = consoleLine or ""

        if self.clearExecutionTime is not None:
            self.clearExecutionTime()
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        line = cursor.selectedText()
        if line and line[0] not in string.printable:
            line = line[1:]

        if line.startswith(self.prompt()) and extraPrint:
            self.write("\n", stream_type=StreamType.RESULT)

        cmdresult = None
        # https://stackoverflow.com/a/29456463
        # If you want to get the result of the code, you have to call eval
        # however eval does not accept multiple statements. For that you need
        # exec which has no Return.
        wasEval = False
        startTime = time.time()

        try:
            compiled = compile(commandText, filename, 'eval')
            wasEval = True
        except Exception:
            compiled = compile(commandText, filename, 'exec')

        # We wrap in try / finally so that elapsed time gets updated, even when an
        # exception is raised.
        try:
            if wasEval:
                cmdresult = eval(compiled, __main__.__dict__, __main__.__dict__)
            else:
                exec(compiled, __main__.__dict__, __main__.__dict__)
        finally:
            # Report the total time it took to execute this code.
            if self.reportExecutionTime is not None:
                delta = time.time() - startTime
                self.reportExecutionTime((delta, commandText))

        # Provide user feedback when running long code execution.
        if self.controller:
            flash_time = self.controller.uiFlashTimeSPIN.value()
            if self.flash_window and flash_time and delta >= flash_time:
                if settings.OS_TYPE == "Windows":
                    try:
                        from casement import utils
                    except ImportError:
                        # If casement is not installed, flash window is disabled
                        pass
                    else:
                        hwnd = int(self.flash_window.winId())
                        utils.flash_window(hwnd)

        if echoResult and wasEval:
            # If the selected code was a statement print the result of the statement.
            ret = repr(cmdresult)
            self.startOutputLine()
            if truncate:
                self.write(
                    Truncate(ret).middle(100) + "\n", stream_type=StreamType.RESULT
                )
            else:
                self.write(ret + "\n", stream_type=StreamType.RESULT)

        return cmdresult, wasEval

    def executeCommand(self):
        """executes the current line of code"""

        # Not using workbox, so clear this
        self.consoleLine = ""

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

                # update prevCommands list, but only if commandText is not the most
                # recent prevCommand, or there are no previous commands
                hasText = len(commandText) > 0
                prevCmds = self._prevCommands
                notPrevCmd = not prevCmds or prevCmds[-1] != commandText
                if hasText and notPrevCmd:
                    self._prevCommands.append(commandText)
                # limit length of prevCommand list to max number of prev commands
                self._prevCommands = self._prevCommands[-1 * self._prevCommandsMax :]

                # evaluate the command
                cmdresult, wasEval = self.executeString(
                    commandText, consoleLine=commandText
                )

                # print the resulting commands
                if cmdresult is not None:
                    # When writing to additional stdout's not including a new line
                    # makes the output not match the formatting you get inside the
                    # console.
                    self.write(u'{}\n'.format(cmdresult))
                    # NOTE: I am using u'' above so unicode strings in python 2
                    # don't get converted to str objects.

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
        """overload the focus in event to ensure the completer has the proper widget"""
        if self.completer():
            self.completer().setWidget(self)
        super().focusInEvent(event)

    def insertCompletion(self, completion):
        """inserts the completion text into the editor"""
        if self.completer().widget() == self:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            cursor.insertText(completion)
            self.setTextCursor(cursor)

    def insertFromMimeData(self, mimeData):
        html = False
        if mimeData.hasHtml():
            txt = mimeData.html()
            html = True
        else:
            txt = mimeData.text()

        doc = QTextDocument()

        if html:
            doc.setHtml(txt)
        else:
            doc.setPlainText(txt)

        txt = doc.toPlainText()

        exp = re.compile(
            (
                r'[^A-Za-z0-9\~\!\@\#\$\%\^\&\*\(\)\_\+\{\}\|\:'
                r'\"\<\>\?\`\-\=\[\]\\\;\'\,\.\/ \t\n]'
            )
        )
        newText = str(txt)
        for each in exp.findall(newText):
            newText = newText.replace(each, '?')

        self.insertPlainText(newText)

    def isatty(self):
        """Return True if the stream is interactive (i.e., connected to a terminal/tty
        device).
        """
        # This method is required for pytest to run in a DCC. Returns False so the
        # output does not contain cursor control characters that disrupt the visual
        # display of the output.
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
        """overload the key press event to handle custom events"""

        completer = self.completer()

        # Define prefix so we can determine if the exact prefix is in
        # completions and highlight it. We must manually add the currently typed
        # character, or remove it if backspace or delete has just been pressed.
        key = event.text()
        _, prefix = completer.currentObject(scope=__main__.__dict__)
        isBackspaceOrDel = event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
        if key.isalnum() or key in ("-", "_"):
            prefix += str(key)
        elif isBackspaceOrDel and prefix:
            prefix = prefix[:-1]

        if completer and event.key() in (
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete,
            Qt.Key.Key_Escape,
        ):
            completer.hideDocumentation()

        # enter || return keys will execute the command
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if completer.popup().isVisible():
                completer.clear()
                event.ignore()
            else:
                self.executeCommand()

        # home key will move the cursor to home
        elif event.key() == Qt.Key.Key_Home:
            self.moveToHome()

        # otherwise, ignore the event for completion events
        elif event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            if not completer.popup().isVisible():
                # The completer does not get updated if its not visible while typing.
                # We are about to complete the text using it so ensure its updated.
                completer.refreshList(scope=__main__.__dict__)
                completer.popup().setCurrentIndex(
                    completer.completionModel().index(0, 0)
                )
            # Insert the correct text and clear the completion model
            index = completer.popup().currentIndex()
            self.insertCompletion(index.data(Qt.ItemDataRole.DisplayRole))
            completer.clear()

        elif event.key() == Qt.Key.Key_Escape and completer.popup().isVisible():
            completer.clear()

        # other wise handle the keypress
        else:
            # define special key sequences
            modifiers = QApplication.instance().keyboardModifiers()
            ctrlSpace = (
                event.key() == Qt.Key.Key_Space
                and modifiers == Qt.KeyboardModifier.ControlModifier
            )
            ctrlM = (
                event.key() == Qt.Key.Key_M
                and modifiers == Qt.KeyboardModifier.ControlModifier
            )
            ctrlI = (
                event.key() == Qt.Key.Key_I
                and modifiers == Qt.KeyboardModifier.ControlModifier
            )

            # Process all events we do not want to override
            if not (ctrlSpace or ctrlM or ctrlI):
                super().keyPressEvent(event)

            if self.controller:
                if ctrlI:
                    self.controller.toggleCaseSensitive()
                if ctrlM:
                    self.controller.cycleCompleterMode()

            # check for particular events for the completion
            if completer:
                # look for documentation popups
                if event.key() == Qt.Key.Key_ParenLeft:
                    rect = self.cursorRect()
                    point = self.mapToGlobal(QPoint(rect.x(), rect.y()))
                    completer.showDocumentation(pos=point, scope=__main__.__dict__)

                # hide documentation popups
                elif event.key() == Qt.Key.Key_ParenRight:
                    completer.hideDocumentation()

                # determine if we need to show the popup or if it already is visible, we
                # need to update it
                elif (
                    event.key() == Qt.Key.Key_Period
                    or event.key() == Qt.Key.Key_Escape
                    or completer.popup().isVisible()
                    or ctrlSpace
                    or ctrlI
                    or ctrlM
                    or completer.wasCompletingCounter
                ):
                    completer.refreshList(scope=__main__.__dict__)

                    model = completer.completionModel()
                    index = model.index(0, 0)

                    # If option chosen, if the exact prefix exists in the
                    # possible completions, highlight it, even if it's not the
                    # topmost completion.
                    if (
                        self.controller
                        and self.controller.uiHighlightExactCompletionCHK.isChecked()
                    ):
                        for i in range(completer.completionCount()):
                            completer.setCurrentRow(i)
                            curCompletion = completer.currentCompletion()
                            if prefix == curCompletion:
                                index = model.index(i, 0)
                                break
                            elif prefix == curCompletion.lower():
                                index = model.index(i, 0)
                                break

                    # Set completer current Row, so finishing the completer will use
                    # correct text
                    completer.setCurrentRow(index.row())

                    # Make sure that current selection is visible, ie scroll to it
                    completer.popup().scrollTo(
                        index, QAbstractItemView.ScrollHint.EnsureVisible
                    )

                    # show the completer for the rect
                    rect = self.cursorRect()
                    rect.setWidth(
                        completer.popup().sizeHintForColumn(0)
                        + completer.popup().verticalScrollBar().sizeHint().width()
                    )
                    completer.complete(rect)

                if completer.popup().isVisible():
                    completer.wasCompleting = True
                    completer.wasCompletingCounter = 0

                if completer.wasCompleting and not completer.popup().isVisible():
                    wasCompletingCounterMax = completer.wasCompletingCounterMax
                    if completer.wasCompletingCounter <= wasCompletingCounterMax:
                        if event.key() not in (Qt.Key.Key_Backspace, Qt.Key.Key_Left):
                            completer.wasCompletingCounter += 1
                    else:
                        completer.wasCompletingCounter = 0
                        completer.wasCompleting = False

    def moveToHome(self):
        """moves the cursor to the home location"""
        mode = QTextCursor.MoveMode.MoveAnchor
        # select the home
        if (
            QApplication.instance().keyboardModifiers()
            == Qt.KeyboardModifier.ShiftModifier
        ):
            mode = QTextCursor.MoveMode.KeepAnchor
        # grab the cursor
        cursor = self.textCursor()
        if (
            QApplication.instance().keyboardModifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            # move to the top of the document if control is pressed
            cursor.movePosition(QTextCursor.MoveOperation.Start)
        else:
            # Otherwise just move it to the start of the line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, mode)
        # move the cursor to the end of the prompt.
        cursor.movePosition(QTextCursor.MoveOperation.Right, mode, len(self.prompt()))
        self.setTextCursor(cursor)

    def onFirstShow(self, event) -> bool:
        if not super().onFirstShow(event):
            # It's already been shown, nothing to do.
            return False

        # This is the first showing of this widget, ensure the first input
        # prompt is styled by any active stylesheet
        self.startInputLine()
        return True

    def outputPrompt(self):
        """The prompt used to output a result."""
        return self._outputPrompt

    def prompt(self):
        return self._consolePrompt

    def setCompleter(self, completer):
        """sets the completer instance for this widget"""
        if completer:
            self._completer = completer
            completer.setWidget(self)
            completer.activated.connect(self.insertCompletion)

    def startInputLine(self):
        """create a new command prompt line"""
        self.startPrompt(self.prompt())
        self._prevCommandIndex = 0

    def startOutputLine(self):
        """Create a new line to show output text."""
        self.startPrompt(self._outputPrompt)

    def removeCurrentLine(self):
        self.moveCursor(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
        self.moveCursor(
            QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor
        )
        self.moveCursor(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        self.textCursor().removeSelectedText()
        self.textCursor().deletePreviousChar()
        self.insertPlainText("\n")

    # This main console should have these settings enabled by default
    stream_clear = QtPropertyInit('_stream_clear', True)
    stream_disable_writes = QtPropertyInit('_stream_disable_writes', True)
    stream_replay = QtPropertyInit('_stream_replay', True)
    stream_echo_stderr = QtPropertyInit(
        '_stream_echo_stderr', True, callback=ConsoleBase.update_streams
    )
    stream_echo_stdout = QtPropertyInit(
        '_stream_echo_stdout', True, callback=ConsoleBase.update_streams
    )
    stream_echo_result = QtPropertyInit("_stream_echo_result", True)
    """Enable StreamType.RESULT output when running code using PrEditor."""
