##
# 	\namespace	blurdev.ide.addons.yamldialog
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/03/11
#

from blurdev.ide.ideaddon import IdeAddon


class YamlAddon(IdeAddon):
    def activate(self, ide):
        """
            \remarks	registers the YamlDialog as the default editor for
                        .yaml files
            \param		ide		<blurdev.ide.IdeEditor>
            \return		<bool> success
        """
        from yamldialog import YamlDialog
        from blurdev.ide import RegistryType

        # reigister the yaml dialog to the registry
        ide.registry().register(
            RegistryType.Extension, '^.yaml$', (YamlDialog.edit, '', '')
        )
        return True

    def deactivate(self, ide):
        """
            \remarks	unregisters the YamlDialog as the default editor for
                        .yaml files
            \param		ide		<blurdev.ide.IdeEditor>
            \return		<bool> success
        """

        from blurdev.ide import RegistryType

        return ide.registry().unregister(RegistryType.Extension, '^.yaml$')


# register the IdeAddon to the IDE system
IdeAddon.register('YAML Compiler', YamlAddon)
