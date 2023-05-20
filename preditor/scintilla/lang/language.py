from __future__ import absolute_import, print_function

import re
import sys

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

from PyQt5 import Qsci


class MethodDescriptor(object):
    def __init__(self, dtype, expr):
        self.dtype = dtype
        self.exprText = expr
        try:
            self.expr = re.compile(expr, re.DOTALL | re.MULTILINE)
        except Exception:
            print('error generating expression', expr)
            self.expr = None

    def search(self, text, startpos=-1):
        if not self.expr:
            return None

        if startpos != -1:
            return self.expr.search(text, startpos)
        else:
            return self.expr.search(text)


class Language(object):
    def __init__(self):
        self._name = ''
        self._fileTypes = []

        # lexer class information
        self._lexerClass = -1
        self._lexerClassName = ''
        self._lexerModule = ''
        self._lexerColorTypes = {}
        self._custom = False
        self._sourcefile = ''

        # comment information
        self._lineComment = ''

        # method descriptors
        self._descriptors = []

    def addDescriptor(self, type, expr):
        self._descriptors.append(MethodDescriptor(type, expr))

    def createLexer(self, parent=None):
        # create an instance of the lexer
        cls = self.lexerClass()
        if not cls:
            return None

        output = cls(parent)
        if output and parent:
            output.setFont(parent.font())
        return output

    def descriptors(self):
        return self._descriptors

    def isCustom(self):
        return self._custom

    def name(self):
        return self._name

    def lexerColorTypes(self):
        return self._lexerColorTypes

    def lineComment(self):
        return self._lineComment

    def fileTypes(self):
        return self._fileTypes

    def lexerClass(self):
        if self._lexerClass == -1:
            # use a custom lexer module
            if self._lexerModule:
                # retrieve the lexer module
                module = sys.modules.get(self._lexerModule)

                # try to import the module
                if not module:
                    try:
                        __import__(self._lexerModule)
                        module = sys.modules.get(self._lexerModule)
                    except Exception:
                        print(
                            (
                                '[preditor.scintilla.lexers.Language.createLexer() '
                                'Error] Could not import %s module'
                            )
                            % self._lexerModule
                        )
                        self._lexerClass = None
                        return None

            # otherwise, its in the Qsci module
            else:
                module = Qsci

            # retrieve the lexer class
            self._lexerClass = module.__dict__.get(self._lexerClassName)
            if not self._lexerClass:
                print(
                    (
                        '[preditor.scintilla.lexers.Language.createLexer() Error] '
                        'No %s class in %s'
                    )
                    % (self._lexerClassName, module.__name__)
                )

        return self._lexerClass

    def lexerClassName(self):
        return self._lexerClassName

    def lexerModule(self):
        return self._lexerModule

    def save(self, filename=''):
        if not filename:
            filename = self.filename()
        if not filename:
            return False

        parser = ConfigParser()
        parser.add_section('GLOBALS')
        parser.set('GLOBALS', 'name', self.name())
        parser.set('GLOBALS', 'filetypes', ';'.join(self.fileTypes()))
        # quotes are to preserve spaces which configparser strips out
        parser.set('GLOBALS', 'linecomment', '"{}"'.format(self.lineComment()))

        parser.add_section('LEXER')
        parser.set('LEXER', 'class', self.lexerClassName())
        parser.set('LEXER', 'module', self.lexerModule())

        parser.add_section('DESCRIPTORS')
        for i, desc in enumerate(self._descriptors):
            parser.set('DESCRIPTORS', '%s%i' % (desc.dtype, i), desc.exprText)

        parser.add_section('COLOR_TYPES')
        for key, value in self.lexerColorTypes().items():
            parser.set('COLOR_TYPES', key, ','.join([str(val) for val in value]))

        # save the language
        f = open(filename, 'w')
        parser.write(f)
        f.close()

        self._sourcefile = filename
        return True

    def setCustom(self, state):
        self._custom = state

    def setFileTypes(self, fileTypes):
        self._fileTypes = fileTypes

    def setLexerClassName(self, className):
        self._lexerClassName = className

    def setLexerModule(self, module):
        self._lexerModule = module

    def setLineComment(self, lineComment):
        self._lineComment = lineComment

    def setLexerColorTypes(self, lexerColorTypes):
        self._lexerColorTypes = lexerColorTypes

    def setName(self, name):
        self._name = name

    def sourcefile(self):
        return self._sourcefile

    @staticmethod
    def fromConfig(filename):
        parser = ConfigParser()

        if not parser.read(filename):
            return False

        plugin = Language()
        plugin._name = parser.get('GLOBALS', 'name')
        plugin._fileTypes = parser.get('GLOBALS', 'filetypes').split(';')

        # try to load the line comment information
        try:
            plugin._lineComment = parser.get('GLOBALS', 'linecomment').strip('"')
        except Exception:
            pass

        # try to load the lexer information
        try:
            plugin._lexerClassName = parser.get('LEXER', 'class')
            plugin._lexerModule = parser.get('LEXER', 'module')
        except Exception:
            pass

        # load the different descriptor options
        try:
            options = parser.options('DESCRIPTORS')
        except Exception:
            options = []

        for option in options:
            expr = parser.get('DESCRIPTORS', option)
            option = re.match(r'([^\d]*)\d*', option).groups()[0]
            plugin._descriptors.append(MethodDescriptor(option, expr))

        # load the different color map options
        try:
            options = parser.options('COLOR_TYPES')
        except Exception:
            options = []

        for option in options:
            vals = []
            for val in parser.get('COLOR_TYPES', option).split(','):
                try:
                    vals.append(int(val))
                except Exception:
                    pass
            plugin._lexerColorTypes[option] = vals

        plugin._sourcefile = filename

        return plugin
