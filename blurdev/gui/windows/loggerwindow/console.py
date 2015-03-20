""" LoggerWindow class is an overloaded python interpreter for blurdev

"""

import re
import __main__
import os
import sys
import sip
import traceback
import socket
import getpass
from abc import ABCMeta

from PyQt4.QtCore import QObject, QPoint, QDateTime, Qt, pyqtProperty
from PyQt4.QtGui import (
    QTextEdit,
    QApplication,
    QTextCursor,
    QTextDocument,
    QTextCharFormat,
    QMessageBox,
    QColor,
    QAction,
)

import blurdev
from blurdev import debug
from .completer import PythonCompleter
from blurdev.gui.highlighters.codehighlighter import CodeHighlighter
from blurdev.tools import ToolsEnvironment
import blurdev.gui.windows.loggerwindow
from blurdev.gui.windows.loggerwindow.errordialog import ErrorDialog

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

additionalInfoHtml = """<br><h3>Information</h3>
<br>
<div style="background:white;padding:5 10 5 10;border:1px black solid"><pre><code>
%(info)s
</code></pre></div>"""

additionalInfoTextile = """h3. Information

<pre><code class="Python">
%(info)s
</code></pre>"""

messageBodyHtml = """<ul>
<li><b>user: </b>%(username)s</li>
<li><b>host: </b>%(hostname)s</li>
<li><b>date: </b>%(date)s</li>
<li><b>python: </b>%(pythonversion)s</li>
<li><b>executable: </b>%(executable)s</li>
<li><b>blurdev core:</b> %(blurdevcore)s</li>
<li><b>blurdev env:</b> %(blurdevenv)s</li>
%(windowinfo)s
%(coremsg)s
%(bdevenvinfo)s
</ul>
<br>
<h3>Traceback Printout</h3>
<br>
%(error)s
%(additionalinfo)s"""

messageBodyTextile = """* *user:* %(username)s
* *host:* %(hostname)s
* *date:* %(date)s
* *python:* %(pythonversion)s
* *executable:* %(executable)s
* *blurdev core:* %(blurdevcore)s
* *blurdev env:* %(blurdevenv)s %(windowinfo)s %(coremsg)s %(bdevenvinfo)s

h3. Traceback Printout

<pre><code class="Python">
%(error)s</code></pre>

%(additionalinfo)s"""

