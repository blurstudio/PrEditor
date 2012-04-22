##
# 	\namespace	blurdev.ide.lexers.pythonlexer
#
# 	\remarks	Defines a class for parsing python files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.Qsci import QsciLexerPython
from PyQt4.QtGui import QColor


class PythonLexer(QsciLexerPython):
    # Items in this list will be highligheded using the color for self.HighlightedIdentifier
    highlightedKeywords = ''

    def __init__(self, *args):
        super(PythonLexer, self).__init__(*args)

        # set the indentation warning
        self.setIndentationWarning(self.Inconsistent)
        # Set the highlight color for this lexer
        self.setPaper(QColor(155, 255, 155), self.HighlightedIdentifier)

    def keywords(self, set):
        # Words to be highlighted
        if set == 2 and self.highlightedKeywords:
            return self.highlightedKeywords
        return super(PythonLexer, self).keywords(set)
