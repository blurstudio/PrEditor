from __future__ import absolute_import

from PyQt5.Qsci import QsciLexerCPP
from Qt.QtGui import QColor

MU_KEYWORDS = """
method string Color use require module for_each let global function nil void
"""


class MuLexer(QsciLexerCPP):
    # Items in this list will be highlighted using the color for self.KeywordSet2
    highlightedKeywords = ''

    def defaultPaper(self, style):
        if style == self.CommentLine:
            # Set the highlight color for this lexer
            return QColor(155, 255, 155)
        return super(MuLexer, self).defaultPaper(style)

    def keywords(self, style):
        # Words to be highlighted
        if style == self.CommentLine and self.highlightedKeywords:
            return self.highlightedKeywords

        output = super(MuLexer, self).keywords(style)
        # for some reason, CPP lexer uses comment style for
        # its keywords
        if style == self.Comment:
            output += MU_KEYWORDS

        return output
