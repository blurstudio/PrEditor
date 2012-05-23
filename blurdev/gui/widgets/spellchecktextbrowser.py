##
#   \namespace  python.blurdev.gui.widgets.spellchecktextbrowser
#
#   \remarks    A QTextBrowser with SpellingHighlighter with SpellingHighlighter suguestions integrated into the right click menu.
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       05/22/12
#

from blurdev.gui.highlighters.spellinghighlighter import SpellingHighlighter
from PyQt4.QtGui import QTextBrowser


class SpellCheckTextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super(SpellCheckTextBrowser, self).__init__(parent)
        self.spellChecker = SpellingHighlighter(self)
        self.spellChecker.setActive(True)

    def contextMenuEvent(self, event):
        menu = self.spellChecker.createStandardSpellCheckMenu(event)
        menu.exec_(event.globalPos())
