##
# 	\namespace	blurdev.ide.addons.svn.svnactionmenu
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import os.path

from PyQt4.QtGui import QMenu, QIcon

from blurdev.ide.addons.svn import svnops


class SvnActionMenu(QMenu):
    def __init__(self, parent, mode, filepath):
        super(SvnActionMenu, self).__init__(parent)

        # set custom properties
        self._filepath = filepath
        isfile = os.path.isfile(filepath)

        from blurdev.ide.addons import svn

        self.setTitle('More SVN')
        self.setIcon(QIcon(svn.resource('img/svn.png')))

        act = self.addAction('Show Log')
        act.setIcon(QIcon(svn.resource('img/log.png')))

        self.addSeparator()

        act = self.addAction('Repo-browser')
        act.setIcon(QIcon(svn.resource('img/browser.png')))
        act.triggered.connect(self.svnBrowse)

        act = self.addAction('Check for modifications')
        act.setIcon(QIcon(svn.resource('img/modifications.png')))

        act = self.addAction('Revision graph')
        act.setIcon(QIcon(svn.resource('img/revision_graph.png')))

        self.addSeparator()

        act = self.addAction('Resolved...')
        act.setIcon(QIcon(svn.resource('img/resolved.png')))

        act = self.addAction('Update to revision...')
        act.setIcon(QIcon(svn.resource('img/update.png')))

        act = self.addAction('Rename...')
        act.setIcon(QIcon(svn.resource('img/rename.png')))
        act.triggered.connect(self.svnRename)

        act = self.addAction('Delete...')
        act.setIcon(QIcon(svn.resource('img/delete.png')))

        act = self.addAction('Revert')
        act.setIcon(QIcon(svn.resource('img/revert.png')))
        act.triggered.connect(self.svnRevert)

        act = self.addAction('Clean up')
        act.setIcon(QIcon(svn.resource('img/cleanup.png')))
        act.triggered.connect(self.svnCleanup)

        act = self.addAction('Get lock...')
        act.setIcon(QIcon(svn.resource('img/lock.png')))

        act = self.addAction('Release lock')
        act.setIcon(QIcon(svn.resource('img/unlock.png')))

        self.addSeparator()

        act = self.addAction('Branch/tag...')
        act.setIcon(QIcon(svn.resource('img/branch.png')))
        act.triggered.connect(self.svnBranch)

        act = self.addAction('Switch...')
        act.setIcon(QIcon(svn.resource('img/switch.png')))

        act = self.addAction('Merge...')
        act.setIcon(QIcon(svn.resource('img/merge.png')))

        act = self.addAction('Export...')
        act.setIcon(QIcon(svn.resource('img/export.png')))

        act = self.addAction('Relocate...')
        act.setIcon(QIcon(svn.resource('img/relocate.png')))

        self.addSeparator()

        act = self.addAction('Add...')
        act.setIcon(QIcon(svn.resource('img/add.png')))
        act.triggered.connect(self.svnAdd)

        self.addSeparator()

        act = self.addAction('Create patch...')
        act.setIcon(QIcon(svn.resource('img/patch.png')))

        act = self.addAction('Apply Patch...')
        act.setIcon(QIcon(svn.resource('img/apply_patch.png')))

        act = self.addAction('Properties...')
        act.setIcon(QIcon(svn.resource('img/properties.png')))

        self.addSeparator()

        act = self.addAction('Settings')
        act.setIcon(QIcon(svn.resource('img/settings.png')))

        act = self.addAction('Help')
        act.setIcon(QIcon(svn.resource('img/help.png')))

        act = self.addAction('About')
        act.setIcon(QIcon(svn.resource('img/about.png')))

    def svnAdd(self):
        svnops.add(self._filepath)

    def svnBranch(self):
        svnops.branch(self._filepath)

    def svnBrowse(self):
        svnops.browse(self._filepath)

    def svnCleanup(self):
        svnops.cleanup(self._filepath)

    def svnRename(self):
        svnops.rename(self._filepath)

    def svnRevert(self):
        svnops.revert(self._filepath)
