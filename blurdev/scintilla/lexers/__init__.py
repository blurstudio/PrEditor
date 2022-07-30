##
# 	\namespace	blurdev.ide.lexers
#
# 	\remarks    This dialog allows the user to create new python classes and packages
# 	based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

# -----------------------------------------------------------------------------
# create default mappings

# from Qt.Qsci import *

# # create default mappings
# register('Batch',		('.bat',),						 	 QsciLexerBatch)
# register('CSS',		('.css',),							 QsciLexerCSS)
# register('C++',		('.cpp','.c','.h',),				 QsciLexerCPP, '//')
# register('HTML',		('.htm','.html',),					 QsciLexerHTML)
# register('Lua',		('.lua',),							 QsciLexerLua)
# register('Python', 	('.py','.pyw','.pys','.b',), 		 QsciLexerPython, '#',
# '^([ \t]*)(def|class)[ \t]*([a-zA-Z0-9_]+\(?[^\)]*\)?):$')
# register('XML', 		('.xml','.ui','.blurproj','.pref',), QsciLexerXML)
# register('Bash',		('.sh',),							 QsciLexerBash)
# register('Javascript',	('.js',),						 QsciLexerJavaScript, '//')
# register('Puppet',		('.pp',),						 QsciLexerPerl, '#')
# register('Perl',		('.perl',),							 QsciLexerPerl)

# # create custom mappings
# from maxscriptlexer import MaxscriptLexer
# register( 'Maxscript',	('.ms','.mcr',),				MaxscriptLexer,		'--' )
