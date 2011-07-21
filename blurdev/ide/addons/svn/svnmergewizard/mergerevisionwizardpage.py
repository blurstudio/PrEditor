##
# 	\namespace	blurdev.ide.addons.svn.svnmergewizardmergerevisionwizardpage
#
# 	\remarks	Creates the interface for merging a range of revisions
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

import pysvn

from blurdev.ide.addons.svn import svnconfig
from blurdev.ide.addons.svn import svnops

from PyQt4.QtGui import QWizardPage


class MergeRevisionWizardPage(QWizardPage):
    def __init__(self, parent):
        # initialize the super class
        QWizardPage.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # create connections
        self.uiUrlBTN.clicked.connect(self.pickUrl)
        self.uiUrlLogBTN.clicked.connect(self.pickRevisions)

    def nextId(self):
        return self.window().Pages.Options

    def url(self):
        return str(self.uiUrlTXT.text())

    def revisions(self):
        return str(self.uiRevisionsTXT.text())

    def pickUrl(self):
        url = svnops.getUrl(self.uiUrlTXT.text())
        if url:
            self.uiUrlTXT.setText(url)

    def pickRevisions(self):
        revisions, accepted = svnops.getRevisions(self.uiUrlTXT.text())
        if accepted:
            # create the revision string
            revisions.sort()

            revisiontext = []

            firstrev = None
            lastrev = None

            for rev in revisions + [None]:
                # make sure we log the first revision in the sequence
                if firstrev == None:
                    firstrev = rev

                # check against the last revision in the chain
                if rev == None or lastrev != None and rev != (lastrev + 1):
                    if lastrev != firstrev:
                        revisiontext.append('%s-%s' % (firstrev, lastrev))
                    else:
                        revisiontext.append('%s' % firstrev)

                    # clear the range
                    firstrev = rev
                    lastrev = None

                lastrev = rev

            self.uiRevisionsTXT.setText(','.join(revisiontext))

    def setFilepath(self, filepath):
        self.uiFilepathLBL.setText(filepath)

        client = pysvn.Client()
        try:
            self.uiUrlTXT.setText(client.info(filepath).url)
        except:
            self.uiUrlTXT.setText(svnconfig.CURRENT_URL)
