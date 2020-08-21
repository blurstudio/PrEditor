##
#   :namespace  python.blurdev.gui.widgets.pyularwidget
#
#   :remarks    A Python regular expression editor based entirely on
#               http://www.rubular.com/
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       11/11/11
#

import sys
import re
import blurdev

from Qt.QtGui import QIcon
from Qt.QtWidgets import QVBoxLayout, QWidget
from .regexrefdialog import RegexRefDialog


class PyularDialog(blurdev.gui.Dialog):
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

    def count(self):
        return self.widget.count()

    def expression(self):
        return self.widget.expression()

    def flags(self):
        return self.widget.flags()

    def setCount(self, count):
        self.widget.setCount(count)

    def setExpression(self, expr):
        self.widget.setExpression(expr)

    def setFlags(self, flags):
        self.widget.setFlags(flags)

    def setTestString(self, testStr):
        self.widget.setTestString(testStr)

    def testString(self):
        return self.widget.testString()


class PyularWidget(QWidget):
    ReType = blurdev.enum.enum(FindAll=0, Match=1, Search=2, Split=3, Sub=4)
    # if this list is changed, processResults must be updated to reflect the list
    emptyString = "['']"
    bulletFormat = '<li>%s</li>'

    def __init__(self, parent=None):
        # initialize the super class
        super(PyularWidget, self).__init__(parent)

        # load the ui
        import blurdev.gui

        blurdev.gui.loadUi(__file__, self)

        self.uiHelpBTN.setIcon(QIcon(blurdev.resourcePath('img/blurdev.png')))
        self.flags = 0
        self.uiSearchTypeDDL.clear()
        self.uiSearchTypeDDL.addItems(
            [self.tr(lab) for lab in self.ReType.labels(byVal=True)]
        )

    def count(self):
        return self.uiCountSPN.value()

    def errorLog(self):
        """
            :remarks    If a exception is called from this class, the email generated
                        will contain this information
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
        for item in list(self.uiFlagsTXT.text().upper()):
            if item in ['I', 'L', 'M', 'S', 'U', 'X']:
                self.flags |= getattr(re, item)
                out.add(item)
        self.uiFlagsTXT.setText(''.join(out))
        self.processResults()

    def processResults(self):
        pattern = self.uiExpressionTXT.text()
        txt = self.uiStringTXT.toPlainText()
        typeIndex = self.uiSearchTypeDDL.currentIndex()
        count = self.uiCountSPN.value()
        # start to build the code string that will be populated later in the code.
        code = 're.'
        flags = []
        for flag in self.uiFlagsTXT.text():
            flags.append('re.{}'.format(flag))
        flags = ' | '.join(flags)
        if flags:
            flags = ', flags={}'.format(flags)
        try:
            self.uiErrorLBL.setVisible(False)
            self.uiSplitNotesLBL.setVisible(False)
            regex = re.compile(pattern, flags=self.flags)
            if typeIndex == self.ReType.FindAll:
                results = regex.findall(txt)
                out = []
                if results:
                    out.append('<ul>')
                    for result in results:
                        # re.findall can return a list of strings, or a list of tuples
                        # containing strings.
                        if isinstance(result, tuple):
                            out.append('<li><b><i>Nested Group:</i></b></li>')
                            out.append('<ul>')
                            for item in result:
                                if item == '':
                                    item = self.emptyString
                                    self.uiSplitNotesLBL.setVisible(True)
                                out.append(self.bulletFormat % item)
                            out.append('</ul>')
                        else:
                            if result == '':
                                result = self.emptyString
                            out.append(self.bulletFormat % result)
                    out.append('</ul>')
                self.uiResultsTXT.setText('\n'.join(out))
                code += "findall(r'{pattern}', r'{stri}'{flags})".format(
                    pattern=pattern, stri=txt, flags=flags
                )
                self.uiCodeTXT.setText(code)
                return
            elif typeIndex == self.ReType.Match:
                code += "match(r'{pattern}', r'{stri}'{flags})".format(
                    pattern=pattern, stri=txt, flags=flags
                )
                self.uiCodeTXT.setText(code)
                return self.processMatchObject(regex.match(txt))
            elif typeIndex == self.ReType.Search:
                code += "search(r'{pattern}', r'{stri}'{flags})".format(
                    pattern=pattern, stri=txt, flags=flags
                )
                self.uiCodeTXT.setText(code)
                return self.processMatchObject(regex.search(txt))
            elif typeIndex == self.ReType.Split:
                results = regex.split(txt, maxsplit=count)
                for index, result in enumerate(results):
                    if result is None:
                        results[index] = '[None]'
                        self.uiSplitNotesLBL.setVisible(True)
                    if result == '':
                        results[index] = self.emptyString
                        self.uiSplitNotesLBL.setVisible(True)
                if sys.version_info.major < 2 or sys.version_info.minor < 7:
                    flags = ''
                txt = "split(r'{pattern}', r'{stri}', maxsplit={count}{flags})"
                code += txt.format(
                    pattern=pattern, stri=txt, count=count, flags=flags
                )
                self.uiCodeTXT.setText(code)
            else:  # Sub
                replace = self.uiReplaceTXT.text()
                results = regex.sub(replace, txt, count=count)
                self.uiResultsTXT.setText(results)
                if sys.version_info.major < 2 or sys.version_info.minor < 7:
                    flags = ''
                txt = "sub(r'{pattern}', r'{repl}', r'{stri}', count={count}{flags})"
                code += txt.format(
                    pattern=pattern, repl=replace, count=count, stri=txt, flags=flags
                )
                self.uiCodeTXT.setText(code)
                return
        except Exception as e:
            results = []
            self.uiErrorLBL.setVisible(True)
            self.uiErrorLBL.setText(str(e))
        self.uiResultsTXT.setText('\n'.join(results))

    def setCount(self, count):
        self.uiCountSPN.setValue(count)

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
        self.uiReplaceWGT.setVisible(index == self.ReType.Sub)
        self.uiCountSPN.setVisible(
            index == self.ReType.Split or index == self.ReType.Sub
        )
        self.uiCountLBL.setVisible(self.uiCountSPN.isVisible())
        self.uiCountSlashLBL.setVisible(self.uiCountSPN.isVisible())
        d = {self.ReType.Split: 'maxsplit', self.ReType.Sub: 'count'}
        self.uiCountLBL.setText(d.get(index, ''))
        self.processResults()

    def processMatchObject(self, results):
        if results:
            groupDict = results.groupdict()
            # swap the keys for items, so we can do the look up on the value of
            # results.groups()
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
