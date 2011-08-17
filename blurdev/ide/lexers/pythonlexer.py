##
# 	\namespace	blurdev.ide.lexers.pythonlexer
#
# 	\remarks	Defines a class for parsing python files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.Qsci import QsciLexerPython


class PythonLexer(QsciLexerPython):
    def __init__(self, *args):
        super(PythonLexer, self).__init__(*args)

        # set the indentation warning
        self.setIndentationWarning(self.Inconsistent)
