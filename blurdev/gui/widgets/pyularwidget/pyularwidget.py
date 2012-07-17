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

from PyQt4.QtGui import QWidget, QIcon, QVBoxLayout
from regexrefdialog import RegexRefDialog


class PyularDialog(blurdev.gui.Dialog):
    def __init__(self, parent=None):
        if not parent:
            parent = blurdev.core.activeWindow()
        super(PyularDialog, self).__init__(parent)
        self.setWindowTitle('Pyular')
        # create the widget
        widget = PyularWidget(self)
        # create the layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        self.setLayout(layout)


class PyularWidget(QWidget):
    # if this list is changed, processResults must be updated to reflect the list
    searchTypes = ['Find All', 'Match', 'Search', 'Split', 'Sub']

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
        self.flags = 0
        self.uiSearchTypeDDL.clear()
        self.uiSearchTypeDDL.addItems(self.searchTypes)

    def parseFlags(self):
        """
            \Remarks	Parses the regular expression options
        """
        self.flags = 0
        out = set()
        for item in list(unicode(self.uiFlagsTXT.text()).upper()):
            if item in ['I', 'L', 'M', 'S', 'U', 'X']:
                self.flags |= getattr(re, item)
                out.add(item)
        self.uiFlagsTXT.setText(''.join(out))
        self.processResults()

    def processResults(self):
        pattern = unicode(self.uiExpressionTXT.text())
        text = unicode(self.uiStringTXT.toPlainText())
        typeIndex = self.uiSearchTypeDDL.currentIndex()
        try:
            self.uiErrorLBL.setText(' ')
            regex = re.compile(pattern, flags=self.flags)
            if typeIndex == 0:
                results = regex.findall(text)[0]
                out = ['<ul>']
                for result in results:
                    out.append('<li>%s</li>' % result)
                out.append('</ul>')
                self.uiResultsTXT.setText('<br>'.join(out))
                return
            elif typeIndex == 1:
                return self.processMatchObject(regex.match(text))
            elif typeIndex == 2:
                return self.processMatchObject(regex.search(text))
            elif typeIndex == 3:
                results = regex.split(text)
            # sub
            else:
                replace = unicode(self.uiReplaceTXT.text())
                results = regex.sub(replace, text)
                self.uiResultsTXT.setText(results)
                return
        except Exception, e:
            results = []
            self.uiErrorLBL.setText(str(e))
        self.uiResultsTXT.setText('\n'.join(results))

    def showRegexHelp(self):
        RegexRefDialog(self).show()

    def typeChanged(self, index):
        self.uiReplaceWGT.setVisible(index == 4)
        self.processResults()

    def processMatchObject(self, results):
        if results:
            groupDict = results.groupdict()
            # swap the keys for items, so we can do the look up on the value of results.groups()
            invert = dict(zip(groupDict.values(), groupDict.keys()))
            out = []
            for index in range(len(results.groups()) + 1):
                item = results.group(index)
                if item in invert:
                    out.append('<b>%s</b>: %s' % (invert[item], item))
                else:
                    out.append('<b>----<\b>: %s' % item)
            self.uiResultsTXT.setText('<br>'.join(out))
        else:
            self.uiResultsTXT.setText('No Match Found')
