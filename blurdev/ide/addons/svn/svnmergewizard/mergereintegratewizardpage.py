##
# 	\namespace	blurdev.ide.addons.svn.svnmergewizardmergereintegratewizardpage
#
# 	\remarks	Options for reintegrating a branch
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

import pysvn

from blurdev.ide.addons.svn import svnconfig

from Qt.QtWidgets import QWizardPage


class MergeReintegrateWizardPage(QWizardPage):
    def __init__(self, parent):
        # initialize the super class
        QWizardPage.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create connections
        self.uiUrlBTN.clicked.connect(self.pickUrl)

    def nextId(self):
        return self.window().Pages.Options

    def url(self):
        return str(self.uiUrlTXT.text())

    def pickUrl(self):
        from blurdev.ide.addons.svn import svnops

        url = svnops.getUrl(self.uiUrlTXT.text())
        if url:
            self.uiUrlTXT.setText(url)

    def setFilepath(self, filepath):
        self.uiFilepathLBL.setText(filepath)

        client = pysvn.Client()
        try:
            self.uiUrlTXT.setText(client.info(filepath).url)
        except:
            self.uiUrlTXT.setText(svnconfig.CURRENT_URL)
