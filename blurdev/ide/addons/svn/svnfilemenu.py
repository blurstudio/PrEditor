##
# 	\namespace	blurdev.ide.addons.svn
#
# 	\remarks	Creates connections to the IDE editor for SVN
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import os
from PyQt4.QtGui import QMenu

from blurdev.ide.idefilemenu import IdeFileMenu
from blurdev.ide.addons.svn import svnops


class SvnFileMenu(IdeFileMenu):
    def defineMenu(self):
        super(SvnFileMenu, self).defineMenu()

        # add the svn commands support
        from PyQt4.QtGui import QAction, QIcon
        from blurdev.ide.addons import svn

        # define the SVN commands before the explore action
        before = self.ide().findChild(QAction, 'uiExploreACT')

        # If BDEV_SVN_FILE_EXTRAS is defined, add the options to this menu, otherwise add them to the SvnActionMenu
        if os.environ.get('BDEV_SVN_FILE_EXTRAS', None):
            if svnops.findUrl(self.filepath()):
                # create the update command
                act = QAction(self)
                act.setText('SVN Update')
                act.setIcon(QIcon(svn.resource('img/update.png')))
                act.triggered.connect(self.svnUpdate)
                self.insertAction(before, act)

                # create the commit command
                act = QAction(self)
                act.setText('SVN Commit')
                act.setIcon(QIcon(svn.resource('img/commit.png')))
                act.triggered.connect(self.svnCommit)
                self.insertAction(before, act)

            # create options to checkout for folders
            elif not self.isfile():
                act = QAction(self)
                act.setText('SVN Checkout')
                act.setIcon(QIcon(svn.resource('img/update.png')))
                act.triggered.connect(self.svnCheckout)
                self.insertAction(before, act)

        from blurdev.ide.addons.svn.svnactionmenu import SvnActionMenu

        menu = SvnActionMenu(self, 'file', self.filepath())
        self.insertMenu(before, menu)

        # add the separator
        self.insertSeparator(before)

    def svnCheckout(self):
        svnops.checkout(self.filepath())

    def svnCommit(self):
        svnops.commit(self.filepath())

    def svnUpdate(self):
        svnops.update(self.filepath())
