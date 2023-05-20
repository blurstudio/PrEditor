from __future__ import absolute_import

import re
from builtins import str as text

from future.utils import iteritems
from PyQt5.Qsci import QsciLexerCustom, QsciScintilla

MS_KEYWORDS = """
if then else not and or key collect
do while for in with where
function fn rollout struct parameters attributes exit continue
local global
true false
ok undefined unsupplied return
filein open close flush include print
"""


class MaxscriptLexer(QsciLexerCustom):
    # Items in this list will be highligheded using the color for self.SmartHighlight
    highlightedKeywords = ''

    def __init__(self, parent=None):
        QsciLexerCustom.__init__(self, parent)
        self._styles = {
            0: 'Default',
            1: 'Comment',
            2: 'CommentLine',
            3: 'Keyword',
            4: 'Operator',
            5: 'Number',
            6: 'String',
            7: 'SmartHighlight',
        }

        for key, value in iteritems(self._styles):
            setattr(self, value, key)

    def description(self, style):
        return self._styles.get(style, '')

    def defaultColor(self, style):
        from Qt.QtCore import Qt
        from Qt.QtGui import QColor

        if style in (self.Comment, self.CommentLine):
            return QColor(40, 160, 40)

        elif style in (self.Keyword, self.Operator):
            return QColor(Qt.blue)

        elif style == self.Number:
            return QColor(Qt.red)

        elif style == self.String:
            return QColor(180, 140, 30)

        return QsciLexerCustom.defaultColor(self, style)

    def defaultPaper(self, style):
        if style == self.SmartHighlight:
            from Qt.QtGui import QColor

            # Set the highlight color for this lexer
            return QColor(155, 255, 155)
        return super(MaxscriptLexer, self).defaultPaper(style)

    def font(self, style):
        font = super(MaxscriptLexer, self).font(style)
        if style in (self.Comment, self.CommentLine):
            font.setFamily('Arial Bold')
        return font

    def keywords(self, style):
        if style == self.Keyword:
            return MS_KEYWORDS
        if style == self.SmartHighlight:
            return self.highlightedKeywords
        return QsciLexerCustom.keywords(self, style)

    def processChunk(self, chunk, lastState, keywords):
        # process the length of the chunk
        if isinstance(chunk, bytearray):
            chunk = chunk.decode('utf8')
        length = len(chunk)

        # check to see if our last state was a block comment
        if lastState == self.Comment:
            pos = chunk.find('*/')
            if pos != -1:
                self.setStyling(pos + 2, self.Comment)
                return self.processChunk(chunk[pos + 2 :], self.Default, keywords)
            else:
                self.setStyling(length, self.Comment)
                return (self.Comment, 0)

        # check to see if our last state was a string
        elif lastState == self.String:
            # remove special case backslashes
            while r'\\' in chunk:
                chunk = chunk.replace(r'\\', '||')

            # remove special case strings
            while r'\"' in chunk:
                chunk = chunk.replace(r'\"', r"\'")

            pos = chunk.find('"')
            if pos != -1:
                self.setStyling(pos + 1, self.String)
                return self.processChunk(chunk[pos + 1 :], self.Default, keywords)
            else:
                self.setStyling(length, self.String)
                return (self.String, 0)

        # otherwise, process a default chunk
        else:
            blockpos = chunk.find('/*')
            linepos = chunk.find('--')
            strpos = chunk.find('"')
            order = [blockpos, linepos, strpos]
            order.sort()

            # any of the above symbols will affect how a symbol following it is treated,
            # so make sure we process in the proper order
            for i in order:
                if i == -1:
                    continue

                # process a string
                if i == strpos:
                    state, folding = self.processChunk(chunk[:i], lastState, keywords)
                    self.setStyling(1, self.String)
                    newstate, newfolding = self.processChunk(
                        chunk[i + 1 :], self.String, keywords
                    )
                    return (newstate, newfolding + folding)

                # process a line comment
                elif i == linepos:
                    state, folding = self.processChunk(chunk[:i], lastState, keywords)
                    self.setStyling(length - i, self.CommentLine)
                    return (self.Default, folding)

                # process a block comment
                elif i == blockpos:
                    state, folding = self.processChunk(chunk[:i], lastState, keywords)
                    self.setStyling(2, self.Comment)
                    newstate, newfolding = self.processChunk(
                        chunk[i + 2 :], self.Comment, keywords
                    )
                    return (newstate, newfolding + folding)

            # otherwise, we are processing a default set of text whose syntaxing is
            # irrelavent from the previous one TODO: this needs to handle QStrings.
            # However I do not thing QStrings are the problem, its more likely a
            # bytearray problem. the conversion at the start of this function may have
            # resolved it.
            results = self.chunkRegex.findall(chunk)
            for space, kwd in results:
                if not (space or kwd):
                    break

                self.setStyling(len(space), self.Default)

                if kwd.lower() in self.hlkwords:
                    self.setStyling(len(kwd), self.SmartHighlight)
                elif kwd.lower() in keywords:
                    self.setStyling(len(kwd), self.Keyword)
                else:
                    self.setStyling(len(kwd), self.Default)

            # in this context, look for opening and closing parenthesis which will
            # determine folding scope
            return (self.Default, chunk.count('(') - chunk.count(')'))

    def styleText(self, start, end):
        editor = self.editor()
        if not editor:
            return

        # scintilla works with encoded bytes, not decoded characters
        # this matters if the source contains non-ascii characters and
        # a multi-byte encoding is used (e.g. utf-8)
        source = ''
        if end > editor.length():
            end = editor.length()

        # define commonly used methods
        SCI = editor.SendScintilla
        SETFOLDLEVEL = QsciScintilla.SCI_SETFOLDLEVEL
        HEADERFLAG = QsciScintilla.SC_FOLDLEVELHEADERFLAG
        CURRFOLDLEVEL = QsciScintilla.SC_FOLDLEVELBASE

        if end > start:
            source = bytearray(end - start)
            editor.SendScintilla(editor.SCI_GETTEXTRANGE, start, end, source)

        if not source:
            return
        self.parent().blockSignals(True)

        # the line index will also need to implement folding
        index = editor.SendScintilla(editor.SCI_LINEFROMPOSITION, start)
        if index > 0:
            # the previous state may be needed for multi-line styling
            pos = editor.SendScintilla(editor.SCI_GETLINEENDPOSITION, index - 1)
            lastState = editor.SendScintilla(editor.SCI_GETSTYLEAT, pos)
        else:
            lastState = self.Default

        self.startStyling(start, 0x1F)

        # cache objects used by processChunk that do not need updated every time it is
        # called
        self.hlkwords = set(text(self.keywords(self.SmartHighlight)).lower().split())
        self.chunkRegex = re.compile('([^A-Za-z0-9]*)([A-Za-z0-9]*)')
        kwrds = set(MS_KEYWORDS.split())

        # scintilla always asks to style whole lines
        for line in source.splitlines(True):
            lastState, folding = self.processChunk(line, lastState, kwrds)

            # open folding levels
            if folding > 0:
                SCI(SETFOLDLEVEL, index, CURRFOLDLEVEL | HEADERFLAG)
                CURRFOLDLEVEL += folding
            else:
                SCI(SETFOLDLEVEL, index, CURRFOLDLEVEL)
                CURRFOLDLEVEL += folding

            # folding implementation goes here
            index += 1
        self.parent().blockSignals(False)
