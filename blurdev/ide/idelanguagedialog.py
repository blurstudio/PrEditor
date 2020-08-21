##
# 	\namespace	blurdev.ide.idelanguagedialog
#
# 	\remarks	Creates an interface for editing language files
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		07/21/11
#

import re

from Qt import Qsci
from Qt.QtCore import QSize, Qt
from Qt.QtGui import QIcon
from Qt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QTreeWidgetItem,
    QVBoxLayout,
)
from Qt import QtCompat

import blurdev
from blurdev.ide import lang


class DescriptorDialog(QDialog):
    def __init__(self, parent):
        super(DescriptorDialog, self).__init__(parent)

        # create ui
        self.uiTypeDDL = QComboBox(self)
        self.uiExprTXT = QLineEdit(self)
        self.uiDialogBTNS = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        self.uiTypeDDL.addItems(['function', 'class'])

        # create layout
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.uiTypeDDL)
        hlayout.addWidget(self.uiExprTXT)

        # create alyout
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.uiDialogBTNS)

        self.setLayout(vlayout)
        self.adjustSize()

        # create connections
        self.uiDialogBTNS.accepted.connect(self.accept)
        self.uiDialogBTNS.rejected.connect(self.reject)

    def accept(self):
        type, expr = self.descriptor()
        if not (type and expr):
            QMessageBox.critical(
                self,
                'Not Enough Info',
                'You need to select a type and enter an expression.',
            )
            return
        super(DescriptorDialog, self).accept()

    def descriptor(self):
        return (str(self.uiTypeDDL.currentText()), str(self.uiExprTXT.text()))

    def setDescriptor(self, type, expr):
        self.uiTypeDDL.setCurrentIndex(self.uiTypeDDL.findText(type))
        self.uiExprTXT.setText(expr)


