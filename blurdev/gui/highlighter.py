##
# 	\namespace	blurdev.gui.highlighter
#
# 	\remarks	Defines the highlighter class for highlighting different text
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/12/08
#

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QRegExp

from PyQt4.QtGui import QColor
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat


class Highlighter(QSyntaxHighlighter):
    keywords = [
        'def',
        'class',
        'from',
        'import',
        'for',
        'in',
        'while',
        'True',
        'False',
        'pass',
        'try',
        'except',
        'self',
        'print',
    ]
    strings = ["'", '"']
    comments = ['#[^\n]*']

    def commentFormat(self):
        format = QTextCharFormat()
        format.setForeground(Qt.darkGreen)
        format.setFontItalic(True)

        return format

    def highlight(self, text, expr, format, offset=0, includeLast=False):
        pos = expr.indexIn(text, 0)

        while pos != -1:
            pos = expr.pos(offset)
            length = expr.cap(offset).length()

            if includeLast:
                length += 1

            self.setFormat(pos, length, format)

            matchedLength = expr.matchedLength()
            if includeLast:
                matchedLength += 1

            pos = expr.indexIn(text, pos + matchedLength)

    def highlightBlock(self, text):
        # Format Keywords
        format = self.keywordFormat()
        for keyword in Highlighter.keywords:
            self.highlight(text, QRegExp(r'\b' + keyword + r'\b'), format)

        # Format Strings
        format = self.stringFormat()
        for stringExp in Highlighter.strings:
            self.highlight(
                text,
                QRegExp(stringExp + '[^' + stringExp + ']*'),
                format,
                includeLast=True,
            )

        # Format Comments
        format = self.commentFormat()
        for definition in Highlighter.comments:
            self.highlight(text, QRegExp(definition), format)

    def keywordFormat(self):
        format = QTextCharFormat()
        format.setForeground(Qt.blue)

        return format

    def stringFormat(self):
        format = QTextCharFormat()
        format.setForeground(QColor(150, 75, 0))

        return format
