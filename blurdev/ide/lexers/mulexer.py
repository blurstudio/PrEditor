##
# 	\namespace	blurdev.ide.lexers.mulexer
#
# 	\remarks	Defines a class for parsing mu files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

import re
from PyQt4.Qsci import QsciLexerCPP

MU_KEYWORDS = """
method string Color use require module for_each let
"""


class MuLexer(QsciLexerCPP):
    def keywords(self, style):
        output = super(MuLexer, self).keywords(style)

        # for some reason, CPP lexer uses comment style for
        # its keywords
        if style == self.Comment:
            output += MU_KEYWORDS

        return output
