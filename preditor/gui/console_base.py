import os
import re
import string
import subprocess
from fractions import Fraction
from typing import Optional

from Qt import QtCompat
from Qt.QtCore import Qt
from Qt.QtGui import (
    QColor,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QTextCharFormat,
    QTextCursor,
)
from Qt.QtWidgets import QAction, QApplication, QTextEdit, QWidget

from .. import instance, resourcePath, stream
from ..constants import StreamType
from ..stream.console_handler import HandlerInfo
from ..utils.cute import QtPropertyInit
from .codehighlighter import CodeHighlighter
from .loggerwindow import LoggerWindow
from .suggest_path_quotes_dialog import SuggestPathQuotesDialog


class ConsoleBase(QTextEdit):
    """Base class for a text widget used to show stdout/stderr writes."""

    workbox_pattern = re.compile(
        r'File "<Workbox(?:Selection)?>:(?P<workboxName>.*)", '
        r'line (?P<lineNum>\d{1,6})'
        r'(?P<inStr>, in)?'
    )
    """For Traceback workbox lines, use this regex pattern, so we can extract
    workboxName and lineNum. Note that Syntax errors present slightly
    differently than other Exceptions.
        SyntaxErrors:
            - Do NOT include the text ", in" followed by a module
            - DO include the offending line of code
        Other Exceptions
            - DO include the text ", in" followed by a module
            - Do NOT include the offending line of code if from stdIn (ie
                  a workbox)
    So we will use the presence of the text ", in" to tell use whether to
    fake the offending code line or not.
    """

    traceback_pattern = re.compile(
        r'File "(?P<filename>.*)", line (?P<lineNum>\d{1,10})(, in|\r\n|\n|$)'
    )
    """A pattern to capture info from tracebacks. The newline/$ section
    handle SyntaxError output that does not include the `, in ...` portion."""

    def __init__(self, parent: QWidget, controller: Optional[LoggerWindow] = None):
        super().__init__(parent)
        self.controller = controller
        self._first_show = True

        # Create the highlighter
        highlight = CodeHighlighter(self, 'Python')
        self.setCodeHighlighter(highlight)

        self.addSepNewline = False
        self.consoleLine = None
        self.mousePressPos = None

        self.init_actions()

    def __repr__(self):
        """The repr for this object including its objectName if set."""
        name = self.objectName()
        if name:
            name = f" named {name!r}"
        module = type(self).__module__
        class_ = type(self).__name__

        return f"<{module}.{class_}{name} object at 0x{id(self):016X}>"

    def contextMenuEvent(self, event):
        """Builds a custom right click menu to show."""
        # Create the standard menu and allow subclasses to customize it
        menu = self.createStandardContextMenu(event.pos())
        menu = self.update_context_menu(menu)
        menu.setFont(self.controller.font())
        menu.exec(self.mapToGlobal(event.pos()))

    @property
    def controller(self) -> Optional[LoggerWindow]:
        """Used to access workbox widgets and PrEditor settings that are needed.

        This must be set to a LoggerWindow instance. If not set then uses
        `self.window()`. If this instance isn't a child of a LoggerWindow you must
        set controller to an instance of a LoggerWindow.
        """
        if self._controller:
            return self._controller
        controller = self.window()
        if not isinstance(controller, LoggerWindow):
            controller = instance(create=False)
        return controller

    @controller.setter
    def controller(self, value: LoggerWindow):
        self._controller = value

    def codeHighlighter(self):
        """Get the code highlighter for the console

        Returns:
            _uiCodeHighlighter (CodeHighlighter): The instantiated CodeHighlighter
        """
        return self._uiCodeHighlighter

    def setCodeHighlighter(self, highlight):
        """Set the code highlighter for the console

        Args:
            highlight (CodeHighlighter): The instantiated CodeHighlighter
        """
        self._uiCodeHighlighter = highlight

    def errorHyperlink(self, anchor):
        """Determine if chosen line is an error traceback file-info line, if so, parse
        the filepath and line number, and attempt to open the module file in the user's
        chosen text editor at the relevant line, using specified Command Prompt pattern.

        The text editor defaults to SublimeText3, in the normal install directory
        """
        # Bail if Error Hyperlinks setting is not turned on or we don't have an anchor.
        doHyperlink = (
            hasattr(self.controller, 'uiErrorHyperlinksCHK')
            and self.controller.uiErrorHyperlinksCHK.isChecked()
            and anchor
        )
        if not doHyperlink:
            return

        # info is a comma separated string, in the form: "filename, workboxIdx, lineNum"
        info = anchor.split(', ')
        modulePath = info[0]
        workboxName = info[1]
        lineNum = info[2]

        # fetch info from LoggerWindow
        exePath = self.controller.textEditorPath
        cmdTempl = self.controller.textEditorCmdTempl

        # Bail if not setup properly
        if not workboxName:
            msg = (
                "Cannot use traceback hyperlink (Correct the path with Options "
                "> Set Preferred Text Editor Path).\n"
            )
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
                    self.controller, cmdTempl, quotedCmdTempl
                )
                self.controller.maybeDisplayDialog(dialog)

            # Refresh cmdTempl in case user just had it changed.
            cmdTempl = self.controller.textEditorCmdTempl

            # Attempt to create command from template and run the command
            try:
                command = cmdTempl.format(
                    exePath=exePath, modulePath=modulePath, lineNum=lineNum
                )
                subprocess.Popen(command)
            except (ValueError, OSError):
                msg = "The provided text editor command is not valid:\n    {}"
                msg = msg.format(cmdTempl)
                print(msg)
        elif workboxName is not None:
            workbox = self.controller.workbox_for_name(workboxName, visible=True)
            lineNum = int(lineNum)
            workbox.__goto_line__(lineNum)
            workbox.setFocus()

    @classmethod
    def getIndentForCodeTracebackLine(cls, msg):
        """Determine the indentation to recreate traceback lines

        Args:
            msg (str): The traceback line

        Returns:
            indent (str): A string of zero or more spaces used for indentation
        """
        indent = ""
        match = re.match(r"^ *", msg)
        if match:
            indent = match.group() * 2
        return indent

    def getWorkboxLine(self, name, lineNum):
        """Python 3 does not include in tracebacks the code line if it comes from
        stdin, which is the case for PrEditor workboxes, so we fake it. This method
        will return the line of code at lineNum, from the workbox with the provided
        name.

        Args:
            name (str): The name of the workbox from which to get a line of code
            lineNum (int): The number of the line to return

        Returns:
            txt (str): The line of text found
        """
        workbox = self.controller.workbox_for_name(name)
        if not workbox:
            return None
        if lineNum > workbox.lines():
            return None
        txt = workbox.text(lineNum).strip() + "\n"
        return txt

    def init_actions(self):
        self.uiClearACT = QAction("&Clear", self)
        self.uiClearACT.setIcon(QIcon(resourcePath('img/close-thick.png')))
        self.uiClearACT.setToolTip(
            "Clears the top section of PrEditor. This does not clear the workbox."
        )
        self.uiClearACT.setShortcut(QKeySequence("Ctrl+Shift+Alt+D"))
        self.uiClearACT.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.uiClearACT.triggered.connect(self.clear)
        self.addAction(self.uiClearACT)

    def init_logging_handlers(self, attrName=None, value=None):
        self.logging_info = {}
        for h in self.logging_handlers:
            hi = HandlerInfo(h)
            hi.install(self.write_log)
            self.logging_info[hi.name] = hi

    def mouseMoveEvent(self, event):
        """Overload of mousePressEvent to change mouse pointer to indicate it is
        over a clickable error hyperlink.
        """
        if self.anchorAt(event.pos()):
            QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
        else:
            QApplication.restoreOverrideCursor()
        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Overload of mousePressEvent to capture click position, so on release, we can
        check release position. If it's the same (ie user clicked vs click-drag to
        select text), we check if user clicked an error hyperlink.
        """
        left = event.button() == Qt.MouseButton.LeftButton
        anchor = self.anchorAt(event.pos())
        self.mousePressPos = event.pos()

        if left and anchor:
            event.ignore()
            return

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Overload of mouseReleaseEvent to capture if user has left clicked... Check if
        click position is the same as release position, if so, call errorHyperlink.
        """
        samePos = event.pos() == self.mousePressPos
        left = event.button() == Qt.MouseButton.LeftButton
        anchor = self.anchorAt(event.pos())

        if samePos and left and anchor:
            self.errorHyperlink(anchor)
        self.mousePressPos = None

        QApplication.restoreOverrideCursor()
        ret = super().mouseReleaseEvent(event)

        return ret

    @classmethod
    def parseErrorHyperLinkInfo(cls, txt):
        """Determine if txt is a File-info line from a traceback, and if so, return info
        dict.
        """

        ret = None
        if not txt.lstrip().startswith("File "):
            return ret

        match = cls.traceback_pattern.search(txt)
        if match:
            filename = match.groupdict().get('filename')
            lineNum = match.groupdict().get('lineNum')
            fileStart = txt.find(filename)
            fileEnd = fileStart + len(filename)

            ret = {
                'filename': filename,
                'fileStart': fileStart,
                'fileEnd': fileEnd,
                'lineNum': lineNum,
            }
        return ret

    def onFirstShow(self, event) -> bool:
        """Run extra code on the first showing of this widget.

        Example override implementation:

            class MyConsole(ConsoleBase):
                def onFirstShow(self, event):
                    if not super().onFirstShow(event):
                        return False
                    self.doWork()
                    return True

        Returns:
            bool: Returns True only if this is the first time this widget is
                shown. All overrides of this method should return the same.
        """
        if not self._first_show:
            return False

        # Configure the stream callbacks if enabled
        self.update_streams()

        # Redefine highlight variables now that stylesheet may have been updated
        self.codeHighlighter().defineHighlightVariables()

        self._first_show = False
        return True

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
        workbox = self.controller.current_workbox()
        if workbox:
            tab_width = workbox.__tab_width__()
        fontPixelWidth = QFontMetrics(font).horizontalAdvance(" ")
        self.setTabStopDistance(fontPixelWidth * tab_width)

        # Scroll to same relative position where we started
        if origPercent is not None:
            self.doubleSingleShotSetScrollValue(origPercent)

    def showEvent(self, event):
        # Ensure the onFirstShow method is run.
        self.onFirstShow(event)
        super().showEvent(event)

    def update_context_menu(self, menu):
        """Returns the menu to use for right click context."""
        # Note: this menu is built in reverse order for easy insertion
        sep = menu.insertSeparator(menu.actions()[0])
        menu.insertAction(sep, self.uiClearACT)
        return menu

    def update_streams(self, attrName=None, value=None):
        # overload the sys logger and ensure the stream_manager is installed
        self.stream_manager = stream.install_to_std()

        needs_callback = self.stream_echo_stdout or self.stream_echo_stderr
        if needs_callback:
            # Redirect future writes directly to the console, add any previous
            # writes to the console and possibly free up the memory consumed by
            # previous writes. It's safe to call this repeatedly.
            self.stream_manager.add_callback(
                self.write,
                replay=self.stream_replay,
                disable_writes=self.stream_disable_writes,
                clear=self.stream_clear,
            )
        else:
            self.stream_manager.remove_callback(self.write)

    def get_logging_info(self, name):
        # Look for a specific rule to handle this logging message
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            name = ".".join(parts[:i])
            if name in self.logging_info:
                return self.logging_info[name]

        # If no logging handler matches the name but we are showing the root
        # handler fall back to using the root handler to handle this logging call.
        if "root" in self.logging_info:
            return self.logging_info["root"]

        # Otherwise ignore it
        return None

    def write_log(self, log_data, stream_type=StreamType.CONSOLE):
        """Write a logging message to the console depending on filters."""
        handler, record = log_data
        # Find the console configuration that allows processing of this record
        logging_info = self.get_logging_info(record.name)
        if logging_info is None:
            return

        # Only log the record if it matches the logging level requirements
        if logging_info.level > record.levelno:
            return

        formatter = handler
        if logging_info.formatter:
            formatter = logging_info.formatter
        msg = formatter.format(record)
        self.write(f'{msg}\n', stream_type=stream_type)

    def write(self, msg, stream_type=StreamType.STDOUT):
        """Write a message to the logger.

        Args:
            msg (str): The message to write.
            stream_type (bool, optional): Treat this write as as stderr output.

        In order to make a stack-trace provide clickable hyperlinks, it must be sent
        to self._write line-by-line, like a actual exception traceback is. So, we check
        if msg has the stack marker str, if so, send it line by line, otherwise, just
        pass msg on to self._write.
        """
        stack_marker = "Stack (most recent call last)"
        index = msg.find(stack_marker)
        has_stack_marker = index > -1

        if has_stack_marker:
            lines = msg.split("\n")
            for line in lines:
                line = "{}\n".format(line)
                self._write(line, stream_type=stream_type)
        else:
            self._write(msg, stream_type=stream_type)

    def _write(self, msg, stream_type=StreamType.STDOUT):
        """write the message to the logger"""
        if not msg:
            return

        # Convert the stream_manager's stream to the boolean value this function expects
        to_error = stream_type & StreamType.STDERR == StreamType.STDERR
        to_console = stream_type & StreamType.CONSOLE == StreamType.CONSOLE
        to_result = stream_type & StreamType.RESULT == StreamType.RESULT

        # Check that we haven't been garbage collected before trying to write.
        # This can happen while shutting down a QApplication like Nuke.
        if not QtCompat.isValid(self):
            return

        if to_result and not self.stream_echo_result:
            return

        # If stream_type is Console, then always show the output
        if not to_console:
            # Otherwise only show the message
            if to_error and not self.stream_echo_stderr:
                return
            if not to_error and not self.stream_echo_stdout:
                return

        doHyperlink = self.controller.uiErrorHyperlinksCHK.isChecked()
        sepPreditorTrace = self.controller.uiSeparateTracebackCHK.isChecked()
        self.moveCursor(QTextCursor.MoveOperation.End)

        charFormat = QTextCharFormat()
        if not to_error:
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
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
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

        # Determine if this is a workbox line of code, or code run directly
        # in the console
        isWorkbox = '<WorkboxSelection>' in filename or '<Workbox>' in filename
        isConsolePrEdit = '<ConsolePrEdit>' in filename

        # Starting in Python 3, tracebacks don't include the code executed
        # for stdin, so workbox code won't appear. This attempts to include
        # it. There is an exception for SyntaxErrors, which DO include the
        # offending line of code, so in those cases (indicated by lack of
        # inStr from the regex search) we skip faking the code line.
        if isWorkbox:
            match = self.workbox_pattern.search(msg)
            workboxName = match.groupdict().get("workboxName")
            lineNum = int(match.groupdict().get("lineNum")) - 1
            inStr = match.groupdict().get("inStr", "")

            workboxLine = self.getWorkboxLine(workboxName, lineNum)
            if workboxLine and inStr:
                indent = self.getIndentForCodeTracebackLine(msg)
                msg = "{}{}{}".format(msg, indent, workboxLine)

        elif isConsolePrEdit:
            consoleLine = self.consoleLine
            indent = self.getIndentForCodeTracebackLine(msg)
            msg = "{}{}{}\n".format(msg, indent, consoleLine)

        # To make it easier to see relevant lines of a traceback, optionally insert
        # a newline separating internal PrEditor code from the code run by user.
        if self.addSepNewline:
            if sepPreditorTrace:
                msg = "\n" + msg
            self.addSepNewline = False

        preditorCalls = ("cmdresult = e", "exec(compiled,")
        if msg.strip().startswith(preditorCalls):
            self.addSepNewline = True

            # Error tracebacks and logging.stack_info supply msg's differently,
            # so modify it here, so we get consistent results.
            msg = msg.replace("\n\n", "\n")

        if info and doHyperlink and not isConsolePrEdit:
            fileStart = info.get("fileStart")
            fileEnd = info.get("fileEnd")
            lineNum = info.get("lineNum")

            toolTip = 'Open "{}" at line number {}'.format(filename, lineNum)
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

    # These Qt Properties can be customized using style sheets.
    commentColor = QtPropertyInit('_commentColor', QColor(0, 206, 52))
    errorMessageColor = QtPropertyInit('_errorMessageColor', QColor(Qt.GlobalColor.red))
    keywordColor = QtPropertyInit('_keywordColor', QColor(17, 154, 255))
    resultColor = QtPropertyInit('_resultColor', QColor(128, 128, 128))
    stdoutColor = QtPropertyInit('_stdoutColor', QColor(17, 154, 255))
    stringColor = QtPropertyInit('_stringColor', QColor(255, 128, 0))

    logging_handlers = QtPropertyInit(
        '_logging_handlers', list, callback=init_logging_handlers, typ="QStringList"
    )
    """Used to install LoggerWindowHandler's for this console. Each item should be a
    `handler.name,level`. Level can be the int value (50) or level name (DEBUG).
    """

    # Configure stdout/error redirection options
    stream_clear = QtPropertyInit('_stream_clear', False)
    """When first shown, should this instance clear the stream manager's stored
    history?"""
    stream_disable_writes = QtPropertyInit('_stream_disable_writes', False)
    """When first shown, should this instance disable writes on the stream?"""
    stream_replay = QtPropertyInit('_stream_replay', False)
    """When first shown, should this instance replay the streams stored history?"""
    stream_echo_stderr = QtPropertyInit(
        '_stream_echo_stderr', False, callback=update_streams
    )
    """Should this console print stderr writes?"""
    stream_echo_stdout = QtPropertyInit(
        '_stream_echo_stdout', False, callback=update_streams
    )
    """Should this console print stdout writes?"""
    stream_echo_result = False
    """Reserved for ConsolePrEdit to enable StreamType.RESULT output. There is
    no reason for the baseclass to use QtPropertyInit, but this property is
    checked used by write so it needs defined."""
