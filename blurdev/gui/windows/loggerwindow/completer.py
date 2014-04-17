##
# 	\namespace	blurapi.gui.windows.loggerwindow.completer
#
# 	\remarks	Custom Python completer for the logger
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/15/08
#

import inspect

from PyQt4.QtCore import pyqtSignal, SIGNAL, Qt
from PyQt4.QtGui import (
    QStringListModel,
    QToolTip,
    QCursor,
    QCompleter,
    QMessageBox as msg,
)


class PythonCompleter(QCompleter):
    def __init__(self, widget):
        QCompleter.__init__(self, widget)

        # use the python model for information
        self.setModel(QStringListModel())

        self._currentText = ''
        self._enabled = True

        # update this completer
        self.setWidget(widget)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitive)

        self.connect(self, SIGNAL('highlighted(const QString &)'), self.setCurrentText)

    def currentCompletion(self):
        return self._currentText

    def currentObject(self, scope=None, docMode=False):
        if self._enabled:
            word = self.textUnderCursor()
            # determine if we are in docMode or not
            if word.endswith('(') and not docMode:
                return None

            word = word.rstrip('(')
            split = unicode(word).split('.')

            # make sure there is more than 1 item for this symbol
            if len(split) > 1 or docMode:
                if not docMode:
                    symbol = '.'.join(split[:-1])
                    prefix = split[-1]
                else:
                    symbol = word
                    prefix = ''

                # try to evaluate the object to pull out the keys
                keys = []
                object = None
                try:
                    object = eval(symbol, scope)
                except:
                    pass

                if not object:
                    import sys

                    if symbol in sys.modules:
                        object = sys.modules[symbol]

                return (object, prefix)
        return (None, '')

    def enabled(self):
        return self._enabled

    def hideDocumentation(self):
        QToolTip.hideText()

    def refreshList(self, scope=None):
        """ refreshes the string list based on the cursor word """
        object, prefix = self.currentObject(scope)
        self.model().setStringList([])
        # Only show hidden method/variable names if the hidden character '_' is typed in.
        if prefix.startswith('_'):
            keys = [key for key in dir(object) if key.startswith('_')]
        else:
            keys = [key for key in dir(object) if not key.startswith('_')]
        keys.sort()
        self.model().setStringList(keys)
        self.setCompletionPrefix(prefix)

    def clear(self):
        self.popup().hide()
        self.hideDocumentation()

    def showDocumentation(self, pos=None, scope=None):
        # hide the existing popup widget
        self.popup().hide()

        # create the default position
        if pos == None:
            pos = QCursor.pos()

        # collect the object
        object, prefix = self.currentObject(scope, docMode=True)
        if object:
            docs = inspect.getdoc(object)
            if docs:
                QToolTip.showText(pos, docs)

    def setCurrentText(self, text):
        self._currentText = text

    def setEnabled(self, state):
        self._enabled = state

    def textUnderCursor(self, useParens=False):
        """ pulls out the text underneath the cursor of this items widget """
        from PyQt4.QtGui import QTextCursor

        cursor = self.widget().textCursor()
        cursor.select(QTextCursor.WordUnderCursor)

        # grab the selected word
        word = cursor.selectedText()
        block = unicode(cursor.block().text())

        # lookup previous words using '.'
        pos = cursor.position() - cursor.block().position() - len(word) - 1

        import re

        while -1 < pos:
            char = block[pos]
            if not re.match('^[a-zA-Z0-9_\.\(\)]$', char):
                break
            word = char + word
            pos -= 1

        return str(word)
