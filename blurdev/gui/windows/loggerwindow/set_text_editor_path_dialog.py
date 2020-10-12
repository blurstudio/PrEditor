import os
import blurdev

from Qt.QtWidgets import QDialog, QMessageBox


class SetTextEditorPathDialog(QDialog):
    """A dialog used to set the user's text editor executable path, as well as define a
    'command template', which allows for the various ways text editor's may implement
    opening a file at a given line number via Command Prompt.
    """
    def __init__(self, parent=None, redmineUrl=None):
        super(SetTextEditorPathDialog, self).__init__(parent)
        blurdev.gui.loadUi(__file__, self)

        # Rerieve existing data from LoggerWindow
        path = self.parent().textEditorPath
        cmdTempl = self.parent().textEditorCmdTempl

        # If the data exists, place in the UI, otherwise use UI defaults
        if path:
            self.uiTextEditorExecutablePathLE.setText(path)
        if cmdTempl:
            self.uiTextEditorCommandPatternLE.setText(cmdTempl)

        toolTip = ("Examples:\n"
            "SublimeText: exePath modulePath:lineNum\n"
            "notepad++: exePath modulePath -nlineNum\n"
            "vim: exePath +lineNum modulePath")
        self.uiTextEditorCommandPatternLE.setToolTip(toolTip)

    def accept(self):
        """Validate that the path exists and is an executable (extension is '.exe')
        Can't really validate the command template, so instead we use try/except when
        issuing the command.
        """
        path = self.uiTextEditorExecutablePathLE.text()
        cmdTempl = self.uiTextEditorCommandPatternLE.text()

        path = path.strip("\"")
        if os.path.exists(path) and path.endswith('.exe'):
            self.parent().textEditorPath = path
            self.parent().textEditorCmdTempl = cmdTempl
            super(SetTextEditorPathDialog, self).accept()
        else:
            msg = "That path doesn't exists or isn't an exe file."
            label = 'Incorrect Path'
            QMessageBox.warning(self.window(), label, msg, QMessageBox.Ok)
