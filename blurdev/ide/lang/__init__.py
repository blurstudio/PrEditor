##
# 	\namespace	blurdev.ide.lang
#
# 	\remarks	Manages the different programming languages that are supported by the IDE
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/16/11
#

import glob
import os.path

from language import Language

_plugins = {}


def byName(name):
    return _plugins.get(str(name))


def byLexer(lexer):
    for plugin in _plugins.values():
        if isinstance(lexer, plugin.lexerClass()):
            return plugin
    return None


def byExtension(extension):
    for plugin in _plugins.values():
        if extension in plugin.fileTypes():
            return plugin
    return None


def languages():
    keys = _plugins.keys()
    keys.sort()
    return keys


def filetypes():
    keys = _plugins.keys()
    keys.sort()

    output = []
    output.append('All Files (*.*)')
    output.append('Text Files (*.txt)')

    for key in keys:
        output.append(
            '%s Files (%s)' % (key, '*' + ';*'.join(_plugins[key].fileTypes()))
        )

    return output


# load the plugins
files = glob.glob(os.path.dirname(__file__) + '/config/*.ini')
for file in files:
    plugin = Language.fromConfig(file)
    if plugin:
        _plugins[plugin.name()] = plugin
    else:
        print '[blurdev.ide.lang Error] Could not import %s' % file
