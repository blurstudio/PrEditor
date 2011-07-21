##
# 	\namespace	blurdev.ide.addons.svn.svnrecentmessagedialog
#
# 	\remarks	Displays the recent messages to the user to pick from
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/02/11
#

from PyQt4.QtCore import Qt, QSize, QVariant
from PyQt4.QtGui import QTreeWidgetItem

from blurdev.gui import Dialog

from blurdev.ide.addons.svn import svnconfig


class SvnRecentMessageDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # load the options
        for msg in svnconfig.RECENT_MESSAGES:
            item = QTreeWidgetItem([msg.split('\n')[0]])
            item.setData(0, Qt.UserRole, QVariant(msg))
            item.setSizeHint(0, QSize(120, 18))
            self.uiMessageTREE.addTopLevelItem(item)

        # connect the double clicked action
        self.uiMessageTREE.itemDoubleClicked.connect(self.accept)

    def currentMessage(self):
        item = self.uiMessageTREE.currentItem()
        if item:
            return str(item.data(0, Qt.UserRole).toString())
        return ''

    # define static methods
    @staticmethod
    def getMessage():
        import blurdev

        dlg = SvnRecentMessageDialog(blurdev.core.activeWindow())
        if dlg.exec_():
            return dlg.currentMessage()
        return ''
