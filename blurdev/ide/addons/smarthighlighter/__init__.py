##
#   \namespace  python.blurdev.ide.addons.smarthighlighter
#
#   \remarks    Pythonic implementation of the Smart Highlighter from Notepad++. Original C++ code can be downloaded at http://notepad-plus-plus.org
# 				This uses a subclassed lexer to acomplish highlighting.
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       04/21/12
#

from blurdev.ide.ideaddon import IdeAddon
from blurdev.ide.lexers.pythonlexer import PythonLexer
import re


class SmartHighlighterAddon(IdeAddon):
    def activate(self, ide):
        # Create a place to store the signal functions so they can be disconnected when deactivated
        self._connectedFunctions = []
        self.setValidatorRegEx()
        ide.editorCreated.connect(self.connectToEditor)
        # connect to all open documents
        for editor in ide.documents():
            self.connectToEditor(editor)
        return True

    def connectToEditor(self, editor):
        r"""
            \remarks	Create the neccissary connections for this plugin and store the neccissary information so we can disconnect when the 
                        plugin is deactivated.
        """
        if isinstance(editor.lexer(), PythonLexer):

            def selectionChanged():
                self.highlightView(editor)

            self._connectedFunctions.append((editor, selectionChanged))
            editor.selectionChanged.connect(selectionChanged)

    def deactivate(self, ide):
        for editor, fnc in self._connectedFunctions[:]:
            # Disconnect from the editor and remove internal reffrences
            editor.selectionChanged.disconnect(fnc)
            self._connectedFunctions.remove((editor, fnc))
            # disable any active syntax highlighting
            lexer = editor.lexer()
            lexer.highlightedKeywords = ''
            editor.setLexer(lexer)
        ide.editorCreated.disconnect(self.connectToEditor)
        return True

    def highlightView(self, view):
        # Get selection
        selectedText = view.selectedText()
        # if text is selected make sure it is a word
        if selectedText:
            # Does the text contain a non allowed word?
            if not self.isWord(selectedText):
                return
            else:
                selection = view.getSelection()
                # the character before and after the selection must not be a word.
                text = view.text(selection[2])  # Character after
                if selection[3] < len(text):
                    if self.isWord(text[selection[3]]):
                        return
                text = view.text(selection[0])  # Character Before
                if selection[1] and selection[1] != -1:
                    if self.isWord(text[selection[1] - 1]):
                        return
        # Make the lexer highlight words
        lexer = view.lexer()
        try:
            lexer.highlightedKeywords = selectedText
            view.setLexer(lexer)
        except AttributeError:
            pass

    def isWord(self, word):
        r"""
            \remarks	Uses self.validator.findAll to check the passed in string. Returns True if no results were found
            \return		<bool>
        """
        return self.validator.findall(word) == []

    def setValidatorRegEx(self, exp='[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>\']'):
        r"""
            \remarks	Set the regular expression used to control if a selection is considered valid for
                        smart highlighting.
            \param		exp		<str>	Defaul:'[ \t\n\r\.,?;:!()\[\]+\-\*\/#@^%$"\\~&{}|=<>]'
        """
        self._validatorRegEx = exp
        self.validator = re.compile(exp)

    def validatorRegEx(self):
        return self._validatorRegEx


# register the addon to the system
IdeAddon.register('Smart Highlighter', SmartHighlighterAddon)

# create the init method (in case this addon doesn't get registered as part of a group)
def init():
    pass
