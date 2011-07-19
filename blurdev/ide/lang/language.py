##
# 	\namespace	blurdev.ide.lang.language
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/16/11
#

import sys
import re

from ConfigParser import ConfigParser

import PyQt4.Qsci


class MethodDescriptor(object):
    def __init__(self, dtype, expr):
        self.dtype = dtype
        try:
            self.expr = re.compile(expr)
        except:
            print 'error generating expression', expr
            self.expr = None

    def match(self, text):
        if not self.expr:
            return {}

        results = self.expr.match(text)

        if results:
            output = results.groupdict()
            output.setdefault('type', self.dtype)
            return output
        else:
            return {}


class Language(object):
    def __init__(self):
        self._name = ''
        self._fileTypes = []

        # lexer class information
        self._lexerClass = -1
        self._lexerClassName = ''
        self._lexerModule = ''

        # comment information
        self._lineComment = ''

        # method descriptors
        self._descriptors = []

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

    def name(self):
        return self._name

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
                    except:
                        print '[blurdev.ide.lexers.Language.createLexer() Error] Could not import %s module' % self._lexerModule
                        self._lexerClass = None
                        return None

            # otherwise, its in the Qsci module
            else:
                module = PyQt4.Qsci

            # retrieve the lexer class
            self._lexerClass = module.__dict__.get(self._lexerClassName)
            if not self._lexerClass:
                print '[blurdev.ide.lexers.Language.createLexer() Error] No %s class in %s' % (
                    self._lexerClassName,
                    module.__name__,
                )

        return self._lexerClass

    def lexerModule(self):
        return self._lexerModule

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
            plugin._lineComment = parser.get('GLOBALS', 'linecomment')
        except:
            pass

        # try to load the lexer information
        try:
            plugin._lexerClassName = parser.get('LEXER', 'class')
            plugin._lexerModule = parser.get('LEXER', 'module')
        except:
            pass

        # load the different descriptor options
        try:
            options = parser.options('DESCRIPTORS')
        except:
            options = []

        for option in options:
            expr = parser.get('DESCRIPTORS', option)
            option = re.match('([^\d]*)\d*', option).groups()[0]
            plugin._descriptors.append(MethodDescriptor(option, expr))

        return plugin
