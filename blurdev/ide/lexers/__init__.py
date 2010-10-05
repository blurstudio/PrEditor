##
# 	\namespace	blurdev.ide.lexers
#
# 	\remarks	This dialog allows the user to create new python classes and packages based on plugin templates
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

_loaded = False
_mapping = {}


class LexerMap:
    def __init__(self, name, fileTypes, lexerClass):
        self.name = name
        self.fileTypes = fileTypes
        self.lexerClass = lexerClass


def load():
    global _loaded
    if not _loaded:
        _loaded = True

        import os.path
        import glob

        filenames = glob.glob(os.path.split(__file__)[0] + '/*.py')
        for filename in filenames:
            modname = os.path.basename(filename).split('.')[0]
            if modname != '__init__':
                __import__('blurdev.ide.lexers.%s' % modname)


def languageFor(lexer):
    for value in _mapping.values():
        if isinstance(lexer, value.lexerClass):
            return value.name
    return ''


def lexerFor(ext):
    for lexerMap in _mapping.values():
        if ext in lexerMap.fileTypes:
            return lexerMap.lexerClass()
    return None


def lexer(lang):
    lmap = _mapping.get(str(lang))
    if lmap:
        return lmap.lexerClass()
    return None


def languages():
    keys = _mapping.keys()
    keys.sort()
    return keys


def register(lang, fileTypes, lexerClass):
    _mapping[str(lang)] = LexerMap(str(lang), fileTypes, lexerClass)


# -----------------------------------------------------------------------------
# create default mappings

from PyQt4.Qsci import *

# create default mappings
register('Python', ('.py', '.pyw', '.pys'), QsciLexerPython)
register('XML', ('.xml', '.ui'), QsciLexerXML)
