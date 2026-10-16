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

        if self.isConsoleMode() and not text.startswith('>>>'):
            return

        pattern = self._highlightPattern
        if pattern is None:
            pattern = self.defineHighlightPattern()

        # Map the named groups of the combined pattern to their formats
        formats = {
            "result": self._resultFormat,
            "string": self._stringFormat,
            "comment": self._commentFormat,
            "keyword": self._keywordFormat,
        }

        # The combined pattern finds the leftmost highlight first and continues
        # searching after it. This prevents highlighting text inside of an
        # existing highlight, for example a keyword inside a string or comment.
        setFormat = self.setFormat
        for match in pattern.finditer(text):
            start, end = match.span()
            setFormat(start, end - start, formats[match.lastgroup])

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
        self._highlightPattern = None

    def defineHighlightPattern(self):
        """Combine the result, string, comment and keyword patterns into a
        single regex pattern with a named group for each. Searching once with
        this pattern is much faster than searching for each pattern separately.

        Returns:
            re.Pattern: The combined pattern, also stored on this instance.
        """
        parts = []
        for name, expr in (
            ("result", self._resultPattern),
            ("string", self._stringPattern),
            ("comment", self._commentPattern),
            ("keyword", self._keywordPattern),
        ):
            # Patterns that match empty text would prevent the other patterns
            # from matching so skip them, they wouldn't highlight anything.
            if expr is not None and expr.pattern:
                parts.append(f"(?P<{name}>{expr.pattern})")

        # If there is nothing to highlight, use a pattern that never matches.
        self._highlightPattern = re.compile("|".join(parts) or "(?!)")
        return self._highlightPattern

    def defineKeywordPattern(self):
        """Define the regex pattern to use for keyword"""
        pattern = ""
        if self._keywords:
            keywords = "|".join(self._keywords)
            pattern = rf"\b(?:{keywords})\b"
        self._keywordPattern = re.compile(pattern)
        self._highlightPattern = None

    def defineResultPattern(self):
        """Define the regex pattern to use for results"""
        parent = self.parent()
        if parent and hasattr(parent, 'outputPrompt'):
            prompt = parent.outputPrompt()
            pattern = '{}[^\n]*'.format(prompt)
            self._resultPattern = re.compile(pattern)
            self._highlightPattern = None

    def defineStringPattern(self):
        """Define the regex pattern to use for strings."""
        lst = ["""{0}[^{0}\n]*{0}""".format(st) for st in self._strings]
        pattern = "|".join(lst)
        self._stringPattern = re.compile(pattern)
        self._highlightPattern = None
