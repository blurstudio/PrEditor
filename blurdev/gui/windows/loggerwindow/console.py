""" LoggerWindow class is an overloaded python interpreter for blurdev

"""

import re
import __main__
import os
import sys
import traceback
import socket
from abc import ABCMeta

from PyQt4.QtCore import QObject, QPoint, QTimer, QDateTime, Qt
from PyQt4.QtGui import (
    QTextEdit,
    QApplication,
    QTextCursor,
    QTextDocument,
    QTextCharFormat,
    QMessageBox,
    QColor,
)

import blurdev
from blurdev import debug
from .completer import PythonCompleter
from blurdev.gui.highlighters.codehighlighter import CodeHighlighter
from blurdev.tools import ToolsEnvironment
import blurdev.gui.windows.loggerwindow

# win32com's redirects all sys.stderr output to sys.stdout if the existing sys.stdout is not a instance of its SafeOutput
# Make our logger classes inherit from SafeOutput so they don't get replaced by win32com
try:
    from win32com.axscript.client.framework import SafeOutput

    class Win32ComFix(SafeOutput):
        pass


except ImportError:
    SafeOutput = None

    class Win32ComFix(object):
        pass


emailformat = """
<html>
    <head>
        <style>
            body {
                font-family: Verdana, sans-serif;
                font-size: 12px;
                color:#484848;
                background:lightGray;
            }
            h1, h2, h3 { font-family: "Trebuchet MS", Verdana, sans-serif; margin: 0px; }
            h1 { font-size: 1.2em; }
            h2, h3 { font-size: 1.1em; }
            a, a:link, a:visited { color: #2A5685;}
            a:hover, a:active { color: #c61a1a; }
            a.wiki-anchor { display: none; }
            hr {
                width: 100%%;
                height: 1px;
                background: gray;
                border: 0;
            }
            .footer {
                font-size: 0.9em;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <h1>%(subject)s</h1>
        <br><br>
        %(body)s
        <br><br><br><br>
        <hr/>
        <span class="footer">
            <p>You have received this notification because you have either subscribed to it, or are involved in it.<br/>
            To change your notification preferences, go into trax and change your options settings.
            </p>
        </span>
    </body>
</html>
"""


class ErrorLog(QObject, Win32ComFix):
    def flush(self):
        """ flush the logger instance """
        self.parent().flush()

    def write(self, msg):
        """ log an error message """
        self.parent().write(msg, error=True)


