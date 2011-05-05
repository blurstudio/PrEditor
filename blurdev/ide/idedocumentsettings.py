##
# 	\namespace	blurdev.ide.idesettings
#
# 	\remarks	[desc::commented]
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		04/18/11


class IdeDocumentSettings(object):
    _defaultSettings = None

    def __init__(self):
        # define the settings that will be configurable for a document
        # allowing for globals as well as project specific settings
        self.font = None
        self.marginFont = None
        self.marginBackground = None
        self.marginForeground = None
        self.foldingBackground = None
        self.foldingForeground = None
        self.whitespaceBackground = None
        self.whitespaceForeground = None
        self.showLineNumbers = None
        self.showWhitespaces = None
        self.autoIndent = None
        self.autoCompleteSource = None
        self.indentationsUseTabs = None
        self.tabIndents = None
        self.tabWidth = None
        self.caretLineVisible = None
        self.caretLineBackground = None

    def recordXml(self, xml):
        # record the settings
        for key, value in self.__dict__.items():
            if key.startswith('_') or value == None:
                continue
            xml.recordProperty(key, value)

    def loadXml(self, xml):
        # restore the settings
        for key in self.__dict__.keys():
            if key.startswith('_'):
                continue
            self.__dict__[key] = xml.restoreProperty(key, None)

    def setupEditor(self, editor):
        # set the editor font
        if self.font != None:
            editor.setFont(self.font)

        # set margin information
        if self.marginFont != None:
            from PyQt4.QtGui import QFontMetrics

            editor.setMarginsFont(self.marginFont)
            editor.setMarginWidth(0, QFontMetrics(self.marginFont).width('000000') + 5)

        # set margin line numbers
        if self.showLineNumbers != None:
            editor.setMarginLineNumbers(0, self.showLineNumbers)

        # set margin background
        if self.marginBackground:
            try:
                editor.setMarginsBackground(self.marginBackground)
            except:
                pass

        # set folding colors
        if self.foldingForeground and self.foldingBackground:
            editor.setFoldMarginColors(self.foldingForeground, self.foldingBackground)

        # set whitespace colors
        if self.whitespaceBackground:
            try:
                editor.setWhitespaceBackgroundColor(self.whitespaceBackground)
            except:
                pass

        if self.whitespaceForeground:
            try:
                editor.setWhitespaceForegroundColor(self.whitespaceForeground)
            except:
                pass

        # set the auto-indent option
        if self.autoIndent != None:
            editor.setAutoIndent(self.autoIndent)

        # set the autocompletion source
        if self.autoCompleteSource != None:
            editor.setAutoCompletionSource(self.autoCompleteSource)

        # set indentation options
        if self.indentationsUseTabs != None:
            editor.setIndentationsUseTabs(self.indentationsUseTabs)

        # set tab indents
        if self.tabIndents != None:
            editor.setTabIndents(self.tabIndents)

        # set the tab width
        if self.tabWidth != None:
            editor.setTabWidth(self.tabWidth)

        # set the caret visibility
        if self.caretLineVisible != None:
            editor.setCaretLineVisible(self.caretLineVisible)

        # set the caret background color
        if self.caretLineBackground != None:
            editor.setCaretLineBackgroundColor(self.caretLineBackground)

        # set the whitespace visibility
        if self.showWhitespaces != None:
            editor.setShowWhitespaces(self.showWhitespaces)

    @staticmethod
    def defaultSettings():
        # create the default settings
        if not IdeDocumentSettings._defaultSettings:
            defaults = IdeDocumentSettings()

            # initialize the default settings
            from PyQt4.QtCore import Qt
            from PyQt4.QtGui import QFont, QColor
            from PyQt4.Qsci import QsciScintilla

            # set default font
            font = QFont()
            font.setFamily('Courier New')
            font.setFixedPitch(True)
            font.setPointSize(9)

            defaults.font = font

            # set default margin font
            mfont = QFont(font)
            mfont.setPointSize(7)

            defaults.marginFont = mfont

            # set default colors
            defaults.marginBackground = QColor(Qt.lightGray)
            defaults.marginForeground = QColor(Qt.gray)
            defaults.foldingForeground = QColor(Qt.yellow)
            defaults.foldingBackground = QColor(Qt.blue)
            defaults.caretLineBackground = QColor(Qt.white)
            defaults.whitespaceBackground = QColor(Qt.white)
            defaults.whitespaceForeground = QColor(Qt.lightGray)

            # set default options
            defaults.autoIndent = True
            defaults.autoCompleteSource = QsciScintilla.AcsAll
            defaults.indentationsUseTabs = True
            defaults.tabIndents = True
            defaults.tabWidth = 4
            defaults.caretLineVisible = False
            defaults.showWhitespaces = False
            defaults.showLineNumbers = True

            IdeDocumentSettings._defaultSettings = defaults

        return IdeDocumentSettings._defaultSettings
