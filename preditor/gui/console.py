""" LoggerWindow class is an overloaded python interpreter for preditor"""
from __future__ import absolute_import, print_function

import os
import re
import string
import subprocess
import sys
import time
import traceback
from builtins import str as text
from fractions import Fraction
from functools import partial

import __main__
from Qt import QtCompat
from Qt.QtCore import QPoint, Qt, QTimer
from Qt.QtGui import QColor, QFontMetrics, QTextCharFormat, QTextCursor, QTextDocument
from Qt.QtWidgets import QAbstractItemView, QAction, QApplication, QTextEdit

from .. import settings, stream
from ..streamhandler_helper import StreamHandlerHelper
from . import QtPropertyInit
from .codehighlighter import CodeHighlighter
from .completer import PythonCompleter
from .suggest_path_quotes_dialog import SuggestPathQuotesDialog


class ConsolePrEdit(QTextEdit):
    # Ensure the error prompt only shows up once.
    _errorPrompted = False

    # These Qt Properties can be customized using style sheets.
    commentColor = QtPropertyInit('_commentColor', QColor(0, 206, 52))
    errorMessageColor = QtPropertyInit('_errorMessageColor', QColor(Qt.red))
    keywordColor = QtPropertyInit('_keywordColor', QColor(17, 154, 255))
    resultColor = QtPropertyInit('_resultColor', QColor(128, 128, 128))
    stdoutColor = QtPropertyInit('_stdoutColor', QColor(17, 154, 255))
    stringColor = QtPropertyInit('_stringColor', QColor(255, 128, 0))

    def __init__(self, parent):
        super(ConsolePrEdit, self).__init__(parent)
        # store the error buffer
        self._completer = None

        # If populated, also write to this interface
        self.outputPipe = None

        self._consolePrompt = '>>> '
        # Note: Changing _outputPrompt may require updating resource\lang\python.xml
        # If still using a #
        self._outputPrompt = '#Result: '
        # Method used to update the gui when code is executed
        self.clearExecutionTime = None
        self.reportExecutionTime = None

        self._firstShow = True

        # When executing code, that takes longer than this seconds, flash the window
        self.flash_time = 1.0
        self.flash_window = None

        # Store previous commands to retrieve easily
        self._prevCommands = []
        self._prevCommandIndex = 0
        self._prevCommandsMax = 100

        # create the completer
        self.setCompleter(PythonCompleter(self))

        # sys.__stdout__ doesn't work if some third party has implemented their own
        # override. Use these to backup the current logger so the logger displays
        # output, but application specific consoles also get the info.
        self.stdout = None
        self.stderr = None
        self._errorLog = None

        # overload the sys logger
        self.stream_manager = stream.install_to_std()
        # Redirect future writes directly to the console, add any previous writes
        # to the console and free up the memory consumed by previous writes as we
        # assume this is likely to be the only callback added to the manager.
        self.stream_manager.add_callback(
            self.write, replay=True, disable_writes=True, clear=True
        )
        # Store the current outputs
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self._errorLog = sys.stderr

        # Update any StreamHandler's that were setup using the old stdout/err
        StreamHandlerHelper.replace_stream(self.stdout, sys.stdout)
        StreamHandlerHelper.replace_stream(self.stderr, sys.stderr)

        # create the highlighter
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')
        self.uiCodeHighlighter = highlight

        self.uiClearToLastPromptACT = QAction('Clear to Last', self)
        self.uiClearToLastPromptACT.triggered.connect(self.clearToLastPrompt)
        self.uiClearToLastPromptACT.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_Backspace)
        self.addAction(self.uiClearToLastPromptACT)

        self.x = 0
        self.clickPos = None
        self.anchor = None

        # Make sure console cursor is visible. It can get it's width set to 0 with
        # unusual(ie not 100%) os display scaling.
        if not self.cursorWidth():
            self.setCursorWidth(1)

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

    def setConsoleFont(self, font):
        """Set the console's font and adjust the tabStopWidth"""

        # Capture the scroll bar's current position (by percentage of max)
        origPercent = None
        scroll = self.verticalScrollBar()
        if scroll.maximum():
            origPercent = Fraction(scroll.value(), scroll.maximum())

        # Set console and completer popup fonts
        self.setFont(font)
        self.completer().popup().setFont(font)

        # Set the setTabStopWidth for the console's font
        tab_width = 4
        # TODO: Make tab_width a general user setting
        if hasattr(self, "window") and "LoggerWindow" in str(type(self.window())):
            # If parented to a LoggerWindow, get the tab_width from it's workboxes
            workbox = self.window().current_workbox()
            if workbox:
                tab_width = workbox.__tab_width__()
        fontPixelWidth = QFontMetrics(font).width(" ")
        self.setTabStopWidth(fontPixelWidth * tab_width)

        # Scroll to same relative position where we started
        if origPercent is not None:
            self.doubleSingleShotSetScrollValue(origPercent)

    def mousePressEvent(self, event):
        """Overload of mousePressEvent to capture click position, so on release, we can
        check release position. If it's the same (ie user clicked vs click-drag to
        select text), we check if user clicked an error hyperlink.
        """
        self.clickPos = event.pos()
        self.anchor = self.anchorAt(event.pos())
        if self.anchor:
            QApplication.setOverrideCursor(Qt.PointingHandCursor)
        return super(ConsolePrEdit, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Overload of mouseReleaseEvent to capture if user has left clicked... Check if
        click position is the same as release position, if so, call errorHyperlink.
        """
        samePos = event.pos() == self.clickPos
        left = event.button() == Qt.LeftButton
        if samePos and left and self.anchor:
            self.errorHyperlink()

        self.clickPos = None
        self.anchor = None
        QApplication.restoreOverrideCursor()
        return super(ConsolePrEdit, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Override of wheelEvent to allow for font resizing by holding ctrl while"""
        # scrolling. If used in LoggerWindow, use that wheel event
        # May not want to import LoggerWindow, so perhaps
        # check by str(type())
        ctrlPressed = event.modifiers() == Qt.ControlModifier
        if ctrlPressed and "LoggerWindow" in str(type(self.window())):
            self.window().wheelEvent(event)
        else:
            QTextEdit.wheelEvent(self, event)

    def keyReleaseEvent(self, event):
        """Override of keyReleaseEvent to determine when to end navigation of
        previous commands
        """
        if event.key() == Qt.Key_Alt:
            self._prevCommandIndex = 0
        else:
            event.ignore()

    def errorHyperlink(self):
        """Determine if chosen line is an error traceback file-info line, if so, parse
        the filepath and line number, and attempt to open the module file in the user's
        chosen text editor at the relevant line, using specified Command Prompt pattern.

        The text editor defaults to SublimeText3, in the normal install directory
        """
        window = self.window()

        # Bail if Error Hyperlinks setting is not turned on or we don't have an anchor.
        doHyperlink = (
            hasattr(window, 'uiErrorHyperlinksACT')
            and window.uiErrorHyperlinksACT.isChecked()
            and self.anchor
        )
        if not doHyperlink:
            return

        # info is a comma separated string, in the form: "filename, workboxIdx, lineNum"
        info = self.anchor.split(', ')
        modulePath = info[0]
        workboxIndex = info[1]
        lineNum = info[2]

        # fetch info from LoggerWindow
        exePath = ''
        cmdTempl = ''
        if hasattr(window, 'textEditorPath'):
            exePath = window.textEditorPath
            cmdTempl = window.textEditorCmdTempl

        # Bail if not setup properly
        msg = "Cannot use traceback hyperlink. "
        if not exePath:
            msg += "No text editor path defined."
            print(msg)
            return
        if not os.path.exists(exePath):
            msg += "Text editor executable does not exist: {}".format(exePath)
            print(msg)
            return
        if not cmdTempl:
            msg += "No text editor Command Prompt command template defined."
            print(msg)
            return
        if modulePath and not os.path.exists(modulePath):
            msg += "Specified module path does not exist: {}".format(modulePath)
            print(msg)
            return

        if modulePath:
            # Check if cmdTempl filepaths aren't wrapped in double=quotes to handle
            # spaces. If not, suggest to user to update the template, offering the
            # suggested change.
            pattern = r"(?<!\")({\w+Path})(?!\")"
            repl = r'"\g<1>"'
            quotedCmdTempl = re.sub(pattern, repl, cmdTempl)
            if quotedCmdTempl != cmdTempl:
                # Instantiate dialog to maybe show (unless user previously chose "Don't
                # ask again")
                dialog = SuggestPathQuotesDialog(
                    self.window(), cmdTempl, quotedCmdTempl
                )
                self.window().maybeDisplayDialog(dialog)

            # Refresh cmdTempl in case user just had it changed.
            cmdTempl = window.textEditorCmdTempl

            # Attempt to create command from template and run the command
            try:
                command = cmdTempl.format(
                    exePath=exePath, modulePath=modulePath, lineNum=lineNum
                )
                subprocess.Popen(command)
            except (ValueError, OSError):
                msg = "The provided text editor command template is not valid:\n    {}"
                msg = msg.format(cmdTempl)
                print(msg)
        elif workboxIndex is not None:
            group, editor = workboxIndex.split(',')
            lineNum = int(lineNum)
            workbox = window.uiWorkboxTAB.set_current_groups_from_index(
                int(group), int(editor)
            )
            workbox.__goto_line__(lineNum)
            workbox.setFocus()

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
        cursor.select(QTextCursor.LineUnderCursor)
        if cursor.selectedText().startswith(self._consolePrompt):
            prevCommand = "{}{}".format(self._consolePrompt, prevCommand)
        cursor.insertText(prevCommand)
        self.setTextCursor(cursor)

    def clear(self):
        """clears the text in the editor"""
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
        for _ in range(findCount):
            self.find(self.prompt(), QTextDocument.FindBackward)
        # move to the end of the found line, select the rest of the text and remove it
        # preserving history if there is anything to remove.
        cursor = self.textCursor()
        cursor.movePosition(cursor.EndOfLine)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        txt = cursor.selectedText()
        if txt:
            self.setTextCursor(cursor)
            self.insertPlainText('')
        # Restore the cursor position to its original location
        self.setTextCursor(currentCursor)

    def completer(self):
        """returns the completer instance that is associated with this editor"""
        return self._completer

    def executeString(self, commandText, filename='<ConsolePrEdit>', extraPrint=True):
        if self.clearExecutionTime is not None:
            self.clearExecutionTime()
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        line = cursor.selectedText()
        if line and line[0] not in string.printable:
            line = line[1:]

        if line.startswith(self.prompt()) and extraPrint:
            print("")

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
        if self.flash_window and self.flash_time and delta >= self.flash_time:
            if settings.OS_TYPE == "Windows":
                try:
                    from casement import utils
                except ImportError:
                    # If casement is not installed, flash window is disabled
                    pass
                else:
                    hwnd = int(self.flash_window.winId())
                    utils.flash_window(hwnd)

        return cmdresult, wasEval

    def executeCommand(self):
        """executes the current line of code"""
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
                cmdresult, wasEval = self.executeString(commandText)

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
        QTextEdit.focusInEvent(self, event)

    def insertCompletion(self, completion):
        """inserts the completion text into the editor"""
        if self.completer().widget() == self:
            cursor = self.textCursor()
            cursor.select(QTextCursor.WordUnderCursor)
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
        newText = text(txt)
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
        isBackspaceOrDel = event.key() in (Qt.Key_Backspace, Qt.Key_Delete)
        if key.isalnum() or key in ("-", "_"):
            prefix += str(key)
        elif isBackspaceOrDel and prefix:
            prefix = prefix[:-1]

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
            # define special key sequences
            modifiers = QApplication.instance().keyboardModifiers()
            ctrlSpace = event.key() == Qt.Key_Space and modifiers == Qt.ControlModifier
            ctrlM = event.key() == Qt.Key_M and modifiers == Qt.ControlModifier
            ctrlI = event.key() == Qt.Key_I and modifiers == Qt.ControlModifier

            # Process all events we do not want to override
            if not (ctrlSpace or ctrlM or ctrlI):
                QTextEdit.keyPressEvent(self, event)

            window = self.window()
            if ctrlI:
                hasToggleCase = hasattr(window, 'toggleCaseSensitive')
                if hasToggleCase:
                    window.toggleCaseSensitive()
            if ctrlM:
                hasCycleMode = hasattr(window, 'cycleCompleterMode')
                if hasCycleMode:
                    window.cycleCompleterMode()

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

                # determine if we need to show the popup or if it already is visible, we
                # need to update it
                elif (
                    event.key() == Qt.Key_Period
                    or event.key() == Qt.Key_Escape
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
                    if self.window().uiHighlightExactCompletionACT.isChecked():
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
                    completer.popup().scrollTo(index, QAbstractItemView.EnsureVisible)

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
                        if event.key() not in (Qt.Key_Backspace, Qt.Key_Left):
                            completer.wasCompletingCounter += 1
                    else:
                        completer.wasCompletingCounter = 0
                        completer.wasCompleting = False

    def moveToHome(self):
        """moves the cursor to the home location"""
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
            cursor.movePosition(QTextCursor.StartOfBlock, mode)
        # move the cursor to the end of the prompt.
        cursor.movePosition(QTextCursor.Right, mode, len(self.prompt()))
        self.setTextCursor(cursor)

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

    def showEvent(self, event):
        # _firstShow is used to ensure the first imput prompt is styled by any active
        # stylesheet
        if self._firstShow:
            self.startInputLine()
            self._firstShow = False
        super(ConsolePrEdit, self).showEvent(event)

    def startInputLine(self):
        """create a new command prompt line"""
        self.startPrompt(self.prompt())
        self._prevCommandIndex = 0

    def startPrompt(self, prompt):
        """create a new command prompt line with the given prompt

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

        scroll = self.verticalScrollBar()
        maximum = scroll.maximum()
        if maximum is not None:
            scroll.setValue(maximum)

    def startOutputLine(self):
        """Create a new line to show output text."""
        self.startPrompt(self._outputPrompt)

    def removeCurrentLine(self):
        self.moveCursor(QTextCursor.End, QTextCursor.MoveAnchor)
        self.moveCursor(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
        self.moveCursor(QTextCursor.End, QTextCursor.KeepAnchor)
        self.textCursor().removeSelectedText()
        self.textCursor().deletePreviousChar()
        self.insertPlainText("\n")

    def parseErrorHyperLinkInfo(self, txt):
        """Determine if txt is a File-info line from a traceback, and if so, return info
        dict.
        """
        lineMarker = '", line '
        ret = None

        filenameEnd = txt.find(lineMarker)
        if txt[:8] == '  File "' and filenameEnd >= 0:
            filename = txt[8:filenameEnd]
            lineNumStart = filenameEnd + len(lineMarker)
            lineNumEnd = txt.find(',', lineNumStart)
            if lineNumEnd == -1:
                lineNumEnd = len(txt)
            lineNum = txt[lineNumStart:lineNumEnd]
            ret = {
                'filename': filename,
                'fileStart': 8,
                'fileEnd': filenameEnd,
                'lineNum': lineNum,
            }

        return ret

    def write(self, msg, error=False):
        """write the message to the logger"""
        # Convert the stream_manager's stream to the boolean value this function expects
        error = error == stream.STDERR
        # Check that we haven't been garbage collected before trying to write.
        # This can happen while shutting down a QApplication like Nuke.
        if QtCompat.isValid(self):
            window = self.window()
            doHyperlink = (
                hasattr(window, 'uiErrorHyperlinksACT')
                and window.uiErrorHyperlinksACT.isChecked()
            )
            self.moveCursor(QTextCursor.End)

            charFormat = QTextCharFormat()
            if not error:
                charFormat.setForeground(self.stdoutColor)
            else:
                charFormat.setForeground(self.errorMessageColor)
            self.setCurrentCharFormat(charFormat)

            # If showing Error Hyperlinks... Sometimes (when a syntax error, at least),
            # the last File-Info line of a traceback is issued in multiple messages
            # starting with unicode paragraph separator (r"\u2029") and followed by a
            # newline, so our normal string checks search won't work. Instead, we'll
            # manually reconstruct the line. If msg is a newline, grab that current line
            # and check it. If it matches,proceed using that line as msg
            cursor = self.textCursor()
            info = None

            if doHyperlink and msg == '\n':
                cursor.select(QTextCursor.BlockUnderCursor)
                line = cursor.selectedText()

                # Remove possible leading unicode paragraph separator, which really
                # messes up the works
                if line and line[0] not in string.printable:
                    line = line[1:]

                info = self.parseErrorHyperLinkInfo(line)
                if info:
                    cursor.insertText("\n")
                    msg = "{}\n".format(line)

            # If showing Error Hyperlinks, display underline output, otherwise
            # display normal output. Exclude ConsolePrEdits
            info = info if info else self.parseErrorHyperLinkInfo(msg)
            filename = info.get("filename", "") if info else ""
            isConsolePrEdit = '<ConsolePrEdit>' in filename

            if info and doHyperlink and not isConsolePrEdit:
                fileStart = info.get("fileStart")
                fileEnd = info.get("fileEnd")
                lineNum = info.get("lineNum")

                isWorkbox = '<WorkboxSelection>' in filename or '<Workbox>' in filename
                if isWorkbox:
                    split = filename.split(':')
                    workboxIdx = split[-1]
                    filename = ''
                else:
                    filename = filename
                    workboxIdx = ''
                href = '{}, {}, {}'.format(filename, workboxIdx, lineNum)

                # Insert initial, non-underlined text
                cursor.insertText(msg[:fileStart])

                # Insert hyperlink
                fmt = cursor.charFormat()
                fmt.setAnchor(True)
                fmt.setAnchorHref(href)
                fmt.setFontUnderline(True)
                toolTip = "Open {} at line number {}".format(filename, lineNum)
                fmt.setToolTip(toolTip)
                cursor.insertText(msg[fileStart:fileEnd], fmt)

                # Insert the rest of the msg
                fmt.setAnchor(False)
                fmt.setAnchorHref('')
                fmt.setFontUnderline(False)
                fmt.setToolTip('')
                cursor.insertText(msg[fileEnd:], fmt)
            else:
                # Non-hyperlink output
                self.insertPlainText(msg)

        # if a outputPipe was provided, write the message to that pipe
        if self.outputPipe:
            self.outputPipe(msg, error=error)
