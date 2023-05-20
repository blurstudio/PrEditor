from __future__ import absolute_import, print_function

from PyQt5.Qsci import QsciScintilla
from Qt.QtCore import QSignalMapper
from Qt.QtWidgets import QWidget

from ...delayable_engine.delayables import SearchDelayable
from .. import FindState


class SmartHighlight(SearchDelayable):
    key = 'smart_highlight'
    indicator_number = 30
    indicator_style = QsciScintilla.StraightBoxIndicator
    border_alpha = 255

    def __init__(self, engine):
        super(SmartHighlight, self).__init__(engine)
        self.signal_mapper = QSignalMapper(self)
        # Respect style sheet changes
        # TODO: Correctly connect this signal
        # LoggerWindow.styleSheetChanged.connect(self.update_indicator_color)

    def add_document(self, document):
        document.indicatorDefine(self.indicator_style, self.indicator_number)
        document.SendScintilla(
            QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
        )
        document.setIndicatorForegroundColor(
            document.paperSmartHighlight, self.indicator_number
        )
        document.SendScintilla(
            QsciScintilla.SCI_INDICSETOUTLINEALPHA,
            self.indicator_number,
            self.border_alpha,
        )

        self.signal_mapper.setMapping(document, document)
        self.signal_mapper.mapped[QWidget].connect(self.update_highlighter)
        document.selectionChanged.connect(self.signal_mapper.map)

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

    def loop(self, document, find_state, clear):
        # Clear the document if needed
        if clear:
            self.clear_markings(document)
        ret = super(SmartHighlight, self).loop(document, find_state)
        if ret:
            # clear should always be false when continuing
            return ret + (False,)

    def remove_document(self, document):
        self.clear_markings(document)
        document.selectionChanged.disconnect(self.signal_mapper.map)

    def text_found(self, document, start, end, find_state):
        if not document.is_word(start, end):
            # Don't highlight the word if its not a word on its own
            return
        document.SendScintilla(
            QsciScintilla.SCI_SETINDICATORCURRENT, self.indicator_number
        )
        document.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start, end - start)

    def update_highlighter(self, document):
        self.clear_markings(document)
        if document.selection_is_word():
            find_state = FindState()
            find_state.expr = document.selectedText()
            self.search_from_position(document, find_state, None, False)

    def update_indicator_color(self):
        for document in self.engine.documents:
            document.setIndicatorForegroundColor(
                document.paperSmartHighlight, self.indicator_number
            )
            document.SendScintilla(
                QsciScintilla.SCI_INDICSETOUTLINEALPHA,
                self.indicator_number,
                self.border_alpha,
            )
