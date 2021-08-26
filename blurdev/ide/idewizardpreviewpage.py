##
# 	\namespace	blurdev.ide.idewizardpreviewpage
#
#   \remarks    This dialog allows the user to create new python classes and packages
#   based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from __future__ import print_function
from __future__ import absolute_import
from Qt.QtCore import Qt
from Qt.QtGui import QColor
from Qt.QtWidgets import QTreeWidgetItem, QWizardPage


class ComponentItem(QTreeWidgetItem):
    def __init__(self, page, xml):
        name = page.formatText(xml.attribute('name'))
        QTreeWidgetItem.__init__(self, [name])

        from Qt.QtCore import Qt
        from Qt.QtGui import QIcon
        import blurdev

        self.setIcon(0, QIcon(blurdev.resourcePath('img/%s.png' % xml.nodeName)))

        if page.formatText(xml.attribute('checked')) != 'False':
            self.setCheckState(0, Qt.Checked)
        else:
            self.setCheckState(0, Qt.Unchecked)

        self._folder = xml.nodeName == 'folder'
        self._copyFrom = page.formatText(xml.attribute('copyFrom'))
        self._templateFrom = page.formatText(xml.attribute('templateFrom'))

        for child in xml.children():
            self.addChild(ComponentItem(page, child))

    def refreshChecked(self, inherit=False, state=None):
        if state is None or not inherit:
            state = self.checkState(0)

        elif inherit:
            self.setCheckState(0, state)

        if not state == Qt.Checked:
            self.setExpanded(False)
            self.setForeground(0, QColor('grey'))
        else:
            self.setExpanded(True)
            self.setForeground(0, QColor('black'))

        for i in range(self.childCount()):
            self.child(i).refreshChecked(inherit, state)

    def create(self, path):
        from Qt.QtCore import Qt

        if not self.checkState(0) == Qt.Checked:
            return

        import os
        import shutil

        path = str(path)
        newpath = os.path.join(path, str(self.text(0)))

        # create a folder
        if self._folder:
            if not os.path.exists(newpath):
                try:
                    os.mkdir(newpath)
                except OSError:
                    print('Could not create folder: ', newpath)
                    return

        # copy a file
        elif self._copyFrom:
            try:
                shutil.copyfile(self._copyFrom, newpath)
            except OSError:
                print('Error copying file from: ', self._copyFrom, ' to: ', newpath)

        # create from a template
        elif self._templateFrom:
            templ = self.page().relativePath('templ/%s' % self._templateFrom)
            self.page().formatFile(templ, newpath)

        # create the children
        for c in range(self.childCount()):
            self.child(c).create(newpath)

    def expandAll(self, state):
        self.setExpanded(state)
        for c in range(self.childCount()):
            self.child(c).expandAll(state)

    def page(self):
        return self.treeWidget().parent()


class IdeWizardPreviewPage(QWizardPage):
    def __init__(self, parent, moduleFile):
        QWizardPage.__init__(self, parent)

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self._moduleFile = moduleFile
        self._options = {}
        self.uiComponentsTREE.itemChanged.connect(self.refreshChecked)
        self.uiComponentsTREE.customContextMenuRequested.connect(self.showMenu)
        self.uiComponentsTREE.itemDoubleClicked.connect(self.renameCurrentItem)

        self.registerField('components', self)

    def formatFile(self, input, output):
        from blurdev import template

        template.formatFile(input, output, self._options)
        # Call formatFile twice so that it can properly format the aditional text added
        # in self._options.
        return template.formatFile(output, output, self._options)

    def formatText(self, text):
        from blurdev import template

        return template.formatText(text, self._options)

    def initializePage(self):
        from Qt.QtCore import QDir

        self.uiRootPATH.setFilePath(QDir.currentPath())

        self.uiComponentsTREE.blockSignals(True)
        self.uiComponentsTREE.setUpdatesEnabled(False)

        # generate a dictionary of options based on the fields
        field = self.field('options')
        foptions = self.field('options')
        if not type(foptions) == dict:
            foptions = {}

        self._options = {}
        for opt, val in foptions.items():
            self._options[str(opt)] = str(val)

        from blurdev.XML import XMLDocument

        doc = XMLDocument()

        field = str(self.field('components'))
        if not field:
            field = 'default'

        # clear and repopulate the tree
        import blurdev

        self.uiComponentsTREE.clear()
        if doc.load(
            blurdev.relativePath(self._moduleFile, 'components/%s.xml' % field)
        ):
            root = doc.root()

            for child in root.children():
                item = ComponentItem(self, child)
                self.uiComponentsTREE.addTopLevelItem(item)
                item.refreshChecked()

        self.uiComponentsTREE.setUpdatesEnabled(True)
        self.uiComponentsTREE.blockSignals(False)

    def refreshChecked(self, item):
        self.uiComponentsTREE.blockSignals(True)
        from Qt.QtCore import Qt
        from Qt.QtWidgets import QApplication

        item.refreshChecked(
            inherit=QApplication.instance().keyboardModifiers() == Qt.ShiftModifier
        )
        self.uiComponentsTREE.blockSignals(False)

    def renameCurrentItem(self):
        from Qt.QtWidgets import QInputDialog, QLineEdit

        item = self.uiComponentsTREE.currentItem()
        if not item:
            return False

        text, accepted = QInputDialog.getText(
            self, 'Rename...', 'New Name:', QLineEdit.Normal, item.text(0)
        )
        if accepted:
            item.setText(0, text)

    def relativePath(self, relpath):
        import blurdev

        return blurdev.relativePath(self._moduleFile, relpath)

    def showMenu(self):
        from Qt.QtGui import QCursor
        from Qt.QtWidgets import QMenu

        item = self.uiComponentsTREE.currentItem()
        if not item:
            return False

        menu = QMenu(self)
        menu.addAction('Rename...').triggered.connect(self.renameCurrentItem)
        menu.exec_(QCursor.pos())

    def validatePage(self):
        if not self.uiRootPATH.isResolved():
            from Qt.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                'Invalid Path',
                'You have to provide a valid path to create this template in',
            )
            return False

        path = self.uiRootPATH.filePath()

        # figure out the package location for this path
        import blurdev

        if 'package' not in self._options:
            self._options['package'] = blurdev.packageForPath(path)

        # record the installpath for future use
        self._options['installpath'] = path
        self.setField('options', self._options)

        # create the components
        for i in range(self.uiComponentsTREE.topLevelItemCount()):
            self.uiComponentsTREE.topLevelItem(i).create(path)

        return True
