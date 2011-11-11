##
#   \namespace  python.blurdev.gui.widgets.pyularwidget
#
#   \remarks    A Python regular expression editor based entirely on http://www.rubular.com/
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       11/11/11
#

import PyQt4.uic, os.path, re, sys, blurdev

from PyQt4.QtGui import QWidget, QIcon
from regexrefdialog import RegexRefDialog


class PyularWidget(QWidget):
    def __init__(self, parent=None):
        # initialize the super class
        super(PyularWidget, self).__init__(parent)

        # load the ui
        uifile = os.path.join(
            os.path.dirname(__file__),
            'ui/%s.ui' % os.path.basename(__file__).split('.')[0],
        )
        PyQt4.uic.loadUi(uifile, self)

        self.uiHelpBTN.setIcon(QIcon(blurdev.resourcePath('img/blurdev.png')))

    def processResults(self):
        try:
            results = re.findall(
                unicode(self.uiExpressionTXT.text()),
                unicode(self.uiStringTXT.toPlainText()),
            )
            self.uiErrorLBL.setText(' ')
        except Exception, e:
            results = []
            self.uiErrorLBL.setText(str(e))
        self.uiResultsTXT.setText('\n'.join(results))

    def showRegexHelp(self):
        RegexRefDialog(self).show()
