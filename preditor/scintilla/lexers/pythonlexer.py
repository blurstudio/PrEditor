from __future__ import absolute_import

from PyQt5.Qsci import QsciLexerPython
from Qt.QtGui import QColor


class PythonLexer(QsciLexerPython):
    # Items in this list will be highlighted using the color for
    # self.HighlightedIdentifier
    highlightedKeywords = ''

    def __init__(self, *args):
        super(PythonLexer, self).__init__(*args)

        # set the indentation warning
        self.setIndentationWarning(self.Inconsistent)

    def defaultPaper(self, style):
        if style == self.HighlightedIdentifier:
            # Set the highlight color for this lexer
            return QColor(155, 255, 155)
        return super(PythonLexer, self).defaultPaper(style)

    def keywords(self, keyset):
        # Words to be highlighted
        if keyset == 2 and self.highlightedKeywords:
            return self.highlightedKeywords
        ret = super(PythonLexer, self).keywords(keyset)
        if keyset == 1:
            ret += (
                ' True False abs divmod input open staticmethod all enumerate int ord '
                'str any eval isinstance pow sum basestring execfile'
                ' issubclass print super bin file iter property tuple bool filter len '
                'range type bytearray float list raw_input unichr'
                ' callable format locals reduce unicode chr frozenset long reload vars '
                'classmethod getattr map repr xrange cmp globals max'
                ' reversed zip compile hasattr memoryview round complex hash min set '
                'apply delattr help next setattr buffer dict hex object'
                ' slice coerce dir id oct sorted intern __import__'
            )
        return ret
