##
# 	\namespace	blurdev.ide.addons.svn.svncopydialog
#
# 	\remarks	Allows the user to create copies of the desired url to a desired url
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/26/11
#

from __future__ import absolute_import
from blurdev.gui import Dialog

from blurdev.ide.addons.svn import svnconfig
from blurdev.ide.addons.svn import svnops


class SvnCopyDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # initialize ui
        self.uiSourceTXT.setText(svnconfig.CURRENT_URL)
        self.uiTargetTXT.setText(svnconfig.CURRENT_URL)
        self.uiSourceBTN.clicked.connect(self.pickSource)
        self.uiTargetBTN.clicked.connect(self.pickTarget)

    def accept(self):
        source = self.source()
        target = self.target()

        from Qt.QtWidgets import QMessageBox

        if not (source and target):
            QMessageBox.critical(
                self,
                'Missing Data',
                'You need to provide valid source and target urls for the copy.',
            )
            return False

        if source == target:
            QMessageBox.critical(
                self,
                'Same Paths',
                'You cannot copy to the same url.  Please provide a valid target url.',
            )
            return False

        if not self.uiMessageTXT.toPlainText():
            QMessageBox.critical(
                self, 'Missing Message', 'You need to provide a message for this copy.'
            )
            return False

        # record the target as the current url
        svnconfig.CURRENT_URL = self.target()

        # create the copy thread
        from .threads.copythread import CopyThread

        thread = CopyThread()
        thread.setSource(source)
        thread.setTarget(target)
        thread.setComments(str(self.uiMessageTXT.toPlainText()))

        # create the action dialog
        from .svnactiondialog import SvnActionDialog

        SvnActionDialog.start(self.parent(), thread, title='Branch/Tag')

        # accept the dialog
        super(SvnCopyDialog, self).accept()

    def pickSource(self):
        source = svnops.getUrl(self.source())
        if source:
            self.setSource(source)

    def pickTarget(self):
        target = svnops.getUrl(self.target())
        if target:
            self.setTarget(target)

    def setSource(self, source):
        self.uiSourceTXT.setText(source)

    def setTarget(self, target):
        self.uiTargetTXT.setText(target)

    def source(self):
        return str(self.uiSourceTXT.text())

    def target(self):
        return str(self.uiTargetTXT.text())

    # define static methods
    @staticmethod
    def branch(source='', target=''):
        import blurdev

        dlg = SvnCopyDialog(blurdev.core.activeWindow())
        dlg.setSource(source)
        dlg.setTarget(target)
        if dlg.exec_():
            return True
        return False
