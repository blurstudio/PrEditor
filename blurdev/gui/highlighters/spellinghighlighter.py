##
# 	\namespace	blurdev.gui.highlighters.spellinghighlighter
#
#   \remarks    Uses the enchant spell checking system to highlight incorrectly spelled
#               words
#
# 	\sa			http://www.rfk.id.au/software/pyenchant/download.html
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		11/12/08
#

from __future__ import absolute_import
from Qt.QtGui import QSyntaxHighlighter, QColor, QTextCharFormat
from Qt.QtWidgets import QMenu, QAction
from Qt.QtCore import QRegExp, Qt
from blurdev import debug
import string

# import aspell library
aspell = None
try:
    import aspell
except ImportError:
    debug.debugMsg(
        '[blurdev.gui.highlighters.spellinghighlighter] -'
        ' python aspell module could not be found'
    )


class SpellingHighlighter(QSyntaxHighlighter):
    def __init__(self, widget, language='en_US'):
        QSyntaxHighlighter.__init__(self, widget)

        # define custom properties
        self._active = False
        self._speller = None
        if aspell:
            try:
                self._speller = aspell.Speller()
            except Exception:
                debug.debugMsg(
                    '[blurdev.gui.highlighters.spellinghighlighter] -'
                    ' python aspell dictionary could not be found'
                )

        # set the dictionary language
        self.setLanguage(language)

    def currentWord(self):
        tc = self.parent().textCursor()
        tc.select(tc.WordUnderCursor)
        return tc.selectedText()

    def textCursorAt(self, pos):
        return self.parent().cursorForPosition(self.parent().mapFromGlobal(pos))

    def wordAt(self, pos):
        tc = self.textCursorAt(pos)
        tc.select(tc.WordUnderCursor)
        return tc.selectedText()

    def createMenuAction(self, menu, item, pos):
        def update():
            tc = self.textCursorAt(pos)
            tc.select(tc.WordUnderCursor)
            tc.insertText(item)

        act = menu.addAction(item)
        act.triggered.connect(update)

    def spellCheckMenu(self, parent, pos=None):
        if self.isValid() and self.isActive():
            if pos:
                word = self.wordAt(pos)
            else:
                word = self.currentWord()
            try:
                # Spell checker will error if a blank string is passed in.
                if word and not (
                    any(letter in string.digits for letter in word)
                    or self._speller.check(word)
                ):
                    menu = QMenu(word, parent)
                    items = self._speller.suggest(word)
                    if items:
                        for item in items:
                            self.createMenuAction(menu, item, pos)
                    else:
                        menu.addAction('No Suguestions')
                    return menu
            except Exception as e:
                # provide information about what word caused the error.
                e.args = e.args + ('asppell check error on word:"%s"' % word,)
                raise e
        return None

    def addWordToDict(self, word):
        self._speller.addtoPersonal(word)
        self._speller.saveAllwords()
        self.rehighlight()

    def createStandardSpellCheckMenu(self, event):
        menu = self.parent().createStandardContextMenu(event.globalPos())
        sm = self.spellCheckMenu(menu, event.globalPos())
        if sm:
            # Build menu from bottom -> top
            word = self.wordAt(event.globalPos())
            menu.insertSeparator(menu.actions()[0])
            qaction = QAction('Add %s to dictionary' % word, self.parent())
            qaction.triggered.connect(lambda: self.addWordToDict(word))
            qaction.setObjectName('uiSpellCheckAddWordACT')
            menu.insertMenu(menu.actions()[0], sm)
        return menu

    def isActive(self):
        """checks to see if this highlighter is in console mode"""
        return self._active

    def isValid(self):
        return aspell is not None and self._speller is not None

    def highlightBlock(self, txt):
        """highlights the inputed text block based on the rules of this code
        highlighter"""
        if self.isValid() and self.isActive():

            # create the format
            format = QTextCharFormat()
            format.setUnderlineColor(QColor(Qt.red))
            format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            format.setFontUnderline(True)

            # create the regexp
            expr = QRegExp(r'\S+\w')
            pos = expr.indexIn(txt, 0)
            # highlight all the given matches to the expression in the txt
            while pos != -1:
                pos = expr.pos()
                length = len(expr.cap())

                # extract the txt chunk for highlighting
                chunk = txt[pos : pos + length]

                if not (
                    any(letter in string.digits for letter in chunk)
                    or self._speller.check(chunk)
                ):
                    # set the formatting
                    self.setFormat(pos, length, format)

                # update the expression location
                matched = expr.matchedLength()
                pos = expr.indexIn(txt, pos + matched)

    def setActive(self, state=True):
        """sets the highlighter to only apply to console strings (lines starting with
        >>>)"""
        self._active = state
        self.rehighlight()

    def setLanguage(self, lang):
        """sets the language of the highlighter by loading"""
        if self.isValid():
            self._speller.setConfigKey("lang", lang)
            return True
        else:
            self._speller = None
            return False

    @staticmethod
    def test():

        from blurdev.gui import Dialog
        from Qt.QtWidgets import QTextEdit, QVBoxLayout

        dlg = Dialog()
        dlg.setWindowTitle('Spell Check Test')
        edit = QTextEdit(dlg)
        h = SpellingHighlighter(edit)
        h.setActive(True)
        layout = QVBoxLayout()
        layout.addWidget(edit)
        dlg.setLayout(layout)

        dlg.show()
