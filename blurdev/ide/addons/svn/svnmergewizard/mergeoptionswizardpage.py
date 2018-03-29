##
# 	\namespace	blurdev.ide.addons.svn.svnmergewizardmergeoptionswizardpage
#
# 	\remarks	Creates the options to run during the merge
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

import pysvn

from Qt.QtWidgets import QWizardPage


class MergeOptionsWizardPage(QWizardPage):
    def __init__(self, parent):
        # initialize the super class
        QWizardPage.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self.uiDryRunBTN.clicked.connect(self.dryRun)

    def additionalOptions(self):
        options = []

        if self.uiIgnoreLineEndingsCHK.isChecked():
            options.append('--ignore-eol-style')

        if self.uiIgnoreWhitespaceChangesCHK.isChecked():
            options.append('--ignore-space-change')

        if self.uiIgnoreWhitespacesCHK.isChecked():
            options.append('--ignore-all-space')

        return options

    def depth(self):
        text = self.uiDepthDDL.currentText()

        if text == 'Fully recursive':
            return pysvn.depth.infinity
        elif text == 'Immediate children, including folders':
            return pysvn.depth.immediates
        elif text == 'Only file children':
            return pysvn.depth.files
        elif text == 'Only this item':
            return pysvn.depth.unknown
        else:
            return pysvn.depth.empty

    def dryRun(self):
        self.window().merge(True)

    def nextId(self):
        return -1

    def noticeAncestry(self):
        return not self.uiIgnoreAncestryCHK.isChecked()

    def recordOnly(self):
        return self.uiRecordOnlyCHK.isChecked()
