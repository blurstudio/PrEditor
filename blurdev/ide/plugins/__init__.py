##
# 	\namespace	blurdev.ide.pluginbuilder.plugins
#
# 	\remarks	These plugins allow you to quickly and easily create components of a tool or class
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

_plugins = {}


def load():
    import glob
    import os.path

    filenames = glob.glob(os.path.split(__file__)[0] + '/*/__init__.py')
    for filename in filenames:
        modname = os.path.normpath(filename).split(os.path.sep)[-2]

        __import__('blurdev.ide.plugins.%s' % modname)


def register(pluginName, pluginClass, iconFile=''):
    import os.path, sys

    from blurdev.ide.plugin import Plugin

    plugin = Plugin()
    plugin.setObjectName(pluginName)
    plugin.setWidgetClass(pluginClass)

    if not iconFile:
        plugin.setIconFile(
            os.path.split(sys.modules[pluginClass.__module__].__file__)[0]
            + '/img/icon.png'
        )
    else:
        plugin.setIconFile(iconFile)

    _plugins[str(pluginName)] = plugin


def plugins():
    output = _plugins.values()
    output.sort(lambda x, y: cmp(x.objectName(), y.objectName()))
    return output
