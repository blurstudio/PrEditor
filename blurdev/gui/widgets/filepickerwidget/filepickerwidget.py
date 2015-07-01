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
from blurdev.media import (
    imageSequenceFromFileName,
    imageSequenceRepr,
    imageSequenceForRepr,
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
        self._imageSequence = False
        self._resolved = False
        self._chosenPath = None

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
        # if it's an image sequence, return the last chosen image path
        return self._chosenPath or self.uiFilenameTXT.text()

    def fileSequence(self):
        if self._imageSequence:
            return imageSequenceForRepr(unicode(self.uiFilenameTXT.text()))
        return []

    def setFileSequence(self, sequence):
        if self._imageSequence:
            self._chosenPath = sequence[0]
            seqRep = imageSequenceRepr(sequence)
            self.uiFilenameTXT.setText(seqRep)
            self.resolve()

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
            elif self._imageSequence:
                initialPath = self._chosenPath or self.uiFilenameTXT.text()
                filepath = QFileDialog.getOpenFileName(
                    self, self._caption, initialPath, self._filters
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

            path = unicode(self.uiFilenameTXT.text())
            if self._pickFolder:
                valid = os.path.isdir(path)
            else:
                valid = os.path.isfile(path)

                if self._imageSequence:
                    # if we got a valid filename, find the sequence
                    if valid:
                        sequenceFiles = imageSequenceFromFileName(path)
                        seqRep = imageSequenceRepr(sequenceFiles)
                        self._chosenPath = path
                    # if not, it could already be an image sequence representation
                    else:
                        sequenceFiles = imageSequenceForRepr(path)
                        valid = (
                            sequenceFiles
                            and os.path.isfile(sequenceFiles[0])
                            and os.path.isfile(sequenceFiles[-1])
                        )
                        seqRep = path
                        # If we don't have a previously selected path, use the path of the first image
                        # in the sequence.
                        if not self._chosenPath and valid:
                            self._chosenPath = sequenceFiles[0]
                    if valid:
                        self.uiFilenameTXT.setText(seqRep)
            if valid:
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

    def imageSequence(self):
        return self._imageSequence

    @pyqtSlot(bool)
    def setNotImageSequence(self, state):
        """ Set resolvePath to the oposite of state. """
        self.setImageSequence(not state)

    @pyqtSlot(bool)
    def setImageSequence(self, state):
        if self._openFile:
            self._imageSequence = state
            self.resolve()
        else:
            raise ValueError("imageSequence only accepted if openFile is enabled.")

    pyCaption = pyqtProperty("QString", caption, setCaption)
    pyFilters = pyqtProperty("QString", filters, setFilters)
    pyPickFolder = pyqtProperty("bool", pickFolder, setPickFolder)
    pyOpenFile = pyqtProperty("bool", openFile, setOpenFile)
    pyResolvePath = pyqtProperty("bool", resolvePath, setResolvePath)
    pyImageSequence = pyqtProperty("bool", imageSequence, setImageSequence)
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
