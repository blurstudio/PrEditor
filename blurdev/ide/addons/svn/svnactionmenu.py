##
# 	\namespace	blurdev.ide.addons.svn.svnactionmenu
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import os

from Qt.QtCore import Signal
from Qt.QtGui import QIcon
from Qt.QtWidgets import QApplication, QMenu

from blurdev.ide.addons.svn import svnops


class SvnActionMenu(QMenu):
    refreshRequested = Signal()

    def __init__(self, parent, mode, filepath):
        super(SvnActionMenu, self).__init__(parent)

        # set custom properties
        self._filepath = filepath
        self._mode = mode
        isfile = os.path.isfile(filepath)

        from blurdev.ide.addons import svn

        hasEnviron = not os.environ.get('BDEV_SVN_FILE_EXTRAS', None)

        if hasEnviron:
            self.setTitle('More pySVN')
        else:
            self.setTitle('pySVN')
        self.setIcon(QIcon(svn.resource('img/svn.png')))

        # If BDEV_SVN_FILE_EXTRAS is defined, add the options to this menu, otherwise
        # add them to the SvnActionMenu
        if hasEnviron:
            if svnops.findUrl(self._filepath):
                # create the update command
                act = self.addAction('SVN Update')
                act.setIcon(QIcon(svn.resource('img/update.png')))
                act.triggered.connect(self.svnUpdate)

                # create the commit command
                act = self.addAction('SVN Commit')
                act.setIcon(QIcon(svn.resource('img/commit.png')))
                act.triggered.connect(self.svnCommit)

            # create options to checkout for folders
            elif not isfile:
                act = self.addAction('SVN Checkout')
                act.setIcon(QIcon(svn.resource('img/update.png')))
                act.triggered.connect(self.svnCheckout)

            self.addSeparator()

        if isfile:
            act = self.addAction('Compare with base...')
            act.setIcon(QIcon(svn.resource('img/compare.png')))
            act.triggered.connect(self.svnCompare)

        act = self.addAction('Show Log')
        act.setIcon(QIcon(svn.resource('img/log.png')))
        act.triggered.connect(self.svnLog)

        if mode != 'repobrowser':
            act = self.addAction('Repo-browser')
            act.setIcon(QIcon(svn.resource('img/browser.png')))
            act.triggered.connect(self.svnBrowse)
        else:
            act = self.addAction('Export...')
            act.setIcon(QIcon(svn.resource('img/export.png')))
            act.setEnabled(False)

            act = self.addAction('Checkout...')
            act.setIcon(QIcon(svn.resource('img/checkout.png')))
            act.setEnabled(False)

            self.addSeparator()

            act = self.addAction('Create folder...')
            act.setIcon(QIcon(svn.resource('img/folder.png')))
            act.triggered.connect(self.svnCreateFolder)

            act = self.addAction('Add file...')
            act.setEnabled(False)

            act = self.addAction('Add folder...')
            act.setEnabled(False)

            self.addSeparator()

        # 		act = self.addAction( 'Check for modifications' )
        # 		act.setIcon( QIcon( svn.resource( 'img/modifications.png' ) ) )
        # 		act.setEnabled(False)
        #
        # 		act = self.addAction( 'Revision graph' )
        # 		act.setIcon( QIcon( svn.resource( 'img/revision_graph.png' ) ) )
        # 		act.setEnabled(False)

        if mode in ('file',):
            self.addSeparator()

            act = self.addAction('Resolved...')
            act.setIcon(QIcon(svn.resource('img/resolved.png')))
            act.setEnabled(False)

            act = self.addAction('Update to revision...')
            act.setIcon(QIcon(svn.resource('img/update.png')))
            act.setEnabled(False)

        if mode in ('file', 'repobrowser',):
            act = self.addAction('Rename...')
            act.setIcon(QIcon(svn.resource('img/rename.png')))
            act.triggered.connect(self.svnRename)

            act = self.addAction('Delete...')
            act.setIcon(QIcon(svn.resource('img/delete.png')))
            act.triggered.connect(self.svnRemove)

        if mode != 'repobrowser':
            act = self.addAction('Revert')
            act.setIcon(QIcon(svn.resource('img/revert.png')))
            act.triggered.connect(self.svnRevert)
        else:
            act = self.addAction('Copy to working copy...')
            act.setEnabled(False)

            act = self.addAction('Copy to...')
            act.setEnabled(False)

            act = self.addAction('Copy URL to clipboard')
            act.triggered.connect(self.copyFilepathToClipboard)

            self.addSeparator()

        if mode in ('file',):
            act = self.addAction('Clean up')
            act.setIcon(QIcon(svn.resource('img/cleanup.png')))
            act.triggered.connect(self.svnCleanup)

            act = self.addAction('Get lock...')
            act.setIcon(QIcon(svn.resource('img/lock.png')))
            act.setEnabled(False)

            act = self.addAction('Release lock')
            act.setIcon(QIcon(svn.resource('img/unlock.png')))
            act.setEnabled(False)

            self.addSeparator()

            act = self.addAction('Branch/tag...')
            act.setIcon(QIcon(svn.resource('img/branch.png')))
            act.triggered.connect(self.svnBranch)

            act = self.addAction('Switch...')
            act.setIcon(QIcon(svn.resource('img/switch.png')))
            act.setEnabled(False)

            act = self.addAction('Merge...')
            act.setIcon(QIcon(svn.resource('img/merge.png')))
            act.triggered.connect(self.svnMerge)

            act = self.addAction('Export...')
            act.setIcon(QIcon(svn.resource('img/export.png')))
            act.setEnabled(False)

            act = self.addAction('Relocate...')
            act.setIcon(QIcon(svn.resource('img/relocate.png')))
            act.setEnabled(False)

            self.addSeparator()

        if mode != 'repobrowser':
            act = self.addAction('Add...')
            act.setIcon(QIcon(svn.resource('img/add.png')))
            act.triggered.connect(self.svnAdd)

        if mode in ('file',):
            self.addSeparator()

            act = self.addAction('Create patch...')
            act.setIcon(QIcon(svn.resource('img/patch.png')))
            act.setEnabled(False)

            act = self.addAction('Apply Patch...')
            act.setIcon(QIcon(svn.resource('img/apply_patch.png')))
            act.setEnabled(False)

        act = self.addAction('Properties...')
        act.setIcon(QIcon(svn.resource('img/properties.png')))
        act.setEnabled(False)

        self.addSeparator()

        act = self.addAction('Settings')
        act.setIcon(QIcon(svn.resource('img/settings.png')))
        act.setEnabled(False)

        act = self.addAction('Help')
        act.setIcon(QIcon(svn.resource('img/help.png')))
        act.setEnabled(False)

        act = self.addAction('About')
        act.setIcon(QIcon(svn.resource('img/about.png')))
        act.setEnabled(False)

    def copyFilepathToClipboard(self):
        QApplication.clipboard().setText(self._filepath)

    def svnAdd(self):
        svnops.add(self._filepath)

    def svnBranch(self):
        svnops.branch(self._filepath)

    def svnBrowse(self):
        svnops.browse(self._filepath)

    def svnCheckout(self):
        svnops.checkout(self._filepath)

    def svnCleanup(self):
        svnops.cleanup(self._filepath)

    def svnCommit(self):
        svnops.commit(self._filepath)

    def svnCompare(self):
        revision = 'HEAD'
        if self._mode != 'repobrowser':
            revision = 'BASE'
        svnops.compare(self._filepath, revision)

    def svnCreateFolder(self):
        if svnops.createFolder(self._filepath):
            self.refreshRequested.emit()

    def svnLog(self):
        svnops.showLog(self._filepath)

    def svnMerge(self):
        svnops.merge(self._filepath)

    def svnRename(self):
        svnops.rename(self._filepath)

    def svnRemove(self):
        if svnops.remove(self._filepath):
            self.refreshRequested.emit()

    def svnRevert(self):
        svnops.revert(self._filepath)

    def svnUpdate(self):
        svnops.update(self._filepath)
