##
# 	\namespace	blurdev.ide.lexers.maxscriptlexer
#
# 	\remarks	Defines a class for parsing maxscript files

#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#


import re

from PyQt4.Qsci import QsciLexerCustom


MS_KEYWORDS = """

if then else not

do while for in with where

function fn rollout struct parameters attributes exit continue

local global

true false

ok undefined unsupplied return

filein open close flush include print

"""


class MaxscriptLexer(QsciLexerCustom):
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
        }

        for key, value in self._styles.iteritems():

            setattr(self, value, key)

    def description(self, style):

        return self._styles.get(style, '')

    def defaultColor(self, style):

        from PyQt4.QtGui import QColor

        from PyQt4.QtCore import Qt

        if style in (self.Comment, self.CommentLine):

            return QColor(50, 180, 50)

        elif style in (self.Keyword, self.Operator):

            return QColor(Qt.blue)

        elif style == self.Number:

            return QColor(Qt.red)

        elif style == self.String:

            return QColor(180, 140, 30)

        return QsciLexerCustom.defaultColor(self, style)

    def keywords(self, style):

        if style == self.Keyword:

            return MS_KEYWORDS

        return QsciLexerCustom.keywords(self, style)

    def processChunk(self, chunk, lastState, keywords):

        # process the length of the chunk

        length = len(chunk)

        # check to see if our last state was a block comment

        if lastState == self.Comment:

            pos = chunk.find('*/')

            if pos != -1:

                self.setStyling(pos + 2, self.Comment)

                return self.processChunk(chunk[pos + 2 :], self.Default, keywords)

            else:

                self.setStyling(length, self.Comment)

                return self.Comment

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

                return self.String

        # otherwise, process a default chunk

        else:

            blockpos = chunk.find('/*')

            linepos = chunk.find('--')

            strpos = chunk.find('"')

            # process a string

            if (
                strpos != -1
                and (blockpos == -1 or strpos < blockpos)
                and (linepos == -1 or strpos < linepos)
            ):

                self.processChunk(chunk[:strpos], lastState, keywords)

                self.setStyling(1, self.String)

                return self.processChunk(chunk[strpos + 1 :], self.String, keywords)

            # process a line comment

            elif (
                linepos != -1
                and (blockpos == -1 or linepos < blockpos)
                and (strpos == -1 or linepos < strpos)
            ):

                self.processChunk(chunk[:linepos], lastState, keywords)

                self.setStyling(length - linepos, self.CommentLine)

                return self.CommentLine

            # process a block comment

            elif (
                blockpos != -1
                and (linepos == -1 or blockpos < linepos)
                and (strpos == -1 or blockpos < strpos)
            ):

                self.processChunk(chunk[:blockpos], lastState, keywords)

                self.setStyling(2, self.Comment)

                return self.processChunk(chunk[blockpos + 2 :], self.Comment, keywords)

            # process a clean bit of text

            else:

                results = re.findall('([^A-Za-z0-9]*)([A-Za-z0-9]*)', chunk)

                for space, kwd in results:

                    if not (space or kwd):

                        break

                    self.setStyling(len(space), self.Default)

                    if kwd in keywords:

                        self.setStyling(len(kwd), self.Keyword)

                    else:

                        self.setStyling(len(kwd), self.Default)

                return self.Default

    def styleText(self, start, end):

        editor = self.editor()

        if not editor:

            return

        import sys

        # scintilla works with encoded bytes, not decoded characters

        # this matters if the source contains non-ascii characters and

        # a multi-byte encoding is used (e.g. utf-8)

        source = ''

        if end > editor.length():

            end = editor.length()

        # define commonly used methods

        from PyQt4.Qsci import QsciScintilla

        SCI = editor.SendScintilla

        SETFOLDLEVEL = QsciScintilla.SCI_SETFOLDLEVEL
        HEADERFLAG = QsciScintilla.SC_FOLDLEVELHEADERFLAG

        CURRFOLDLEVEL = QsciScintilla.SC_FOLDLEVELBASE

        if end > start:

            if sys.hexversion >= 0x02060000:

                # faster when styling big files, but needs python 2.6

                source = bytearray(end - start)

                editor.SendScintilla(editor.SCI_GETTEXTRANGE, start, end, source)

            else:

                source = unicode(editor.text()).encode('utf-8')[start:end]

        if not source:

            return

        # the line index will also need to implement folding

        index = editor.SendScintilla(editor.SCI_LINEFROMPOSITION, start)

        if index > 0:

            # the previous state may be needed for multi-line styling

            pos = editor.SendScintilla(editor.SCI_GETLINEENDPOSITION, index - 1)

            lastState = editor.SendScintilla(editor.SCI_GETSTYLEAT, pos)

        else:

            lastState = self.Default

        self.startStyling(start, 0x1F)

        # scintilla always asks to style whole lines

        lastIndent = ''

        import re

        for line in source.splitlines(True):

            lastState = self.processChunk(line, lastState, MS_KEYWORDS.split())

            # handle folding alla python, based on the spaces at the front of the line

            results = re.match('([ \t]*)', line)

            indent = results.groups()[0].replace('\t', ' ')

            diff = len(indent) - len(lastIndent)

            lastIndent = indent

            # show the collapse level

            if diff > 0:

                SCI(SETFOLDLEVEL, index - 1, CURRFOLDLEVEL | HEADERFLAG)

            # update the current fold level

            CURRFOLDLEVEL += diff

            if lastIndent:

                SCI(SETFOLDLEVEL, index, CURRFOLDLEVEL)

            # folding implementation goes here

            index += 1
