##
#   \namespace  python.blurdev.ide.languagecombobox
#
#   \remarks    A combo box to provide the ability to select the language of a document.
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       04/03/12
#
from Qt.QtCore import QSize, Signal
from Qt.QtWidgets import QComboBox
from blurdev.ide import lang


class LanguageComboBox(QComboBox):
    currentLanguageChanged = Signal(str)

    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.setIconSize(QSize(16, 16))
        self.setMaxVisibleItems(20)
        self.refresh()
        self.currentIndexChanged.connect(self.emitLanguageChange)

    def currentLanguage(self):
        return lang.byName(self.currentText())

    def refresh(self):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
        current = self.currentLanguage()
        self.addItem('Plain Text')
        self.insertSeparator(1)
        for language in lang.languages():
            self.addItem(language)
        self.setCurrentLanguage(current)
        self.setUpdatesEnabled(True)
        self.blockSignals(False)

    def emitLanguageChange(self):
        self.currentLanguageChanged.emit(self.currentText())

    def setCurrentLanguage(self, language):
        if language:
            if isinstance(language, lang.Language):
                language = language.name()
            index = self.findText(language)
            # if the language is not recognized set it to Plain Text
            if index == -1:
                index = 0
        else:
            index = 0
        self.setCurrentIndex(index)
