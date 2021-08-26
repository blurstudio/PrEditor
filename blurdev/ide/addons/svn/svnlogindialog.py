##
# 	\namespace	blurdev.ide.addons.svn.svnlogindialog
#
# 	\remarks	Creates login information for SVN
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

from __future__ import absolute_import
from blurdev.gui import Dialog


class SvnLoginDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self.uiDialogBTNS.accepted.connect(self.accept)
        self.uiDialogBTNS.rejected.connect(self.reject)

    # define static methods
    @staticmethod
    def login(realm, username, may_save):
        import blurdev

        dlg = SvnLoginDialog(blurdev.core.activeWindow())

        dlg.uiRememberCHK.setEnabled(may_save)
        dlg.uiUsernameTXT.setText(username)

        if dlg.exec_():
            return (
                True,
                str(dlg.uiUsernameTXT.text()),
                str(dlg.uiPasswordTXT.text()),
                dlg.uiRememberCHK.isChecked() and dlg.uiRememberCHK.isEnabled(),
            )
        return (False, '', '', False)
