##
# 	\namespace	blurdev.ide.addons.svn.svncomparedialog
#
# 	\remarks	Creates a dialog for comparing and merging changes between revisions
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

from __future__ import absolute_import
import os.path

from blurdev.gui import Dialog


class SvnCompareDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create custom properties
        self._scrolling = False

        # create the editors
        from blurdev.ide.documenteditor import DocumentEditor

        # create the left side editor
        self._left = DocumentEditor(self)
        self._left.setReadOnly(True)
        self.uiLeftAREA.setWidget(self._left)

        # create the right side editor
        self._right = DocumentEditor(self)
        self._right.setReadOnly(True)
        self.uiRightAREA.setWidget(self._right)

        # create the connections
        self._left.verticalScrollBar().valueChanged.connect(self.updateRightVScroll)
        self._left.horizontalScrollBar().valueChanged.connect(self.updateRightHScroll)
        self._right.verticalScrollBar().valueChanged.connect(self.updateLeftVScroll)
        self._right.horizontalScrollBar().valueChanged.connect(self.updateLeftHScroll)

    def setBaseFile(self, basefile):
        self._basefile = basefile
        self.setWindowTitle('SVN Compare - %s' % os.path.basename(basefile))
        self._left.load(basefile)
        self._right.load(basefile)

    def setDiff(self, diff):
        self._diff = diff
        self.uiDiffTXT.setText(diff)

    def updateScrollBar(self, bar, value):
        # have to use this vs. the block signals so that Scintilla updates properly
        if self._scrolling:
            return

        self._scrolling = True
        bar.setValue(value)
        self._scrolling = False

    def updateRightHScroll(self, value):
        self.updateScrollBar(self._right.horizontalScrollBar(), value)

    def updateRightVScroll(self, value):
        self.updateScrollBar(self._right.verticalScrollBar(), value)

    def updateLeftHScroll(self, value):
        self.updateScrollBar(self._left.horizontalScrollBar(), value)

    def updateLeftVScroll(self, value):
        self.updateScrollBar(self._left.verticalScrollBar(), value)

    # define static methods
    @staticmethod
    def compare(basefile, diff):
        import blurdev

        dlg = SvnCompareDialog(blurdev.core.rootWindow())
        dlg.setBaseFile(basefile)
        dlg.setDiff(diff)
        dlg.show()
