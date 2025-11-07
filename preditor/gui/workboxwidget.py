from __future__ import absolute_import, print_function

import os
import re
from pathlib import Path

from Qt.QtCore import QEvent, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import QAction, QMessageBox

from .. import core, resourcePath
from ..gui.workbox_mixin import WorkboxMixin
from ..scintilla import QsciScintilla
from ..scintilla.documenteditor import DocumentEditor, SearchOptions
from ..scintilla.finddialog import FindDialog


class WorkboxWidget(WorkboxMixin, DocumentEditor):
    def __init__(
        self,
        parent=None,
        console=None,
        delayable_engine='default',
        core_name=None,
        **kwargs,
    ):
        self.__set_console__(console)
        self._searchFlags = 0
        self._searchText = ''
        self._searchDialog = None

        # initialize the super class
        super(WorkboxWidget, self).__init__(
            parent, delayable_engine=delayable_engine, core_name=core_name, **kwargs
        )

        # Store the software name so we can handle custom keyboard shortcuts based on
        # software
        self._software = core.objectName()
        # Used to remove any trailing whitespace when running selected text
        self.regex = re.compile(r'\s+$')
        self.initShortcuts()

        self._defaultLanguage = "Python"
        self.setLanguage(self._defaultLanguage)
        # Default to unix newlines
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        if hasattr(self.window(), "setWorkboxFontBasedOnConsole"):
            self.window().setWorkboxFontBasedOnConsole()

    def __auto_complete_enabled__(self):
        return self.autoCompletionSource() == QsciScintilla.AutoCompletionSource.AcsAll

    def __set_auto_complete_enabled__(self, state):
        state = (
            QsciScintilla.AutoCompletionSource.AcsAll
            if state
            else QsciScintilla.AutoCompletionSource.AcsNone
        )
        self.setAutoCompletionSource(state)

    def __clear__(self):
        self.clear()
        self.__set_last_saved_text__(self.__text__())

    def __comment_toggle__(self):
        self.commentToggle()

    def __copy_indents_as_spaces__(self):
        return self.copyIndentsAsSpaces

    def __set_copy_indents_as_spaces__(self, state):
        self.copyIndentsAsSpaces = state

    def __cursor_position__(self):
        """Returns the line and index of the cursor."""
        return self.getCursorPosition()

    def __set_cursor_position__(self, line, index):
        """Set the cursor to this line number and index"""
        self.setCursorPosition(line, index)

    def __check_for_save__(self):
        if self.isModified():
            result = QMessageBox.question(
                self.window(),
                'Save changes to...',
                'Do you want to save your changes?',
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Yes:
                return self.save()
            elif result == QMessageBox.StandardButton.Cancel:
                return False
        return True

    def eventFilter(self, object, event):
        if event.type() == QEvent.Type.Close and not self.__check_for_save__():
            event.ignore()
            return True
        return False

    def execStandalone(self):
        if self.__save__():
            os.startfile(str(self.filename()))

    def __filename__(self):
        return self.filename()

    def __set_filename__(self, filename):
        self.set_filename(filename)

    def __font__(self):
        if self.lexer():
            return self.lexer().font(0)
        else:
            return self.font()

    def __set_font__(self, font):
        self.documentFont = font
        if self.lexer():
            self.lexer().setFont(font)
        else:
            self.setFont(font)

    def __goto_line__(self, line):
        self.goToLine(line)

    def __indentations_use_tabs__(self):
        return self.indentationsUseTabs()

    def __set_indentations_use_tabs__(self, state):
        self.setIndentationsUseTabs(state)

    def __insert_text__(self, txt):
        self.insert(txt)

    def __load__(self, filename):
        if filename and Path(filename).is_file():
            # This is overriding WorkboxMixin.__load__, make sure to base class
            # method.
            super().__load__(filename)

            # DocumentEditor specific calls
            font = self.__font__()
            self.updateFilename(str(filename))
            self.__set_font__(font)
            self.setEolMode(self.detectEndLine(self.__text__()))

    def __save__(self):
        font = self.__font__()
        super().__save__()
        filename = self.__filename__()
        if filename:
            self.updateFilename(filename)
        self.__set_font__(font)

    def __margins_font__(self):
        return self.marginsFont()

    def __set_margins_font__(self, font):
        self.setMarginsFont(font)

    def __marker_add__(self, line):
        try:
            marker = self._marker
        except AttributeError:
            self._marker = self.markerDefine(QsciScintilla.MarkerSymbol.Circle)
            marker = self._marker
        self.markerAdd(line, marker)

    def __marker_clear_all__(self):
        try:
            self.markerDeleteAll(self._marker)
        except AttributeError:
            # self._marker has not been created yet
            pass

    def __remove_selected_text__(self):
        self.removeSelectedText()

    def __selected_text__(self, start_of_line=False, selectText=False):
        line, s, end, e = self.getSelection()

        # Sometime self.getSelection returns values that equate to a non-existent
        # selection, ie start and end are the same, so let's process it as if there is
        # no selection
        selectionIsEmpty = line == end and s == e
        if line == -1 or selectionIsEmpty:
            # Nothing is selected, return the current line of text
            line, index = self.getCursorPosition()
            txt = self.__text_part__(lineNum=line)

            if selectText:
                lineLength = len(txt.rstrip())
                self.setSelection(line, 0, line, lineLength)

        elif start_of_line:
            ss = self.positionFromLineIndex(line, 0)
            ee = self.positionFromLineIndex(end, e)
            txt = self.__text_part__(start=ss, end=ee)
        else:
            txt = self.selectedText()
        return self.regex.split(txt)[0], line

    def __tab_width__(self):
        return self.tabWidth()

    def __set_tab_width__(self, width):
        self.setTabWidth(width)

    def __text__(self):
        """Returns the text in this widget
        Returns:
            str: Returns the text in this widget
        """
        return self.text()

    def keyPressEvent(self, event):
        """Check for certain keyboard shortcuts, and handle them as needed,
        otherwise pass the keyPress to the superclass.

        NOTE! We handle the "shift+return" shortcut here, rather than the
        QAction's shortcut, because the workbox will always intercept that
        shortcut. So, we handle it here, and call the main window's
        execSelected, which ultimately calls this workbox's __exec_selected__.

        Also note, it would make sense to have ctrl+Enter also execute without
        truncation, but no modifiers are registered when Enter is pressed (unlike
        when Return is pressed), so this combination is not detectable.
        """
        tab_widget = self.__tab_widget__()
        if tab_widget is not None:
            tab_widget.tabBar().update()

        if self.process_shortcut(event):
            return
        else:
            # Send regular keystroke
            super(WorkboxWidget, self).keyPressEvent(event)

    def initShortcuts(self):
        """Use this to set up shortcuts when the DocumentEditor"""
        icon = QIcon(resourcePath('img/text-search-variant.png'))
        self.uiFindACT = QAction(icon, 'Find...', self)
        self.uiFindACT.setShortcut("Ctrl+F")
        self.addAction(self.uiFindACT)

        icon = QIcon(resourcePath('img/skip-previous.png'))
        self.uiFindPrevACT = QAction(icon, 'Find Prev', self)
        self.uiFindPrevACT.setShortcut("Ctrl+F3")
        self.addAction(self.uiFindPrevACT)

        icon = QIcon(resourcePath('img/skip-next.png'))
        self.uiFindNextACT = QAction(icon, 'Find Next', self)
        self.uiFindNextACT.setShortcut("F3")
        self.addAction(self.uiFindNextACT)

        self.uiSelectCurrentLineACT = QAction(icon, 'Select Line', self)
        self.uiSelectCurrentLineACT.triggered.connect(self.expandCursorToLineSelection)
        self.uiSelectCurrentLineACT.setShortcut('Ctrl+L')
        self.addAction(self.uiSelectCurrentLineACT)

        # create the search dialog and connect actions
        self._searchDialog = FindDialog(self)
        self._searchDialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.uiFindACT.triggered.connect(
            lambda: self._searchDialog.search(self.searchText())
        )
        self.uiFindPrevACT.triggered.connect(
            lambda: self.findPrev(self.searchText(), self.searchFlags())
        )
        self.uiFindNextACT.triggered.connect(
            lambda: self.findNext(self.searchText(), self.searchFlags())
        )

    def searchFlags(self):
        return self._searchFlags

    def searchText(self):
        if not self._searchDialog:
            return ''
        # refresh the search text unless we are using regular expressions
        if (
            not self._searchDialog.isVisible()
            and not self._searchFlags & SearchOptions.QRegExp
        ):
            txt = self.selectedText()
            if txt:
                self._searchText = txt
        return self._searchText

    def setSearchFlags(self, flags):
        self._searchFlags = flags

    def setSearchText(self, txt):
        self._searchText = txt

    def showMenu(self, pos):
        menu = super(WorkboxWidget, self).showMenu(pos, popup=False)
        menu.addSeparator()
        submenu = menu.addMenu('Options')
        act = submenu.addAction('Toggle end line visibility')
        act.setCheckable(True)
        act.setChecked(self.eolVisibility())
        act.triggered.connect(self.setEolVisibility)

        act = submenu.addAction('Show Whitespace')
        act.setCheckable(True)
        act.setChecked(self.showWhitespaces())
        act.triggered.connect(self.setShowWhitespaces)

        menu.popup(self._clickPos)
