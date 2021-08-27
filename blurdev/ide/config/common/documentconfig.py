##
# 	\namespace	blurdev.ide.config.[module]
#
# 	\remarks	Edit the addon properties for the IDE
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/08/11
#

from __future__ import absolute_import
import blurdev

from blurdev.gui.dialogs.configdialog import ConfigSectionWidget
from Qt.QtWidgets import QMessageBox


class DocumentConfig(ConfigSectionWidget):
    def initUi(self):
        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)
        self.uiSpellCheckCHK.clicked.connect(self.spellCheckClicked)

    def spellCheckClicked(self, clicked):
        aspell = None
        try:
            import aspell
        except ImportError:
            pass
        if aspell:
            try:
                aspell.Speller()
            except Exception as e:
                self.uiSpellCheckCHK.setCheckable(False)
                QMessageBox.warning(self, "Spell-Check", "{}".format(e))

    def recordUi(self):
        """records the latest ui settings to the data"""
        section = self.section()
        # record section values
        section.setValue('autoIndent', self.uiAutoIndentCHK.isChecked())
        section.setValue(
            'autoCompleteThreshold', self.uiAutoCompleteThresholdSPN.value()
        )
        section.setValue('autoComplete', self.uiAutoCompleteCHK.isChecked())
        section.setValue(
            'indentationsUseTabs', self.uiIndentationsUseTabsCHK.isChecked()
        )
        section.setValue('tabIndents', self.uiTabIndentsCHK.isChecked())
        section.setValue('copyIndentsAsSpaces', self.uiCopyTabsToSpacesCHK.isChecked())
        section.setValue('tabWidth', self.uiTabWidthSPN.value())
        section.setValue('caretLineVisible', self.uiCaretLineVisibleCHK.isChecked())
        section.setValue('showWhitespaces', self.uiShowWhitespacesCHK.isChecked())
        section.setValue('showLineNumbers', self.uiShowLineNumbersCHK.isChecked())
        section.setValue('showIndentations', self.uiShowIndentationsCHK.isChecked())
        section.setValue('showLimitColumn', self.uiShowLimitColumnCHK.isChecked())
        section.setValue('limitColumn', self.uiLimitColumnSPN.value())
        section.setValue('showEol', self.uiShowEndlinesCHK.isChecked())
        section.setValue('eolMode', self.uiEndlineModeDDL.currentText())
        section.setValue('convertEol', self.uiEndlineConvertCHK.isChecked())
        section.setValue('openFileMonitor', self.uiOpenFileMonitorCHK.isChecked())
        section.setValue('spellCheck', self.uiSpellCheckCHK.isChecked())
        section.setValue('smartHighlighting', self.uiSmartHighlightingCHK.isChecked())
        section.setValue('backspaceUnindents', self.uiBackspaceUnindentsCHK.isChecked())

    def refreshUi(self):
        """refrshes the ui with the latest data settings"""
        section = self.section()
        # restore section values
        self.uiAutoIndentCHK.setChecked(section.value('autoIndent'))
        self.uiAutoCompleteThresholdSPN.setValue(section.value('autoCompleteThreshold'))
        self.uiAutoCompleteCHK.setChecked(section.value('autoComplete'))
        self.uiIndentationsUseTabsCHK.setChecked(section.value('indentationsUseTabs'))
        self.uiTabIndentsCHK.setChecked(section.value('tabIndents'))
        self.uiCopyTabsToSpacesCHK.setChecked(section.value('copyIndentsAsSpaces'))
        self.uiTabWidthSPN.setValue(section.value('tabWidth'))
        self.uiCaretLineVisibleCHK.setChecked(section.value('caretLineVisible'))
        self.uiShowWhitespacesCHK.setChecked(section.value('showWhitespaces'))
        self.uiShowLineNumbersCHK.setChecked(section.value('showLineNumbers'))
        self.uiShowIndentationsCHK.setChecked(section.value('showIndentations'))
        self.uiShowEndlinesCHK.setChecked(section.value('showEol'))
        self.uiShowLimitColumnCHK.setChecked(section.value('showLimitColumn'))
        self.uiLimitColumnSPN.setValue(section.value('limitColumn'))
        self.uiEndlineConvertCHK.setChecked(section.value('convertEol'))
        self.uiEndlineModeDDL.setCurrentIndex(
            self.uiEndlineModeDDL.findText(section.value('eolMode'))
        )
        self.uiOpenFileMonitorCHK.setChecked(section.value('openFileMonitor'))
        try:
            import aspell  # noqa: F401

            self.uiSpellCheckCHK.setChecked(section.value('spellCheck'))
        except ImportError:
            self.uiSpellCheckCHK.setDisabled(True)
        self.uiSmartHighlightingCHK.setChecked(section.value('smartHighlighting'))
        self.uiBackspaceUnindentsCHK.setChecked(section.value('backspaceUnindents'))


def registerSections(configSet):
    """registers one or many new sections to the config system
    Args:
        configSet (blurdev.gui.dialogs.configdialog.ConfigSet):
    """

    # define section
    group = 'Common'
    section = 'Document'
    icon = blurdev.relativePath(__file__, 'img/documentconfig.png')
    cls = DocumentConfig
    params = {
        'autoIndent': True,
        'autoComplete': True,
        'autoCompleteThreshold': 3,
        'indentationsUseTabs': True,
        'tabIndents': True,
        'copyIndentsAsSpaces': False,
        'tabWidth': 4,
        'caretLineVisible': False,
        'showWhitespaces': False,
        'showLineNumbers': True,
        'showIndentations': False,
        'showEol': False,
        'eolMode': 'Auto-Detect',
        'convertEol': False,
        'showLimitColumn': False,
        'limitColumn': 100,
        'openFileMonitor': True,
        'smartHighlighting': True,
        'spellCheck': False,
        'backspaceUnindents': True,
    }

    # register the section to the configset
    configSet.registerSection(section, cls, params, group=group, icon=icon)
