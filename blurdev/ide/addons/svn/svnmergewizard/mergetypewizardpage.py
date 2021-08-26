##
# 	\namespace	blurdev.ide.addons.svn.svnmergewizardmergetypewizardpage
#
# 	\remarks	Creates the merge type options page
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

from __future__ import absolute_import
from Qt.QtWidgets import QWizardPage


class MergeTypeWizardPage(QWizardPage):
    def __init__(self, parent):
        # initialize the super class
        QWizardPage.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

    def nextId(self):
        if self.isRevision():
            return self.window().Pages.Ranges
        elif self.isReintegrate():
            return self.window().Pages.Reintegrate
        else:
            return self.window().Pages.Tree

    def isRevision(self):
        return self.uiMergeRevisionCHK.isChecked()

    def isReintegrate(self):
        return self.uiReintegrateCHK.isChecked()

    def isTree(self):
        return self.uiMergeDifferentCHK.isChecked()
