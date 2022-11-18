from __future__ import absolute_import

import inspect
import re
import sys
from enum import Enum

from Qt.QtCore import QRegExp, QSortFilterProxyModel, QStringListModel, Qt
from Qt.QtGui import QCursor, QTextCursor
from Qt.QtWidgets import QCompleter, QToolTip


class CompleterMode(Enum):
    """
    Enum which defines the available Completer Modes

    STARTS_WITH - (Default) Matches completions which start with the typed input
                    regex = "^SampleInput.*"
    OUTER_FUZZY - Matches completions which contain, but don't necessarily
                    start with, the typed input
                    regex = ".*SampleInput.*"
    FULL_FUZZY - Matches completions which contain the characters of the typed input,
                    in order, regardless of other characters intermixed
                    regex = ".*S.*a.*m.*p.*l.*e.*I.*n.*p.*u.*t.*"

    Matches respect case-sensitivity, which is set separately
    """

    STARTS_WITH = 0
    OUTER_FUZZY = 1
    FULL_FUZZY = 2

    def displayName(self):
        return self.name.replace('_', ' ').title()

    def toolTip(self):
        toolTipMap = {
            'STARTS_WITH': "'all' matches 'allowtabs', does not match 'findallnames'",
            'OUTER_FUZZY': "'all' matches 'getallobjs', does not match 'anylonglist'",
            'FULL_FUZZY': "'all' matches 'getallobjs', also matches 'anylonglist'",
        }
        return toolTipMap.get(self.name, "")


class PythonCompleter(QCompleter):
    def __init__(self, widget):
        super(PythonCompleter, self).__init__(widget)

        # use the python model for information

        self._enabled = True

        # update this completer
        self.setWidget(widget)

        self.setCaseSensitive()
        self.setCompleterMode()
        self.buildCompleter()

        self.wasCompleting = False
        self.wasCompletingCounter = 0
        self.wasCompletingCounterMax = 1

    def setCaseSensitive(self, caseSensitive=True):
        """Set case sensitivity for completions"""
        self._sensitivity = Qt.CaseSensitive if caseSensitive else Qt.CaseInsensitive
        self.buildCompleter()

    def caseSensitive(self):
        """Return current case sensitivity state for completions"""
        caseSensitive = self._sensitivity == Qt.CaseSensitive
        return caseSensitive

    def setCompleterMode(self, completerMode=CompleterMode.STARTS_WITH):
        """Set completer mode"""
        self._completerMode = completerMode

    def completerMode(self):
        """Return current completer mode"""
        return self._completerMode

    def buildCompleter(self):
        """
        Build the completer to allow for wildcards and set
        case sensitivity to use
        """
        model = QStringListModel()
        self.filterModel = QSortFilterProxyModel(self.parent())
        self.filterModel.setSourceModel(model)
        self.filterModel.setFilterCaseSensitivity(self._sensitivity)
        self.setModel(self.filterModel)
        self.setCompletionMode(QCompleter.UnfilteredPopupCompletion)

    def currentObject(self, scope=None, docMode=False):
        if self._enabled:
            word = self.textUnderCursor()

            # determine if we are in docMode or not
            if word.endswith('(') and not docMode:
                return (None, '')

            word = word.rstrip('(')
            split = word.split('.')

            # make sure there is more than 1 item for this symbol
            if len(split) > 1 or docMode:
                if not docMode:
                    symbol = '.'.join(split[:-1])
                    prefix = split[-1]
                else:
                    symbol = word
                    prefix = ''

                # try to evaluate the object to pull out the keys
                object = None
                try:
                    object = eval(symbol, scope)
                except Exception:
                    pass

                if object is None:
                    if symbol in sys.modules:
                        object = sys.modules[symbol]

                return (object, prefix)
        return (None, '')

    def enabled(self):
        return self._enabled

    def hideDocumentation(self):
        QToolTip.hideText()

    def refreshList(self, scope=None):
        """refreshes the string list based on the cursor word"""
        object, prefix = self.currentObject(scope)

        # Only show hidden method/variable names if the hidden character '_' is typed
        # in.
        try:
            if prefix.startswith('_'):
                keys = [key for key in dir(object) if key.startswith('_')]
            else:
                keys = [key for key in dir(object) if not key.startswith('_')]
        except AttributeError:
            keys = []
        keys.sort()
        self.model().sourceModel().setStringList(keys)

        regExStr = ""
        if self._completerMode == CompleterMode.STARTS_WITH:
            regExStr = "^{}.*".format(prefix)
        if self._completerMode == CompleterMode.OUTER_FUZZY:
            regExStr = ".*{}.*".format(prefix)
        if self._completerMode == CompleterMode.FULL_FUZZY:
            regExStr = ".*".join(prefix)

        regexp = QRegExp(regExStr, self._sensitivity)
        self.filterModel.setFilterRegExp(regexp)

    def clear(self):
        self.popup().hide()
        self.hideDocumentation()

        self.wasCompletingCounter = 0
        self.wasCompleting = False

    def showDocumentation(self, pos=None, scope=None):
        # hide the existing popup widget
        self.popup().hide()

        # create the default position
        if pos is None:
            pos = QCursor.pos()

        # collect the object
        object, prefix = self.currentObject(scope, docMode=True)

        # not all objects allow `if object`, so catch any errors
        # Specifically, numpy arrays fail with ValueError here
        try:
            if object:
                docs = inspect.getdoc(object)
                if docs:
                    QToolTip.showText(pos, docs)
        except Exception:
            pass

    def setEnabled(self, state):
        self._enabled = state

    def textUnderCursor(self, useParens=False):
        """pulls out the text underneath the cursor of this items widget"""

        cursor = self.widget().textCursor()
        cursor.select(QTextCursor.WordUnderCursor)

        # grab the selected word
        word = cursor.selectedText()
        block = cursor.block().text()

        # lookup previous words using '.'
        pos = cursor.position() - cursor.block().position() - len(word) - 1

        while -1 < pos:
            char = block[pos]
            if not re.match(r"^[a-zA-Z0-9_\.\(\)'\"]$", char):
                break
            word = char + word
            pos -= 1

        # If the word starts with a opening parentheses, remove it if there is not a
        # matching closing one.
        if word and word[0] == '(':
            count = 0
            # use a simple instance count to check if the opening parentheses is closed
            for char in word:
                if char == '(':
                    count += 1
                elif char == ')':
                    count -= 1
            if count:
                # the opening parentheses is not closed, remove it
                word = word[1:]

        return str(word)