class ConsoleEdit(QTextEdit, Win32ComFix):
    _additionalInfo = None

    def __init__(self, parent):
        QTextEdit.__init__(self, parent)

        # store the error buffer
        self._completer = None
        self.errorTimeout = 50
        self._errorTimer = QTimer()
        self._errorTimer.setSingleShot(True)
        self._errorTimer.timeout.connect(self.handleError)
        self._additionalInfoTimer = QTimer()
        self._additionalInfoTimer.setSingleShot(True)
        self._additionalInfoTimer.timeout.connect(self.clearAdditionalInfo)

        # create the completer
        self.setCompleter(PythonCompleter(self))

        # overload the sys logger (if we are not on a high debugging level)
        if (
            os.path.basename(sys.executable) != 'python.exe'
            or debug.debugLevel() != debug.DebugLevel.High
        ):
            sys.stdout = self
            sys.stderr = ErrorLog(self)

        # create the highlighter
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')

        self.startInputLine()

    def clear(self):
        """ clears the text in the editor """
        QTextEdit.clear(self)
        self.startInputLine()

    def completer(self):
        """ returns the completer instance that is associated with this editor """
        return self._completer

    @staticmethod
    def emailError(emails, error, subject=None, information=None):
        """
        Generates and sends a email of the traceback, and usefull information provided by the class if available.
        
            If the erroring class provides the folowing method, what ever text it returns will be included in the email under Additional Information
            |	def errorLog(self):
            |		return '[Additional text to include in email]'
        :param emails: A string of the emails to send to
        :param error: The error message to pass along
        :param subject: If not provided the second to last line of the error is used
        :param information: if provided this string is included under the Information header of the provided email
        """
        if not error:
            return

        # do not email when debugging
        if debug.debugLevel():
            return

        # get current user
        username = blurdev.osystem.username()
        if not username:
            username = 'Anonymous'

        # get current host
        try:
            host = socket.gethostname()
        except:
            host = 'Unknown'

        # Build the message
        envName = blurdev.activeEnvironment().objectName()
        message = ['<ul>']
        message.append('<li><b>user: </b>%s</li>' % username)
        message.append('<li><b>host: </b>%s</li>' % host)
        message.append(
            '<li><b>date: </b>%s</li>'
            % QDateTime.currentDateTime().toString('MMM dd, yyyy @ h:mm ap')
        )
        message.append('<li><b>python: </b>%s</li>' % sys.version)
        message.append('<li><b>executable: </b>%s</li>' % sys.executable)
        message.append(
            '<li><b>blurdev env:</b> %s: %s</li>'
            % (envName, blurdev.activeEnvironment().path())
        )

        # notify where the error came from
        window = QApplication.activeWindow()
        className = ''

        # use the root application
        if window.__class__.__name__ == 'LoggerWindow':
            window = window.parent()

        if window:
            message.append(
                '<li><b>window: </b>%s (from %s Class)</li>'
                % (window.objectName(), window.__class__.__name__)
            )
            className = '[W:%s]' % window.__class__.__name__

        # Build the brief & subject information
        if not subject:
            subject = error.split('\n')[-2]
        if envName:
            envName = '[E:%s]' % envName

        subject = '[Python Error][U:%s][C:%s]%s%s %s' % (
            username,
            blurdev.core.objectName(),
            envName,
            className,
            subject,
        )

        coreMsg = blurdev.core.errorCoreText()
        if coreMsg:
            message.append('<li><b>blurdev.core Message:</b> %s</li>' % coreMsg)

        # Load in any aditional error info from the environment variables
        prefix = 'BDEV_EMAILINFO_'
        for key in sorted(os.environ):
            if key.startswith(prefix):
                message.append(
                    '<li><b>%s:</b> %s</li>'
                    % (key[len(prefix) :].replace('_', ' ').lower(), os.environ[key])
                )

        message.append('</ul>')
        message.append('<br>')
        message.append('<h3>Traceback Printout</h3>')
        message.append('<hr>')
        message.append(
            '<div style="background:white;color:red;padding:5 10 5 10;border:1px black solid"><pre><code>'
        )
        message.append(unicode(error).replace('\n', '<br>'))
        message.append('</code></pre></div>')
        # append any passed in body text
        for info in (information, ConsoleEdit.additionalInfo()):
            if info != None:
                message.append('<h3>Information</h3>')
                message.append('<hr>')
                message.append(
                    '<div style="background:white;color:red;padding:5 10 5 10;border:1px black solid"><pre><code>'
                )
                try:
                    message.append(unicode(info).replace('\n', '<br>'))
                except:
                    message.append('module.errorLog() generated a error.')
                message.append('</code></pre></div>')
        # append extra stuff
        if hasattr(sys, 'last_traceback'):
            tb = sys.last_traceback
            if tb:
                frame = tb.tb_frame
                if frame:
                    module = frame.f_locals.get('self')
                    if module:
                        if hasattr(module, 'errorLog'):
                            message.append('<h3>Additional Information</h3>')
                            message.append('<hr>')
                            message.append(
                                '<div style="background:white;color:red;padding:5 10 5 10;border:1px black solid"><pre><code>'
                            )
                            try:
                                message.append(module.errorLog().replace('\n', '<br>'))
                            except:
                                message.append('module.errorLog() generated a error.')
                            message.append('</code></pre></div>')

        blurdev.core.sendEmail(
            'thePipe@blur.com',
            emails,
            subject,
            emailformat % {'subject': subject, 'body': '\n'.join(message)},
        )

    def errorTimeout(self):
        """ end the error lookup """
        self._timer.stop()

    def executeCommand(self):
        """ executes the current line of code """
        # grab the command from the line
        block = self.textCursor().block().text()
        results = re.search('>>> (.*)', unicode(block))
        if results:
            # if the cursor position is at the end of the line
            if self.textCursor().atEnd():
                # insert a new line
                self.insertPlainText('\n')

                # evaluate the command
                cmdresult = None
                try:
                    cmdresult = eval(
                        unicode(results.groups()[0]),
                        __main__.__dict__,
                        __main__.__dict__,
                    )
                except:
                    exec (
                        unicode(results.groups()[0])
                    ) in __main__.__dict__, __main__.__dict__

                # print the resulting commands
                if cmdresult != None:
                    self.write(unicode(cmdresult))

                self.startInputLine()

            # otherwise, move the command to the end of the line
            else:
                self.startInputLine()
                self.insertPlainText(unicode(results.groups()[0]))

        # if no command, then start a new line
        else:
            self.startInputLine()

    def flush(self):
        self.clear()

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
        newText = unicode(text).encode('utf-8')
        for each in exp.findall(newText):
            newText = newText.replace(each, '?')

        self.insertPlainText(newText)

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
            self.insertCompletion(completer.currentCompletion())
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
            block = unicode(cursor.block().text()).split()
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

        self.moveCursor(QTextCursor.End)

        # if this is not already a new line
        if self.textCursor().block().text() != '>>> ':
            charFormat = QTextCharFormat()
            charFormat.setForeground(Qt.lightGray)
            self.setCurrentCharFormat(charFormat)

            inputstr = '>>> '
            if unicode(self.textCursor().block().text()):
                inputstr = '\n' + inputstr

            self.insertPlainText(inputstr)

    def handleError(self):
        """ process an error event handling """

        # determine the error email path
        emails = ToolsEnvironment.activeEnvironment().emailOnError()
        if emails:
            self.emailError(emails, ''.join(self.lastError()))

        # if the logger is not visible, prompt the user
        inst = blurdev.gui.windows.loggerwindow.LoggerWindow.instance()
        if not inst.isVisible():
            if not blurdev.core.quietMode():
                result = QMessageBox.question(
                    blurdev.core.rootWindow(),
                    'Error Occurred',
                    'An error has occurred in your Python script.  Would you like to see the log?',
                    QMessageBox.Yes | QMessageBox.No,
                )
                if result == QMessageBox.Yes:
                    inst.show()

    def write(self, msg, error=False):
        """ write the message to the logger """
        self.moveCursor(QTextCursor.End)
        charFormat = QTextCharFormat()

        if not error:
            charFormat.setForeground(QColor(17, 154, 255))
        else:
            # start recording information to the error buffer
            self._errorTimer.stop()
            self._errorTimer.start(self.errorTimeout)
            # Ensure the additionalInfo timeout lasts longer than the error timer
            self.resetAdditionalInfo()

            charFormat.setForeground(Qt.red)

        self.setCurrentCharFormat(charFormat)
        try:
            self.insertPlainText(msg)
        except:
            if SafeOutput:
                # win32com writes to the debugger if it is unable to print, so ensure it still does this.
                SafeOutput.write(self, msg)

    # These methods are used to insert extra data into error reports when debugging hard to reproduce errors.
    @classmethod
    def additionalInfo(cls):
        return cls._additionalInfo

    @classmethod
    def clearAdditionalInfo(cls):
        cls.setAdditionalInfo(None)

    def resetAdditionalInfo(self):
        self._additionalInfoTimer.stop()
        self._additionalInfoTimer.start(self.errorTimeout * 2)

    @classmethod
    def setAdditionalInfo(cls, info):
        cls._additionalInfo = info
