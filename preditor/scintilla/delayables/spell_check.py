from __future__ import absolute_import, print_function

import logging
import re
import string

from PyQt5.Qsci import QsciScintilla
from Qt.QtCore import Qt
from Qt.QtGui import QColor

from ...delayable_engine.delayables import RangeDelayable
from .. import lang

logger = logging.getLogger(__name__)


try:  # noqa: C901
    import aspell
except ImportError:
    # if we can't import aspell don't define the SpellCheckDelayable class
    logger.debug('Unable to import aspell')
else:

    class SpellCheckDelayable(RangeDelayable):
        """Spell check some text in the document.

        IF the document is not visible, the spell check will be skipped.

        Loop Args:
            start_pos (int): The document position to start spell checking.
            end_pos (int or None): The document position to stop spell checking.
                If None, then check to the end of the document.
        """

        indicator_number = 31
        key = 'spell_check'

        def __init__(self, engine):
            super(SpellCheckDelayable, self).__init__(engine)
            self.chunk_re = re.compile('([^A-Za-z0-9]*)([A-Za-z0-9]*)')
            self.camel_case_re = re.compile(
                '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)'
            )

        def add_document(self, document):
            # Create the speller for the document
            document.__speller__ = aspell.Speller()

            # https://www.scintilla.org/ScintillaDox.html#SCI_INDICSETSTYLE
            # https://qscintilla.com/#clickable_text/indicators
            document.indicatorDefine(
                QsciScintilla.SquiggleLowIndicator, self.indicator_number
            )
            document.SendScintilla(
                QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
            )
            document.setIndicatorForegroundColor(QColor(Qt.red), self.indicator_number)

            document.SCN_MODIFIED.connect(document.onTextModified)

            # Update __speller__ dictionary with programming language words
            # and force spellcheck of the document
            self.reset_session(document)

        def camel_case_split(self, identifier):
            return [m.group(0) for m in self.camel_case_re.finditer(identifier)]

        def clear_markings(self, document):
            """Remove markings made by this Delayable for the given document.

            Args:
                document (blurdev.scintilla.documenteditor.DocumentEditor): The document
                    to clear spell check markings from.
            """
            document.SendScintilla(
                QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
            )
            document.SendScintilla(
                QsciScintilla.SCI_INDICATORCLEARRANGE, 0, len(document.text())
            )

        def loop(self, document, start_pos, end_pos):
            # If end_pos is None, use the whole document
            end_pos = len(document.text()) if end_pos is None else end_pos
            match = next(self.chunk_re.finditer(document.text(start_pos, end_pos)))
            if match:
                start = start_pos
                space, result = tuple(match.groups())
                if space:
                    # If the user inserted space between two words, that space
                    # will still be marked as incorrect. Clear its indicator.
                    document.SendScintilla(
                        QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
                    )
                    document.SendScintilla(
                        QsciScintilla.SCI_INDICATORCLEARRANGE, start, len(space)
                    )
                start += len(space)
                for word in self.camel_case_split(result):
                    length_word = len(word)
                    if any(
                        letter in string.digits for letter in word
                    ) or document.__speller__.check(word):
                        document.SendScintilla(
                            QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
                        )
                        document.SendScintilla(
                            QsciScintilla.SCI_INDICATORCLEARRANGE, start, length_word
                        )
                    else:
                        document.SendScintilla(
                            QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
                        )
                        document.SendScintilla(
                            QsciScintilla.SCI_INDICATORFILLRANGE, start, length_word
                        )
                    start += length_word

                if start < end_pos:
                    # There is more text to process
                    return (start, end_pos)

            return

        def remove_document(self, document):
            try:
                document.SCN_MODIFIED.disconnect(document.onTextModified)
            except TypeError:
                pass

            self.clear_markings(document)

        def reset_session(self, document):
            """Resets the speller dictionary and adds document language
            specific words"""
            if document.__speller__ is None:
                return
            elif not document.lexer() or not document._language:
                # Force spellcheck of the documents
                self.engine.enqueue(document, self.key, 0, None)
                return

            keywords = ''
            language = lang.byName(document._language)
            max_int = {
                key for _, keys in language.lexerColorTypes().items() for key in keys
            }
            # The SQL lexer returns an empty maxEnumIntList
            max_int = max(max_int) if max_int else 0
            for i in range(max_int):
                lexer_keywords = document.lexer().keywords(i)
                if lexer_keywords:
                    keywords += ' ' + lexer_keywords
            document.__speller__.clearSession()

            if not keywords:
                return

            for keyword in keywords.split():
                # Split along whitespace
                # Convert '-' to '_' because aspell doesn't process them
                keyword = keyword.replace('-', '_')
                # Strip '_' because aspell doesn't process them
                keyword = keyword.strip('_')
                # Remove non-alpha chars because aspell doesn't process them
                keyword = ''.join(i for i in keyword if i.isalpha())
                for word in keyword.split('_'):
                    # Split along '_' because aspell doesn't process them
                    if '' != word:
                        document.__speller__.addtoSession(word)

            # Force spellcheck of the documents
            self.engine.enqueue(document, self.key, 0, None)
