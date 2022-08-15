from __future__ import absolute_import

import json
import os
import re

from Qt.QtCore import QRegExp
from Qt.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat

from .. import resourcePath


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, widget):
        super(CodeHighlighter, self).__init__(widget)

        # setup the search rules
        self._keywords = []
        self._strings = []
        self._comments = []
        self._consoleMode = False
        # color storage
        self._commentColor = QColor(0, 206, 52)
        self._keywordColor = QColor(17, 154, 255)
        self._stringColor = QColor(255, 128, 0)
        self._resultColor = QColor(125, 128, 128)

        # setup the font
        font = widget.font()
        font.setFamily('Courier New')
        widget.setFont(font)

    def commentColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'commentColor'):
            return parent.commentColor()
        return self._commentColor

    def setCommentColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'setCommentColor'):
            parent.setCommentColor(color)
        self._commentColor = color

    def commentFormat(self):
        """returns the comments QTextCharFormat for this highlighter"""
        format = QTextCharFormat()
        format.setForeground(self.commentColor())
        format.setFontItalic(True)

        return format

    def isConsoleMode(self):
        """checks to see if this highlighter is in console mode"""
        return self._consoleMode

    def highlightBlock(self, text):
        """highlights the inputed text block based on the rules of this code
        highlighter"""
        if not self.isConsoleMode() or str(text).startswith('>>>'):
            # format the result lines
            format = self.resultFormat()
            parent = self.parent()
            if parent and hasattr(parent, 'outputPrompt'):
                self.highlightText(
                    text,
                    QRegExp('%s[^\\n]*' % re.escape(parent.outputPrompt())),
                    format,
                )

            # format the keywords
            format = self.keywordFormat()
            for kwd in self._keywords:
                self.highlightText(text, QRegExp(r'\b%s\b' % kwd), format)

            # format the strings
            format = self.stringFormat()
            for string in self._strings:
                self.highlightText(
                    text,
                    QRegExp('%s[^%s]*' % (string, string)),
                    format,
                    includeLast=True,
                )

            # format the comments
            format = self.commentFormat()
            for comment in self._comments:
                self.highlightText(text, QRegExp(comment), format)

    def highlightText(self, text, expr, format, offset=0, includeLast=False):
        """Highlights a text group with an expression and format

        Args:
            text (str): text to highlight
            expr (QRegExp): search parameter
            format (QTextCharFormat): formatting rule
            offset (int): number of characters to offset by when highlighting
            includeLast (bool): whether or not the last character should be highlighted
        """
        pos = expr.indexIn(text, 0)

        # highlight all the given matches to the expression in the text
        while pos != -1:
            pos = expr.pos(offset)
            length = len(expr.cap(offset))

            # use the last character if desired
            if includeLast:
                length += 1

            # set the formatting
            self.setFormat(pos, length, format)

            matched = expr.matchedLength()
            if includeLast:
                matched += 1

            pos = expr.indexIn(text, pos + matched)

    def keywordColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'keywordColor'):
            return parent.keywordColor()
        return self._keywordColor

    def setKeywordColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'setKeywordColor'):
            parent.setKeywordColor(color)
        self._keywordColor = color

    def keywordFormat(self):
        """returns the keywords QTextCharFormat for this highlighter"""
        format = QTextCharFormat()
        format.setForeground(self.keywordColor())

        return format

    def resultColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'resultColor'):
            return parent.resultColor()
        return self._resultColor

    def setResultColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'setResultColor'):
            parent.setResultColor(color)
        self._resultColor = color

    def resultFormat(self):
        """returns the result QTextCharFormat for this highlighter"""
        fmt = QTextCharFormat()
        fmt.setForeground(self.resultColor())
        return fmt

    def setConsoleMode(self, state=False):
        """sets the highlighter to only apply to console strings
        (lines starting with >>>)
        """
        self._consoleMode = state

    def setLanguage(self, lang):
        """sets the language of the highlighter by loading the json definition"""
        filename = resourcePath('lang/%s.json' % lang.lower())
        if os.path.exists(filename):
            data = json.load(open(filename))
            self.setObjectName(data.get('name', ''))
            self._keywords = data.get('keywords', [])
            self._comments = data.get('comments', [])
            self._strings = data.get('strings', [])

            return True
        return False

    def stringColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'stringColor'):
            return parent.stringColor()
        return self._stringColor

    def setStringColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'setStringColor'):
            parent.setStringColor(color)
        self._stringColor = color

    def stringFormat(self):
        """returns the keywords QTextCharFormat for this highligter"""
        format = QTextCharFormat()
        format.setForeground(self.stringColor())
        return format
