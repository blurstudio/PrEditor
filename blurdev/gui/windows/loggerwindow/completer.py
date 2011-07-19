##
# 	\namespace	blurapi.gui.windows.loggerwindow.completer
#
# 	\remarks	Custom Python completer for the logger
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		01/15/08
#

from PyQt4.QtCore import pyqtSignal, SIGNAL
from PyQt4.QtGui import QCompleter
from PyQt4.QtGui import QStringListModel


class PythonCompleter(QCompleter):
    def __init__(self, widget):
        QCompleter.__init__(self, widget)

        # use the python model for information
        self.setModel(QStringListModel())

        self._currentText = ''

        # update this completer
        from PyQt4.QtCore import Qt

        self.setWidget(widget)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitive)

        self.connect(self, SIGNAL('highlighted(const QString &)'), self.setCurrentText)

    def currentCompletion(self):
        return self._currentText

    def refreshList(self, scope=None):
        """ refreshes the string list based on the cursor word """
        word = self.textUnderCursor()
        split = unicode(word).split('.')

        # make sure there is more than 1 item for this symbol
        if len(split) > 1:
            symbol = '.'.join(split[:-1])
            prefix = split[-1]

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

            # pull the keys from the object
            if object:
                import inspect

                # Collect non-hidden method/variable names
                keys = [key for key in dir(object) if not key.startswith('_')]
                keys.sort()

                self.model().setStringList(keys)
                self.setCompletionPrefix(prefix)
            else:
                self.model().setStringList([])
        else:
            self.model().setStringList([])

    def setCurrentText(self, text):
        self._currentText = text

    def textUnderCursor(self):
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
            if not re.match('[a-zA-Z0-9\.]', char):
                break
            word = char + word
            pos -= 1

        return word
