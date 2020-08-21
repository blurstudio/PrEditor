##
#   :namespace  python.blurdev.gui.widgets.pyularwidget.regexrefdialog
#
#   :remarks
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       11/11/11
#

from blurdev.gui import Dialog


class RegexRefDialog(Dialog):
    def __init__(self, parent=None):
        super(RegexRefDialog, self).__init__(parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)
