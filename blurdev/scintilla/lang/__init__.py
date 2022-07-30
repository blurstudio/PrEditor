##
# 	\namespace	blurdev.ide.lang
#
# 	\remarks	Manages the different programming languages that are supported by the IDE
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/16/11
#

from __future__ import print_function
from __future__ import absolute_import
import glob
import os.path

from .language import Language

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
    return sorted(_plugins.keys())


def filetypes():
    keys = sorted(_plugins.keys())

    output = []
    output.append('All Files (*.*)')
    output.append('Text Files (*.txt)')

    for key in keys:
        output.append(
            '%s Files (%s)' % (key, '*' + ';*'.join(_plugins[key].fileTypes()))
        )

    return ';;'.join(output)


def loadPlugins(path, custom=False):
    from blurdev import osystem

    path = osystem.expandvars(path)
    if not os.path.exists(path):
        return False

    files = glob.glob(os.path.join(path, '*.ini'))

    for file in files:
        plugin = Language.fromConfig(file)
        if plugin:
            plugin.setCustom(custom)
            _plugins[plugin.name()] = plugin
        else:
            print('[blurdev.ide.lang Error] Could not import %s' % file)


def refresh():
    import blurdev

    _plugins.clear()

    # load the installed plugins
    loadPlugins(os.path.dirname(__file__) + '/config')

    # load languags from the environment
    for key in os.environ.keys():
        if key.startswith('BDEV_PATH_LANG_'):
            loadPlugins(os.environ[key])

    # load the user plugins
    loadPlugins(blurdev.prefPath('lang'), True)


refresh()
