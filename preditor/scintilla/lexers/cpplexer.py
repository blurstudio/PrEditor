from __future__ import absolute_import

from PyQt5.Qsci import QsciLexerCPP
from Qt.QtGui import QColor


class CppLexer(QsciLexerCPP):
    # Items in this list will be highlighted using the color for self.KeywordSet2
    highlightedKeywords = ''

    def defaultPaper(self, style):
        if style == self.CommentLine:
            # Set the highlight color for this lexer
            return QColor(155, 255, 155)
        return super(CppLexer, self).defaultPaper(style)

    def keywords(self, style):
        # Words to be highlighted
        if style == self.CommentLine and self.highlightedKeywords:
            return self.highlightedKeywords
        return super(CppLexer, self).keywords(style)
