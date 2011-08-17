##
# 	\namespace	blurdev.ide.addons.svn.svncheckoutdialog
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/24/11
#

from PyQt4.QtGui import QFileDialog, QMessageBox as msg

from blurdev.gui import Dialog
from blurdev.ide.addons.svn import svnops
from blurdev.ide.addons.svn import svnconfig


class SvnCheckoutDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self.uiUrlTXT.setText(svnconfig.CURRENT_URL)

        # create connections
        self.uiUrlBTN.clicked.connect(self.pickUrl)
        self.uiFilepathBTN.clicked.connect(self.pickPath)

    def accept(self):
        # make sure there is a url and a filepath specified
        if not (self.url() and self.filepath()):
            msg.critical(
                self,
                'Missing Data',
                'You need to provide a URL and filepath for the checkout to work.',
            )
            return False

        # create the checkout thread
        from threads.checkoutthread import CheckoutThread

        thread = CheckoutThread()
        thread.setFilepath(self.filepath())
        thread.setUrl(self.url())
        thread.setRecursive(self.uiRecursiveCHK.isChecked())
        thread.setIgnoreExternals(self.uiExternalsCHK.isChecked())

        if not self.uiHeadCHK.isChecked():
            print 'process a specific revision'

        # create the actions dialog
        from svnactiondialog import SvnActionDialog

        SvnActionDialog.start(self.parent(), thread, title='Checkout')

        svnconfig.CURRENT_URL = self.url()

        # accept the dialog
        super(SvnCheckoutDialog, self).accept()

    def filepath(self):
        return self.uiFilepathTXT.text()

    def setFilepath(self, filepath):
        self.uiFilepathTXT.setText(filepath)

    def setUrl(self, url):
        self.uiUrlTXT.setText(url)

    def pickUrl(self):
        url = svnops.getUrl(str(self.url()))
        if url:
            self.uiUrlTXT.setText(url)

    def pickPath(self):
        filepath = QFileDialog.getExistingDirectory(
            self, 'Checkout Directory', self.filePath()
        )
        if filepath:
            self.setFilepath(filepath)

    def url(self):
        return str(self.uiUrlTXT.text())

    # define static methods
    @staticmethod
    def checkout(ide, filepath='', url=''):
        dlg = SvnCheckoutDialog(ide)
        dlg.setFilepath(filepath)

        if url:
            dlg.setUrl(url)

        dlg.show()
