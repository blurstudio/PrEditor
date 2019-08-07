from cute.icon_factory import IconFactory as CuteIconFactory


class IconFactory(CuteIconFactory):
    def __init__(self):
        super(IconFactory, self).__init__()

        from pillar.resource_finder import ResourceFinder
        from blurdev import Resources

        finder = ResourceFinder('icons', 'img', parent=Resources())
        self._configure(finders=finder)
