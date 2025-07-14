from __future__ import absolute_import

from Qt.QtGui import QColor

from .. import Qsci


class JavaScriptLexer(Qsci.QsciLexerJavaScript):
    # Items in this list will be highlighted using the color for
    # `Qsci.QsciLexerJavaScript.KeywordSet2`
    highlightedKeywords = ''

    def defaultFont(self, index):
        # HACK: TODO: I should probably preserve the existing fonts
        return self.font(0)

    def defaultPaper(self, style):
        if style == Qsci.QsciLexerJavaScript.KeywordSet2:
            # Set the highlight color for this lexer
            return QColor(155, 255, 155)
        return super(JavaScriptLexer, self).defaultPaper(style)

    def keywords(self, style):
        # Words to be highlighted
        if style == 2 and self.highlightedKeywords:
            return self.highlightedKeywords
        return super(JavaScriptLexer, self).keywords(style)
