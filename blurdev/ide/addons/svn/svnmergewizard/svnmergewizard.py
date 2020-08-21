##
# 	\namespace	blurdev.ide.addons.svn.svnmergewizard
#
#   \remarks    Creates a merging wizard for taking a user through the steps of merging
#               SVN branches
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/01/11
#

from blurdev.ide.addons.svn.threads.mergethread import (
    MergeRangesThread, MergeReintegrateThread,
)

from blurdev.gui import Wizard
from blurdev.enum import enum


class SvnMergeWizard(Wizard):
    Pages = enum('Type', 'Ranges', 'Reintegrate', 'Tree', 'Options')

    def initWizardPages(self):
        """ overloaded from the Wizard class, this method allows a user to define the
        pages that are going to be used for this wizard.  Look up QWizard in the Qt
        Assistant for more advanced options and controlling flows for your wizard.

        Wizard classes don't need to specify UI information, all the data for the
        Wizard will be encased within WizardPage instances
        """
        # create custom properties
        self._filepath = ''

        # define wizard properties
        self.setFixedHeight(450)
        self.setWindowTitle('SVN Merge')
        self.setButtonText(Wizard.FinishButton, 'Merge')

        # create the merge type merge path
        from mergetypewizardpage import MergeTypeWizardPage

        self._mergeType = MergeTypeWizardPage(self)
        self.setPage(self.Pages.Type, self._mergeType)

        # create the merge reintegrate page
        from mergereintegratewizardpage import MergeReintegrateWizardPage

        self._reintegrate = MergeReintegrateWizardPage(self)
        self.setPage(self.Pages.Reintegrate, self._reintegrate)

        # create the merge revision page
        from mergerevisionwizardpage import MergeRevisionWizardPage

        self._revision = MergeRevisionWizardPage(self)
        self.setPage(self.Pages.Ranges, self._revision)

        # create the merge options page
        from mergeoptionswizardpage import MergeOptionsWizardPage

        self._options = MergeOptionsWizardPage(self)
        self.setPage(self.Pages.Options, self._options)

    def accept(self):
        Wizard.accept(self)
        self.merge()

    def merge(self, test=False):
        thread = None

        # create the mulitple revisions thread
        if self._mergeType.isRevision():
            thread = MergeRangesThread()

            # set revision options
            thread.setUrl(self._revision.url())
            thread.setRanges(self._revision.revisions())
            thread.setTargetPath(self._filepath)

        # create the reintegration thread
        elif self._mergeType.isReintegrate():
            thread = MergeReintegrateThread()

            # set reintegrate options
            thread.setUrl(self._reintegrate.url())
            thread.setTargetPath(self._filepath)

        # set common thread options
        thread.setDepth(self._options.depth())
        thread.setNoticeAncestry(self._options.noticeAncestry())
        thread.setRecordOnly(self._options.recordOnly())
        thread.setAdditionalOptions(self._options.additionalOptions())
        thread.setDryRun(test)

        if thread:
            # run the merge thread action
            from blurdev.ide.addons.svn.svnactiondialog import SvnActionDialog

            SvnActionDialog.start(self.parent(), thread, title='Merge')

    def setFilepath(self, filepath):
        self._filepath = filepath
        self._revision.setFilepath(filepath)
        self._reintegrate.setFilepath(filepath)

    @classmethod
    def runWizard(cls, filepath, parent=None):
        wiz = cls(parent)
        wiz.setFilepath(filepath)
        wiz.show()
