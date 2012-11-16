##
#   :namespace  python.blurdev.gui.widgets.pyularwidget
#
#   :remarks    A Python regular expression editor based entirely on http://www.rubular.com/
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       11/11/11
#

import PyQt4.uic, os.path, re, sys, blurdev

from PyQt4.QtGui import QWidget, QIcon, QVBoxLayout
from regexrefdialog import RegexRefDialog


class PyularDialog(blurdev.gui.Dialog):
    _instance = None

    def __init__(self, parent=None):
        if not parent:
            parent = blurdev.core.activeWindow()
        super(PyularDialog, self).__init__(parent)
        self.setWindowTitle('Pyular')
        # create the widget
        self.widget = PyularWidget(self)
        # create the layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget)
        self.setLayout(layout)
        self.setWindowIcon(QIcon(blurdev.resourcePath('img/ide/pyular.png')))

    def expression(self):
        return self.widget.expression()

    def flags(self):
        return self.widget.flags()

    def setExpression(self, expr):
        self.widget.setExpression(expr)

    def setFlags(self, flags):
        self.widget.setFlags(flags)

    def setTestString(self, testStr):
        self.widget.setTestString(testStr)

    def testString(self):
        return self.widget.testString()

    @staticmethod
    def instance(parent=None):
        if not PyularDialog._instance:
            inst = PyularDialog(parent)

            from PyQt4.QtCore import Qt

            inst.setAttribute(Qt.WA_DeleteOnClose, False)

            PyularDialog._instance = inst

        return PyularDialog._instance


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

    def errorLog(self):
        """
            :remarks	If a exception is called from this class, the email generated will contain this information
        """
        msg = []
        msg.append('Pyular')
        msg.append('Expression: %s' % self.uiExpressionTXT.text())
        msg.append('Flags: %s' % self.uiFlagsTXT.text())
        msg.append('Search Type: %s' % self.uiSearchTypeDDL.currentText())
        msg.append('Replace Text: %s' % self.uiReplaceTXT.text())
        msg.append('Test String: %s' % self.uiStringTXT.toPlainText())
        return '\n'.join(msg)

    def expression(self):
        return self.uiExpressionTXT.text()

    def flags(self):
        return self.uiFlagsTXT.text()

    def parseFlags(self):
        """
            :remarks	Parses the regular expression options
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
            self.uiErrorLBL.setVisible(False)
            self.uiSplitNotesLBL.setVisible(False)
            regex = re.compile(pattern, flags=self.flags)
            if typeIndex == 0:  # Find All
                results = regex.findall(text)
                out = []
                if results:
                    out.append('<ul>')
                    for result in results:
                        out.append('<li>%s</li>' % result)
                    out.append('</ul>')
                self.uiResultsTXT.setText('\n'.join(out))
                return
            elif typeIndex == 1:  # Match
                return self.processMatchObject(regex.match(text))
            elif typeIndex == 2:  # Search
                return self.processMatchObject(regex.search(text))
            elif typeIndex == 3:  # Split
                results = regex.split(text)
                for index, result in enumerate(results):
                    if result == None:
                        results[index] = '[None]'
                        self.uiSplitNotesLBL.setVisible(True)
                    if result == '':
                        results[index] = "['']"
                        self.uiSplitNotesLBL.setVisible(True)
            else:  # Sub
                replace = unicode(self.uiReplaceTXT.text())
                results = regex.sub(replace, text)
                self.uiResultsTXT.setText(results)
                return
        except Exception, e:
            results = []
            self.uiErrorLBL.setVisible(True)
            self.uiErrorLBL.setText(str(e))
        self.uiResultsTXT.setText('\n'.join(results))

    def setExpression(self, expr):
        self.uiExpressionTXT.setText(expr)

    def setFlags(self, flags):
        self.uiFlagsTXT.setText(flags)
        self.parseFlags()

    def setTestString(self, testStr):
        self.uiStringTXT.setPlainText(testStr)

    def showRegexHelp(self):
        RegexRefDialog(self).show()

    def testString(self):
        return self.uiStringTXT.toPlainText()

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
