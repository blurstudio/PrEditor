##
#   \namespace  blurdev.ide.ideeditor
#
#   \remarks    This is the main ide window
#
#   \author     beta@blur.com
#   \author     Blur Studio
#   \date       08/19/10
#

from __future__ import absolute_import
from blurdev.gui.dialogs.configdialog import ConfigSet


class IdeEditor(object):
    # define the global config set
    _globalConfigSet = None

    @staticmethod
    def documentConfigSet():
        # create a temp config set to duplicate the settings from
        import blurdev.ide.config.common
        import blurdev.ide.config.editor

        configSet = ConfigSet()
        configSet.loadPlugins(blurdev.ide.config.common)
        configSet.loadPlugins(blurdev.ide.config.editor)

        # copy parameters from the global
        configSet.copyFrom(IdeEditor.globalConfigSet())

        return configSet

    @staticmethod
    def globalConfigSet():
        if not IdeEditor._globalConfigSet:
            import blurdev.ide.config.common
            import blurdev.ide.config.editor

            IdeEditor._globalConfigSet = ConfigSet('ide/config')
            IdeEditor._globalConfigSet.loadPlugins(blurdev.ide.config.common)
            IdeEditor._globalConfigSet.loadPlugins(blurdev.ide.config.editor)
            IdeEditor._globalConfigSet.restore()

        return IdeEditor._globalConfigSet
