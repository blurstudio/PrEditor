from __future__ import absolute_import, print_function

from Qt.QtCore import Qt, Slot
from Qt.QtGui import QIcon, QKeySequence
from Qt.QtWidgets import QApplication, QShortcut, QWidget

from .. import resourcePath
from ..utils.text_search import RegexTextSearch, SimpleTextSearch
from . import loadUi


class FindFiles(QWidget):
    def __init__(self, parent=None, managers=None, console=None):
        super(FindFiles, self).__init__(parent=parent)
        if managers is None:
            managers = []
        self.managers = managers
        self.console = console
        self.finder = None
        self.match_files_count = 0

        loadUi(__file__, self)

        # Set the icons
        self.uiCaseSensitiveBTN.setIcon(
            QIcon(resourcePath("img/format-letter-case.svg"))
        )
        self.uiCloseBTN.setIcon(QIcon(resourcePath('img/close-thick.png')))
        self.uiRegexBTN.setIcon(QIcon(resourcePath("img/regex.svg")))

        # Create shortcuts
        self.uiCloseSCT = QShortcut(
            QKeySequence(Qt.Key_Escape), self, context=Qt.WidgetWithChildrenShortcut
        )

        self.uiCloseSCT.activated.connect(self.hide)

        self.uiCaseSensitiveSCT = QShortcut(
            QKeySequence(Qt.AltModifier | Qt.Key_C),
            self,
            context=Qt.WidgetWithChildrenShortcut,
        )
        self.uiCaseSensitiveSCT.activated.connect(self.uiCaseSensitiveBTN.toggle)

        self.uiRegexSCT = QShortcut(
            QKeySequence(Qt.AltModifier | Qt.Key_R),
            self,
            context=Qt.WidgetWithChildrenShortcut,
        )
        self.uiRegexSCT.activated.connect(self.uiRegexBTN.toggle)

    def activate(self):
        """Called to make this widget ready for the user to interact with."""
        self.show()
        self.uiFindTXT.setFocus()

    @Slot()
    def find(self):
        find_text = self.uiFindTXT.text()
        context = self.uiContextSPN.value()
        # Create an instance of the TextSearch to use for this search
        if self.uiRegexBTN.isChecked():
            TextSearch = RegexTextSearch
        else:
            TextSearch = SimpleTextSearch
        self.finder = TextSearch(
            find_text, self.uiCaseSensitiveBTN.isChecked(), context=context
        )
        self.finder.callback_matching = self.insert_found_text
        self.finder.callback_non_matching = self.insert_text

        self.insert_text(self.finder.title())

        self.match_files_count = 0
        for manager in self.managers:
            for (
                editor,
                group_name,
                tab_name,
                group_index,
                tab_index,
            ) in manager.all_widgets():
                path = "/".join((group_name, tab_name))
                workbox_id = '{},{}'.format(group_index, tab_index)
                self.find_in_editor(editor, path, workbox_id)

        self.insert_text(
            '\n{} matches in {} workboxes\n'.format(
                self.finder.match_count, self.match_files_count
            )
        )

    def find_in_editor(self, editor, path, workbox_id):
        # Ensure the editor text is loaded and get its raw text
        editor.__show__()
        text = editor.__text__()

        # Use the finder to check for matches
        found = self.finder.search_text(text, path, workbox_id)
        if found:
            self.match_files_count += 1

    def insert_found_text(self, text, workbox_id, line_num, tool_tip):
        href = ', {}, {}'.format(workbox_id, line_num)
        cursor = self.console.textCursor()
        # Insert hyperlink
        fmt = cursor.charFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(href)
        fmt.setFontUnderline(True)
        fmt.setToolTip(tool_tip)
        cursor.insertText(text, fmt)
        # Show the updated text output
        QApplication.instance().processEvents()

    def insert_text(self, text):
        cursor = self.console.textCursor()
        fmt = cursor.charFormat()
        fmt.setAnchor(False)
        fmt.setAnchorHref('')
        fmt.setFontUnderline(False)
        fmt.setToolTip('')
        cursor.insertText(text, fmt)
        # Show the updated text output
        QApplication.instance().processEvents()