messageBodyPlain = """user: %(username)s
host: %(hostname)s
date: %(date)s
python: %(pythonversion)s
executable: %(executable)s
blurdev core: %(blurdevcore)s
blurdev env: %(blurdevenv)s
%(windowinfo)s
%(coremsg)s
%(bdevenvinfo)s
Traceback Printout

%(error)s

%(additionalinfo)s"""

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
        <br>
        %(body)s
        <br><br>
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
    _excepthook = None
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

        # sys.__stdout__ and sys.__excepthook__ don't work if some third party has implemented their
        # own override. Use these to backup the current logger so the logger displays output, but
        # application specific consoles also get the info.
        self.stdout = None
        self.stderr = None
        ConsoleEdit._excepthook = None
        self._errorLog = None
        # overload the sys logger (if we are not on a high debugging level)
        if (
            os.path.basename(sys.executable) != 'python.exe'
            or debug.debugLevel() != debug.DebugLevel.High
        ):
            # Store the current outputs
            self.stdout = sys.stdout
            self.stderr = sys.stderr
            ConsoleEdit._excepthook = sys.excepthook
            # insert our own outputs
            sys.stdout = self
            sys.stderr = ErrorLog(self)
            self._errorLog = sys.stderr
            sys.excepthook = ConsoleEdit.excepthook

        # create the highlighter
        highlight = CodeHighlighter(self)
        highlight.setLanguage('Python')
        self.uiCodeHighlighter = highlight

        # If populated, also write to this interface
        self.outputPipe = None

        self._foregroundColor = QColor(Qt.black)
        self._stdoutColor = QColor(17, 154, 255)
        self._commentColor = QColor(0, 206, 52)
        self._keywordColor = QColor(17, 154, 255)
        self._stringColor = QColor(255, 128, 0)
        # These variables are used to enable pdb mode. This is a special mode used by the logger if
        # it is launched externally via getPdb, set_trace, or post_mortem in blurdev.debug.
        self._pdbPrompt = '(Pdb) '
        self._consolePrompt = '>>> '
        self._pdbMode = False
        # if populated when setPdbMode is called, this action will be enabled and its check state
        # will match the current pdbMode.
        self.pdbModeAction = None

        self._firstShow = True

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

    @staticmethod
    def highlightCodeHtml(code, lexer, style, linenos=False, divstyles=None):

        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import HtmlFormatter
        except Exception, e:
            print 'Could not import pygments, using old html formatting', str(e)
            htmlTemplate = """<div style="background:white;color:red;padding:5 10 5 10;border:1px black solid"><pre><code>
%(code)s
</code></pre></div>"""
            return htmlTemplate % {'code': code.replace('\n', '<br>')}

        lexer = lexer or 'python'
        style = style or 'colorful'
        defstyles = 'overflow:auto;width:auto;'
        if not divstyles:
            divstyles = (
                'border:solid gray;border-width:.1em .1em .1em .8em;padding:.2em .6em;'
            )

        formatter = HtmlFormatter(
            style=style,
            linenos=False,
            noclasses=True,
            cssclass='',
            cssstyles=defstyles + divstyles,
            prestyles='margin: 0',
        )
        html = highlight(code, get_lexer_by_name(lexer), formatter)
        if linenos:
            html = ConsoleEdit.insert_line_numbers(html)
        return html

    @staticmethod
    def insert_line_numbers(html):
        match = re.search('(<pre[^>]*>)(.*)(</pre>)', html, re.DOTALL)
        if not match:
            return html

        pre_open = match.group(1)
        pre = match.group(2)
        pre_close = match.group(3)

        html = html.replace(pre_close, '</pre></td></tr></table>')
        numbers = range(1, pre.count('\n') + 1)
        format = '%' + str(len(str(numbers[-1]))) + 'i'
        lines = '\n'.join(format % i for i in numbers)
        html = html.replace(
            pre_open,
            '<table><tr><td>' + pre_open + lines + '</pre></td><td>' + pre_open,
        )
        return html

    @staticmethod
    def excepthook(exctype, value, traceback_):
        """
        Logger Console excepthook. Re-implemented from sys.excepthook.  Catches
        all unhandled exceptions so that the user may be prompted that an error
        has occurred and can automatically show the Console view.		
        
        """
        # Print a new line before the traceback is printed. This ensures that the first line is not
        # printed on a prompt, and also provides seperation between tracebacks that makes it easier
        # to identify which traceback you are looking at when multiple tracebacks are received.
        print ''
        # Call the base implementation.  This generaly prints the traceback to stderr.
        if ConsoleEdit._excepthook:
            try:
                ConsoleEdit._excepthook(exctype, value, traceback_)
            except TypeError:
                # If the ConsoleEdit is no longer valid because it has been c++ garbage collected
                sys.__excepthook__(exctype, value, traceback_)
        else:
            sys.__excepthook__(exctype, value, traceback_)

        # Email the error traceback.
        emails = ToolsEnvironment.activeEnvironment().emailOnError()
        traceback_msg = ''.join(traceback.format_exception(exctype, value, traceback_))
        if emails:
            ConsoleEdit.emailError(emails, traceback_msg)

        # If the logger is not visible, prompt the user to show it.
        inst = blurdev.gui.windows.loggerwindow.LoggerWindow.instance()
        if (
            not inst.isVisible()
            and not blurdev.core.quietMode()
            and not ConsoleEdit._errorPrompted
        ):
            # This is used to ensure we only ever show a single error prompt. In special cases this
            # messagebox was showing multiple times, which is very annoying to the user.
            # This is not needed for normal Qt event loops, but if some other system (c++, threading)
            # raises multiple errors that get processed outside the standard qt event loop.
            ConsoleEdit._errorPrompted = True
            errorDialog = ErrorDialog(blurdev.core.rootWindow())
            errorDialog.setText(traceback_msg)
            errorDialog.exec_()

            # The messagebox was closed, so reset the tracking variable.
            ConsoleEdit._errorPrompted = False

        ConsoleEdit.clearAdditionalInfo()

    @staticmethod
    def buildErrorMessage(error, subject=None, information=None, format='html'):
        """
        Generates a email of the traceback, and useful information provided by the class if available.
        
            If the erroring class provides the following method, any text it returns will be included in the message under Additional Information
            |	def errorLog(self):
            |		return '[Additional text to include in email]'

        :param error: The error message to pass along
        :param information: if provided this string is included under the Information header of the provided email
        """
        if not error:
            return

        # get current user
        username = getpass.getuser()
        if not username:
            username = 'Anonymous'

        # get current host
        try:
            host = socket.gethostname()
        except:
            host = 'Unknown'

        # Build the message
        envName = blurdev.activeEnvironment().objectName()
        minfo = {}
        minfo['username'] = username
        minfo['hostname'] = host
        minfo['date'] = QDateTime.currentDateTime().toString('MMM dd, yyyy @ h:mm ap')
        minfo['pythonversion'] = sys.version.replace('\n', '')
        minfo['executable'] = sys.executable
        minfo['blurdevcore'] = blurdev.core.objectName()
        minfo['blurdevenv'] = '%s: %s' % (envName, blurdev.activeEnvironment().path())

        # notify where the error came from
        window = QApplication.activeWindow()
        className = ''

        # use the root application
        if window.__class__.__name__ == 'LoggerWindow':
            window = window.parent()
        elif window.__class__.__name__ == 'ErrorDialog':
            window = window.parent()

        minfo['windowinfo'] = ''
        if window:
            if format == 'html':
                windowinfo = '<li><b>window: </b>%s (from %s Class)</li>'
            elif format == 'textile':
                windowinfo = '\n* *window:* %s (from %s Class)'
            else:
                windowinfo = '\n%s (from %s Class)'
            minfo['windowinfo'] = windowinfo % (
                window.objectName(),
                window.__class__.__name__,
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

        minfo['coremsg'] = ''
        if coreMsg:
            if format == 'html':
                coremsg = '<li><b>blurdev.core Message:</b> %s</li>'
            elif format == 'textile':
                coremsg = '\n* *blurdev.core Message:* %s'
            else:
                coremsg = '\nblurdev.core Message: %s'
            minfo['coremsg'] = coremsg % coreMsg

        # Load in any aditional error info from the environment variables
        minfo['bdevenvinfo'] = ''
        prefix = 'BDEV_EMAILINFO_'
        for key in sorted(os.environ):
            if key.startswith(prefix):
                if format == 'html':
                    bdevenvinfo = '<li><b>%s:</b> %s</li>'
                elif format == 'textile':
                    bdevenvinfo = '\n* *%s:* %s'
                else:
                    bdevenvinfo = '\n%s: %s'

                minfo['bdevenvinfo'] += bdevenvinfo % (
                    key[len(prefix) :].replace('_', ' ').lower(),
                    os.environ[key],
                )

        if format == 'html':
            errorstr = ConsoleEdit.highlightCodeHtml(unicode(error), 'pytb', 'default')
        else:
            errorstr = unicode(error)
        minfo['error'] = errorstr

        # append any passed in body text
        minfo['additionalinfo'] = ''
        for info in (information, ConsoleEdit.additionalInfo()):
            if info is not None:
                if format == 'html':
                    addinfo = additionalInfoHtml % {
                        'info': unicode(info).replace('\n', '<br>')
                    }
                elif format == 'textile':
                    addinfo = additionalInfoTextile % {'info': unicode(info)}
                else:
                    addinfo = unicode(info)
                minfo['additionalinfo'] += addinfo

        # append extra stuff
        if hasattr(sys, 'last_traceback'):
            tb = sys.last_traceback
            if tb:
                frame = tb.tb_frame
                if frame:
                    module = frame.f_locals.get('self')
                    if module:
                        if hasattr(module, 'errorLog'):
                            try:
                                errorlog = module.errorLog()
                            except Exception, e:
                                modulename = frame.f_globals.get('__name__')
                                if not modulename:
                                    modulename = 'module'
                                errorlog = '%s.errorLog() generated an error: %s' % (
                                    modulename,
                                    str(e),
                                )
                            if format == 'html':
                                addinfo = additionalInfoHtml % {
                                    'info': unicode(errorlog).replace('\n', '<br>')
                                }
                            elif format == 'textile':
                                addinfo = additionalInfoTextile % {
                                    'info': unicode(errorlog)
                                }
                            else:
                                addinfo = unicode(errorlog)
                            minfo['additionalinfo'] += addinfo

        if format == 'html':
            message = messageBodyHtml % minfo
        elif format == 'textile':
            message = messageBodyTextile % minfo
        else:
            message = messageBodyPlain % minfo
        return subject, message

    @staticmethod
    def emailError(emails, error, subject=None, information=None):
        if not error:
            return

        # do not email when debugging
        if debug.debugLevel():
            return

        subject, message = ConsoleEdit.buildErrorMessage(error, subject, information)
        blurdev.core.sendEmail(
            'thePipe@blur.com',
            emails,
            subject,
            emailformat % {'subject': subject, 'body': message},
        )

    def executeCommand(self):
        """ executes the current line of code """
        # grab the command from the line
        block = self.textCursor().block().text()
        p = '{prompt}(.*)'.format(
            prompt=self.prompt().replace('(', '\(').replace(')', '\)')
        )
        results = re.search(p, unicode(block))
        if results:
            commandText = unicode(results.groups()[0])
            # if the cursor position is at the end of the line
            if self.textCursor().atEnd():
                # insert a new line
                self.insertPlainText('\n')

                if self._pdbMode:
                    if commandText:
                        import blurdev.external

                        blurdev.external.External(['pdb', '', {'msg': commandText}])
                    else:
                        # Sending a blank line to pdb will cause it to quit raising a exception.
                        # Most likely the user just wants to add some white space between their
                        # commands, so just add a new prompt line.
                        self.startInputLine()
                        self.insertPlainText(commandText)
                else:
                    # evaluate the command
                    cmdresult = None
                    try:
                        cmdresult = eval(
                            commandText, __main__.__dict__, __main__.__dict__
                        )
                    except:
                        exec (commandText) in __main__.__dict__, __main__.__dict__

                    # print the resulting commands
                    if cmdresult is not None:
                        self.write(unicode(cmdresult))

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
            block = unicode(cursor.block().text()).split()
            cursor.movePosition(QTextCursor.StartOfBlock, mode)
        # move the cursor to the end of the prompt.
        cursor.movePosition(QTextCursor.Right, mode, len(self.prompt()))
        self.setTextCursor(cursor)

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
        self.startInputLine()
        # Make sure the stylesheet recalculates for the new value
        blurdev.core.refreshStyleSheet()

    def prompt(self):
        if self._pdbMode:
            return self._pdbPrompt
        return self._consolePrompt

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
        self.moveCursor(QTextCursor.End)

        # if this is not already a new line
        if self.textCursor().block().text() != self.prompt():
            charFormat = QTextCharFormat()
            charFormat.setForeground(self.foregroundColor())
            self.setCurrentCharFormat(charFormat)

            inputstr = self.prompt()
            if unicode(self.textCursor().block().text()):
                inputstr = '\n' + inputstr

            self.insertPlainText(inputstr)

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

    # These methods are used to insert extra data into error reports when debugging hard to reproduce errors.
    @classmethod
    def additionalInfo(cls):
        return cls._additionalInfo

    @classmethod
    def clearAdditionalInfo(cls):
        cls.setAdditionalInfo(None)

    def resetAdditionalInfo(self):
        ConsoleEdit.clearAdditionalInfo()

    @classmethod
    def setAdditionalInfo(cls, info):
        cls._additionalInfo = info

    # These properties are used by the stylesheet to style various items.
    pyPdbMode = pyqtProperty(bool, pdbMode, setPdbMode)
    pyErrorMessageColor = pyqtProperty(QColor, errorMessageColor, setErrorMessageColor)
    pyForegroundColor = pyqtProperty(QColor, foregroundColor, setForegroundColor)
    pyStdoutColor = pyqtProperty(QColor, stdoutColor, setStdoutColor)
    pyCommentColor = pyqtProperty(QColor, commentColor, setCommentColor)
    pyKeywordColor = pyqtProperty(QColor, keywordColor, setKeywordColor)
    pyStringColor = pyqtProperty(QColor, stringColor, setStringColor)
