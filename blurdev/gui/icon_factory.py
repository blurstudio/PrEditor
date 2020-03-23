from cute.icon_factory import IconFactory as CuteIconFactory


class IconFactory(CuteIconFactory):

    """Subclass that adds finders for the production library's and blurdev's icons. Also loads preset file.
    """

    def __init__(self, **kwargs):

        from pillar.resource_finder import ResourceFinder
        from blurdev import Resources

        from pathlib2 import Path

        finders = []
        local_path = Path(__file__).parents[0]

        # Build blurdev image finder.
        root_finder = Resources()
        bdev_finder = root_finder.child('resources')
        finders.append(ResourceFinder('blurdev-icons', 'img', parent=bdev_finder))

        # Build library image finder.
        lib_finder = root_finder.child('library')
        config_file = local_path / 'library_icons.yaml'
        if config_file.exists():
            finders.extend(
                ResourceFinder.build_from_config_file(
                    str(config_file), parent=lib_finder
                )
            )
        else:
            print("No icon config file found.")
            finders.append(ResourceFinder('library-icons', 'icons', parent=lib_finder))

        # Get presets file.
        presets_file = local_path / 'icon_presets.yaml'

        # Add finders to IconFactory.
        super(IconFactory, self).__init__(finders=finders, presets=str(presets_file))

        # Allow passed kwargs to override settings.
        self._configure(**kwargs)
