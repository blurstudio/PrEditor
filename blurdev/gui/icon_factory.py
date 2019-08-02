from cute.icon_factory import IconFactory as PillarIconFactory


class IconFactory(PillarIconFactory):
    def __init__(self):
        super(IconFactory, self).__init__()

        from pillar.resource_finder import ResourceFinder
        from blurdev import Resources

        finder = ResourceFinder('icons', 'img', parent=Resources())
        self._setFinders(finder, False)
