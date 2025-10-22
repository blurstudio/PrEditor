from __future__ import absolute_import

import keyword
import os
import re

from Qt.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat

from .. import resourcePath, utils


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, widget, language):
        super(CodeHighlighter, self).__init__(widget)
        self._consoleMode = False

        self.initHighlightVariables()
        self.setLanguage(language)

        self.defineHighlightVariables()

    def initHighlightVariables(self):
        """Initialize the variables which will be used in code highlighting"""

        # For each call of highlightBlock, keep track of the spans of each highlight, so
        # we can prevent overlapping spans (ie if a string is found, but it's within a
        # comment, do not highlight it).
        self.spans = []

        self._enabled = True

        # Language specific lists
        self._comments = []
        self._keywords = []
        self._strings = []

        # Patterns
        self._commentPattern = None
        self._keywordPattern = None
        self._resultPattern = None
        self._stringsPattern = None

        # Formats
        self._commentFormat = None
        self._keywordFormat = None
        self._resultFormat = None
        self._stringFormat = None

        # Colors. These may be overriden by parent colors, which themselves my be
        # overridden by stylesheets (ie Bright.css)
        self._commentColor = QColor(0, 206, 52)
        self._keywordColor = QColor(255, 0, 255)
        self._resultColor = QColor(125, 128, 128)
        self._stringColor = QColor(255, 128, 0)

    def enabled(self):
        return self._enabled

    def setEnabled(self, state):
        self._enabled = state

    def setLanguage(self, lang):
        """Sets the language of the highlighter by loading the json definition"""
        filename = resourcePath('lang/%s.json' % lang.lower())
        if os.path.exists(filename):
            data = utils.Json(filename).load()
            self.setObjectName(data.get('name', ''))

            self._comments = data.get('comments', [])
            self._strings = data.get('strings', [])

            # If using python, we can get keywords dynamically, otherwise get them from
            # the language json data.
            if lang.lower() == "python":
                self._keywords = keyword.kwlist
            else:
                self._keywords = data.get('keywords', [])

            return True
        return False

    def defineHighlightVariables(self):
        """Define the formats and regex patterns which will be used to highlight
        code."""
        # Define highlight formats
        self.defineCommentFormat()
        self.defineKeywordFormat()
        self.defineResultFormat()
        self.defineStringFormat()

        # Define highlight regex patterns
        self.defineCommentPattern()
        self.defineKeywordPattern()
        self.defineResultPattern()
        self.defineStringPattern()

    def highlightBlock(self, text):
        """Highlights the inputed text block based on the rules of this code
        highlighter"""

        if not self.enabled():
            return

        # Reset the highlight spans for this text block
        self.spans = []

        if not self.isConsoleMode() or str(text).startswith('>>>'):

            # We only have a result pattern if the parent has an attr "outputPrompt", so
            # only proceed if we have been able to define self._resultPattern.
            if self._resultPattern:
                self.highlightText(
                    text,
                    self._resultPattern,
                    self._resultFormat,
                )

            # Format the strings
            self.highlightText(
                text,
                self._stringPattern,
                self._stringFormat,
            )

            # format the comments
            self.highlightText(
                text,
                self._commentPattern,
                self._commentFormat,
            )

            # Format the keywords
            self.highlightText(
                text,
                self._keywordPattern,
                self._keywordFormat,
            )

    def highlightText(self, text, expr, format):
        """Highlights a text group with an expression and format

        Args:
            text (str): text to highlight
            expr (re.compile): search parameter
            format (QTextCharFormat): formatting rule
        """
        if expr is None or not text:
            return

        # highlight all the given matches to the expression in the text
        for match in expr.finditer(text):
            match_span = match.span()
            start, end = match_span
            length = end - start

            # Determine if the current highlight is within an already determined
            # highlight, if so, let's block it.
            blocked = False
            for span in self.spans:
                if start > span[0] and start < span[-1]:
                    blocked = True
                    break

            if not blocked:
                self.setFormat(start, length, format)

                # Append the current span to self.spans, so we can later block
                # new highlights which should be blocked
                self.spans.append(match_span)

    def isConsoleMode(self):
        """checks to see if this highlighter is in console mode"""
        return self._consoleMode

    def setConsoleMode(self, state=False):
        """sets the highlighter to only apply to console strings
        (lines starting with >>>)
        """
        self._consoleMode = state

    def commentColor(self):
        # Pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'commentColor'):
            return parent.commentColor
        return self._commentColor

    def setCommentColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'commentColor'):
            parent.commentColor = color
        self._commentColor = color

    def keywordColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'keywordColor'):
            return parent.keywordColor
        return self._keywordColor

    def setKeywordColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'keywordColor'):
            parent.keywordColor = color
        self._keywordColor = color

    def resultColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'resultColor'):
            return parent.resultColor
        return self._resultColor

    def setResultColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'resultColor'):
            parent.resultColor = color
        self._resultColor = color

    def stringColor(self):
        # pull the color from the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'stringColor'):
            return parent.stringColor
        return self._stringColor

    def setStringColor(self, color):
        # set the color for the parent if possible because this doesn't support
        # stylesheets
        parent = self.parent()
        if parent and hasattr(parent, 'stringColor'):
            parent.stringColor = color
        self._stringColor = color

    def defineCommentFormat(self):
        """Define the comment format based on the comment color"""
        self._commentFormat = QTextCharFormat()
        self._commentFormat.setForeground(self.commentColor())
        self._commentFormat.setFontItalic(True)

    def defineKeywordFormat(self):
        """Define the keyword format based on the keyword color"""
        self._keywordFormat = QTextCharFormat()
        self._keywordFormat.setForeground(self.keywordColor())

    def defineResultFormat(self):
        """Define the result format based on the result color"""
        self._resultFormat = QTextCharFormat()
        self._resultFormat.setForeground(self.resultColor())

    def defineStringFormat(self):
        """Define the string format based on the string color"""
        self._stringFormat = QTextCharFormat()
        self._stringFormat.setForeground(self.stringColor())

    def defineCommentPattern(self):
        """Define the regex pattern to use for comment"""
        pattern = "|".join(self._comments)
        self._commentPattern = re.compile(pattern)

    def defineKeywordPattern(self):
        """Define the regex pattern to use for keyword"""
        keywords = [r"\b{}\b".format(word) for word in self._keywords]
        pattern = "|".join(keywords)
        self._keywordPattern = re.compile(pattern)

    def defineResultPattern(self):
        """Define the regex pattern to use for results"""
        parent = self.parent()
        if parent and hasattr(parent, 'outputPrompt'):
            prompt = parent.outputPrompt()
            pattern = '{}[^\n]*'.format(prompt)
            self._resultPattern = re.compile(pattern)

    def defineStringPattern(self):
        """Define the regex pattern to use for strings."""
        lst = ["""{0}[^{0}\n]*{0}""".format(st) for st in self._strings]
        pattern = "|".join(lst)
        self._stringPattern = re.compile(pattern)
