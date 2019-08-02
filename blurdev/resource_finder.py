from pillar.resource_finder import ResourceFinder as PillarResourceFinder


class ResourceFinder(PillarResourceFinder):
    def __init__(self):
        from pathlib2 import Path

        path = Path(__file__).parents[1] / 'resource'
        super(ResourceFinder, self).__init__('blurdev', path)
