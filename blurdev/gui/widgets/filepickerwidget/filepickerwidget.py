##
#   :namespace  python.blurdev.gui.widgets.filepickerwidget.filepickerwidget
#
# 	:remarks	Defines the FilePickerWidget class
#
# 	:author		beta@blur.com
# 	:author		Blur Studio
# 	:date		10/06/10
#

from PyQt4.QtCore import pyqtSignal, pyqtSlot, pyqtProperty, Qt
from PyQt4.QtGui import (
    QWidget,
    QLineEdit,
    QToolButton,
    QHBoxLayout,
    QApplication,
    QFileDialog,
    QColor,
)

resolvedStylesheetDefault = """QLineEdit {color: rgba%(fg)s;
    background: rgba%(bg)s;
}"""


class LineEdit(QLineEdit):
    def dragEnterEvent(self, event):
        if not self.isReadOnly():
            event.acceptProposedAction()
        else:
            super(LineEdit, self).dragEnterEvent(event)

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if not self.isReadOnly() and mimeData.hasUrls():
            urlList = mimeData.urls()
            if urlList:
                fname = urlList[0].toLocalFile()
                self.setText(fname)
        event.acceptProposedAction()


class FilePickerWidget(QWidget):
    filenamePicked = pyqtSignal(str)
    filenameChanged = pyqtSignal(str)

    filenameEdited = pyqtSignal(str)

    def __init__(self, parent):
        self._correctBackground = QColor(0, 128, 0, 100)
        self._correctForeground = QColor(Qt.white)
        self._inCorrectBackground = QColor(139, 0, 0, 100)
        self._inCorrectForeground = QColor(Qt.white)
        QWidget.__init__(self, parent)

        self.uiFilenameTXT = LineEdit(self)
        self.uiPickFileBTN = QToolButton(self)
        self.uiPickFileBTN.setText('...')
        self.uiPickFileBTN.setToolTip(
            '<html><head/><body><p>Browse to a file path.</p><p>Ctrl + LMB: Explore to current path.</p></body></html>'
        )
        # Make this widget focusable and pass the widget focus to uiFilenameTXT
        self.setFocusProxy(self.uiFilenameTXT)
        self.setFocusPolicy(Qt.StrongFocus)
        layout = QHBoxLayout(self)
        layout.addWidget(self.uiFilenameTXT)
        layout.addWidget(self.uiPickFileBTN)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._caption = "Pick file..."
        self._filters = "All Files (*.*)"
        self._pickFolder = False
        self._openFile = False
        self._resolvePath = False
        self._resolved = False

        self.uiFilenameTXT.textChanged.connect(self.emitFilenameChanged)

        self.uiFilenameTXT.editingFinished.connect(self.emitFilenameEdited)
        self.uiPickFileBTN.clicked.connect(self.pickPath)
        self.resolvedStylesheet = resolvedStylesheetDefault

        self.resolve()

    def caption(self):
        return self._caption

    def emitFilenameChanged(self):
        self.resolve()
        if not self.signalsBlocked():
            self.filenameChanged.emit(self.uiFilenameTXT.text())

    def emitFilenameEdited(self):
        if not self.signalsBlocked():
            self.filenameEdited.emit(self.uiFilenameTXT.text())

    def filePath(self):
        return self.uiFilenameTXT.text()

    def filters(self):
        return self._filters

    def isResolved(self):
        return self._resolved

    def openFile(self):
        return self._openFile

    def pickFolder(self):
        return self._pickFolder

    def pickPath(self):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            import blurdev

            blurdev.osystem.explore(self.uiFilenameTXT.text())
        else:
            if self._pickFolder:
                filepath = QFileDialog.getExistingDirectory(
                    self, self._caption, self.uiFilenameTXT.text()
                )
            elif self._openFile:
                filepath = QFileDialog.getOpenFileName(
                    self, self._caption, self.uiFilenameTXT.text(), self._filters
                )
            else:
                filepath = QFileDialog.getSaveFileName(
                    self, self._caption, self.uiFilenameTXT.text(), self._filters
                )
            if filepath:
                self.uiFilenameTXT.setText(filepath)
                if not self.signalsBlocked():
                    self.filenamePicked.emit(filepath)

    def resolve(self):
        if self.resolvePath():
            import os.path

            if os.path.exists(str(self.uiFilenameTXT.text())):
                fg = self.correctForeground
                bg = self.correctBackground
                self._resolved = True
            else:
                fg = self.inCorrectForeground
                bg = self.inCorrectBackground
                self._resolved = False

            style = self.resolvedStylesheet % {'bg': bg.getRgb(), 'fg': fg.getRgb()}
        else:
            style = ''
            self._resolved = False

        self.uiFilenameTXT.setStyleSheet(style)

    def resolvePath(self):
        return self._resolvePath

    def setCaption(self, caption):
        self._caption = caption

    @pyqtSlot(str)
    def setFilePath(self, filePath):
        self.uiFilenameTXT.setText(filePath)

        self.resolve()

    def setFilters(self, filters):
        self._filters = filters

    def setOpenFile(self, state):
        self._openFile = state

    def setPickFolder(self, state):
        self._pickFolder = state

    @pyqtSlot(bool)
    def setNotResolvePath(self, state):
        """ Set resolvePath to the oposite of state. """
        self.setResolvePath(not state)

    @pyqtSlot(bool)
    def setResolvePath(self, state):
        self._resolvePath = state
        self.resolve()

    pyCaption = pyqtProperty("QString", caption, setCaption)
    pyFilters = pyqtProperty("QString", filters, setFilters)
    pyPickFolder = pyqtProperty("bool", pickFolder, setPickFolder)
    pyOpenFile = pyqtProperty("bool", openFile, setOpenFile)
    pyResolvePath = pyqtProperty("bool", resolvePath, setResolvePath)
    pyFilePath = pyqtProperty("QString", filePath, setFilePath)

    # Load the colors from the stylesheets
    @pyqtProperty(QColor)
    def correctBackground(self):
        return self._correctBackground

    @correctBackground.setter
    def correctBackground(self, color):
        self._correctBackground = color
        self.resolve()

    @pyqtProperty(QColor)
    def correctForeground(self):
        return self._correctForeground

    @correctForeground.setter
    def correctForeground(self, color):
        self._correctForeground = color
        self.resolve()

    @pyqtProperty(QColor)
    def inCorrectBackground(self):
        return self._inCorrectBackground

    @inCorrectBackground.setter
    def inCorrectBackground(self, color):
        self._inCorrectBackground = color
        self.resolve()

    @pyqtProperty(QColor)
    def inCorrectForeground(self):
        return self._inCorrectForeground

    @inCorrectForeground.setter
    def inCorrectForeground(self, color):
        self._inCorrectForeground = color
        self.resolve()
