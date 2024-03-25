from __future__ import absolute_import

from Qt.QtWidgets import QDialog

from . import loadUi


class SuggestPathQuotesDialog(QDialog):
    """A dialog to suggest to enclose paths in double-quotes in the cmdTempl which is
    used to launch an external text editor.
    """

    def __init__(self, parent, oldCmdTempl, newCmdTempl):
        super(SuggestPathQuotesDialog, self).__init__(parent)
        loadUi(__file__, self)

        self.parentWindow = self.parent().window()

        self.uiTextEditorOldCommandPatternLE.setText(oldCmdTempl)
        self.uiTextEditorNewCommandPatternLE.setText(newCmdTempl)

        toolTip = (
            "Examples:\n"
            'SublimeText: "{exePath}" "{modulePath}":{lineNum}\n'
            'notepad++: "{exePath}" "{modulePath}" -n{lineNum}\n'
            'vim: "{exePath}" + {lineNum} "{modulePath}'
        )
        self.uiTextEditorNewCommandPatternLE.setToolTip(toolTip)

    def accept(self):
        """Set the parentWindow's textEditorCmdTempl property from the dialog, and
        optionally add dialog to parent's dont_ask_again list, and accept.
        """

        cmdTempl = self.uiTextEditorNewCommandPatternLE.text()
        self.parentWindow.textEditorCmdTempl = cmdTempl

        if self.uiDontAskAgainCHK.isChecked():
            if hasattr(self.parentWindow, "dont_ask_again"):
                self.parentWindow.dont_ask_again.append(self.objectName())

        super(SuggestPathQuotesDialog, self).accept()

    def reject(self):
        """Optionally add dialog to parentWindow's dont_ask_again list, and reject"""
        if self.uiDontAskAgainCHK.isChecked():
            if hasattr(self.parentWindow, "dont_ask_again"):
                self.parentWindow.dont_ask_again.append(self.objectName())

        super(SuggestPathQuotesDialog, self).reject()