class IdeLanguageDialog(QDialog):
    def __init__(self, parent=None):
        super(IdeLanguageDialog, self).__init__(parent)
        if parent:
            self.setPalette(parent.palette())

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        # load the scheme options
        from blurdev.ide.ideeditor import IdeEditor

        configSet = IdeEditor.globalConfigSet()
        scheme = configSet.section('Editor::Scheme')
        if scheme:
            # create the scheme options
            for key in scheme.properties():
                if key.startswith('document_color_'):
                    item = QTreeWidgetItem([key.replace('document_color_', '')])
                    clr = scheme.value(key)
                    item.setForeground(0, clr)
                    item.setBackground(
                        0, self.palette().color(self.palette().AlternateBase)
                    )
                    self.uiEditorColorsTREE.addTopLevelItem(item)

            self.uiEditorColorsTREE.sortByColumn(0, Qt.AscendingOrder)

        # create the icons
        self.uiAddDescriptorBTN.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
        self.uiEditDescriptorBTN.setIcon(QIcon(blurdev.resourcePath('img/edit.png')))
        self.uiRemoveDescriptorBTN.setIcon(
            QIcon(blurdev.resourcePath('img/remove.png'))
        )

        # load the lexer classes
        self.uiLexerClassDDL.addItem('Custom')
        for key in dir(Qsci):
            if key.startswith('QsciLexer'):
                key = key.replace('QsciLexer', '')
                if key and key != 'Custom':
                    self.uiLexerClassDDL.addItem(key)

        # define custom properties
        self._language = None

        blurdev.bindMethod(self.uiEditorColorsTREE, 'dropEvent', self.handleDropEvent)
        blurdev.bindMethod(self.uiLexerColorsTREE, 'dropEvent', self.handleDropEvent)

        # create connections
        self.uiAddDescriptorBTN.clicked.connect(self.addDescriptor)
        self.uiEditDescriptorBTN.clicked.connect(self.editDescriptor)
        self.uiRemoveDescriptorBTN.clicked.connect(self.removeDescriptor)
        self.uiLexerClassDDL.currentIndexChanged.connect(
            self.refreshSchemeItemsFromCurrent
        )
        self.uiSaveBTN.clicked.connect(self.save)
        self.uiSaveAsBTN.clicked.connect(self.saveAs)
        self.uiLoadFromBTN.clicked.connect(self.loadFrom)
        self.uiCancelBTN.clicked.connect(self.reject)

    def addDescriptor(self):
        dlg = DescriptorDialog(self)
        if dlg.exec_():
            self.uiDescriptorTREE.addTopLevelItem(QTreeWidgetItem(dlg.descriptor()))

    def editDescriptor(self):
        item = self.uiDescriptorTREE.currentItem()
        if not item:
            QMessageBox.critical(
                self, 'No Item Selected', 'You have no descriptors selected to edit.'
            )
            return False

        dlg = DescriptorDialog(self)
        dlg.setDescriptor(item.text(0), item.text(1))
        if dlg.exec_():
            self.uiDescriptorTREE.addTopLevelItem(QTreeWidgetItem(dlg.descriptor()))

    def handleDropEvent(object, event):  # noqa: N805
        self = object.window()
        dragItem = event.source().currentItem()
        if not dragItem:
            return

        elif dragItem.treeWidget() == self.uiEditorColorsTREE and not dragItem.parent():
            QMessageBox.critical(
                self, 'Cannot Move', 'You cannot move the color items.'
            )
            return

        # return to the lexer colors tree
        if object == self.uiLexerColorsTREE:
            if dragItem.treeWidget() != object:
                dragItem.parent().takeChild(dragItem.parent().indexOfChild(dragItem))
                object.addTopLevelItem(dragItem)
            return

        # drop onto the editor colors tree
        targetItem = self.uiEditorColorsTREE.itemAt(event.pos())
        if targetItem and targetItem.parent():
            targetItem = targetItem.parent()

        if targetItem:
            # remove the drag item from its source
            if dragItem.parent():
                dragItem.parent().takeChild(dragItem.parent().indexOfChild(dragItem))
            else:
                dragItem.treeWidget().takeTopLevelItem(
                    dragItem.treeWidget().indexOfTopLevelItem(dragItem)
                )

            targetItem.addChild(dragItem)
            targetItem.setExpanded(True)

    # define instance methods
    def language(self):
        """
            \remarks	returns the value for my parameter
            \return		<variant>
        """
        return self._language

    def recordUi(self, language):
        language.setName(self.uiNameTXT.text())
        language.setFileTypes(str(self.uiFileTypesTXT.text()).split(';'))
        language.setLineComment(str(self.uiLineCommentTXT.text()))
        language.setLexerClassName(str(self.uiLexerClassDDL.currentText()))
        if language.lexerClassName() == 'Custom':
            language.setLexerClassName(str(self.uiLexerClassTXT.text()))
            language.setLexerModule(str(self.uiLexerModuleTXT.text()))

        for i in range(self.uiDescriptorTREE.topLevelItemCount()):
            item = self.uiDescriptorTREE.topLevelItem(i)
            language.addDescriptor(item.text(0), item.text(1))

        lexerColorTypes = {}
        for i in range(self.uiEditorColorsTREE.topLevelItemCount()):
            item = self.uiEditorColorsTREE.topLevelItem(i)
            lexerColorTypes[str(item.text(0))] = [
                item.child(c).data(0, Qt.UserRole) for c in range(item.childCount())
            ]

        language.setLexerColorTypes(lexerColorTypes)

    def refreshUi(self, language):
        self.uiNameTXT.setText(language.name())
        self.uiFileTypesTXT.setText(';'.join(language.fileTypes()))
        self.uiLineCommentTXT.setText(language.lineComment())

        self.uiLexerClassDDL.blockSignals(True)
        index = self.uiLexerClassDDL.findText(
            language.lexerClassName().replace('QsciLexer', '')
        )
        if index != -1:
            self.uiLexerClassDDL.setCurrentIndex(index)
        else:
            self.uiLexerClassDDL.setCurrentIndex(0)
            self.uiLexerClassTXT.setText(language.lexerClassName())
            self.uiLexerModuleTXT.setText(language.lexerModule())
        self.uiLexerClassDDL.blockSignals(False)

        # load the descriptors
        for descriptor in language.descriptors():
            item = QTreeWidgetItem([descriptor.dtype, descriptor.exprText])
            item.setSizeHint(0, QSize(0, 18))
            self.uiDescriptorTREE.addTopLevelItem(item)

        self.refreshSchemeItems(language)

    def refreshSchemeItemsFromCurrent(self):
        self.refreshSchemeItems(self._language)

    def refreshSchemeItems(self, language):
        lexercls = Qsci.__dict__.get('QsciLexer%s' % self.uiLexerClassDDL.currentText())

        # map the keys to the enum text
        data_map = {}
        if lexercls:
            try:
                lexer = lexercls()
            except Exception:
                lexer = None

            for k in dir(lexer):
                val = getattr(lexer, k)
                if re.match('^[A-Z]\w+$', k) and type(val) == int:
                    data_map[val] = k

        # clear the data options from the tree
        item_map = {}
        for i in range(self.uiEditorColorsTREE.topLevelItemCount()):
            item = self.uiEditorColorsTREE.topLevelItem(i)
            item_map[str(item.text(0)).lower()] = item
            for c in range(item.childCount() - 1, -1, -1):
                item.takeChild(c)

        # process the data from the language
        lexerColorTypes = language.lexerColorTypes()
        processed = []
        for key, values in lexerColorTypes.items():
            item = item_map.get(key.lower())
            if not item:
                continue

            processed += values
            for data in values:
                child = QTreeWidgetItem([str(data_map.get(data, data))])
                child.setData(0, Qt.UserRole, data)
                item.addChild(child)
            item.setExpanded(True)

        # add unprocessed data
        for data, key in data_map.items():
            if data not in processed:
                child = QTreeWidgetItem([str(data_map.get(data, data))])
                child.setData(0, Qt.UserRole, data)
                self.uiLexerColorsTREE.addTopLevelItem(child)

        self.uiLexerColorsTREE.sortByColumn(0, Qt.AscendingOrder)

    def removeDescriptor(self):
        item = self.uiDescriptorTREE.currentItem()
        if (
            item
            and QMessageBox.question(
                self,
                'Remove Item',
                'Are you sure you want to remove this descriptor?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.uiDescriptorTREE.takeTopLevelItem(
                self.uiDescriptorTREE.indexOfTopLevelItem(item)
            )

    def save(self, filename=''):
        if not self.uiNameTXT.text():
            QMessageBox.critical(
                self,
                'No Name Supplied',
                'You need to provide a name for this language.',
            )
            return False

        if not (type(filename) == str and filename):
            filename = self._language.sourcefile()
            if not filename:
                filename = blurdev.prefPath('lang/%s.ini' % self.uiNameTXT.text())

        # create a fresh language to save to
        language = lang.Language()

        # record the ui settings to the language
        self.recordUi(language)

        # save the language
        language.save(filename)
        self.accept()

    def saveAs(self):
        filename, _ = QtCompat.QFileDialog.getSaveFileName(
            self, 'Language Files', '', 'Ini Files (*.ini);;All Files (*.*)'
        )
        if filename:
            self.save(str(filename))

    def loadFrom(self):
        langname, accepted = QInputDialog.getItem(
            self, 'Select Language', 'Load from language:', lang.languages()
        )
        if accepted:
            language = lang.byName(str(langname))
            if language:
                self.refreshUi(language)

    def setLanguage(self, language):
        """
            \remarks	sets the value for my parameter to the inputed value
            \param		value	<variant>
        """
        self._language = language
        self.uiSaveBTN.setEnabled(language.isCustom())
        self.refreshUi(language)

    # define static methods
    @staticmethod
    def edit(language, parent=None):
        dlg = IdeLanguageDialog(parent)
        dlg.setLanguage(language)
        if dlg.exec_():
            return True
        return False
